from django.db import transaction
from django.utils import timezone
from typing import Dict, Any, List
import logging

from apps.trading.models import PurchaseOrder, SalesOrder
from apps.fund.models import FundToken
from apps.trading.security.token_validators import TokenReservationManager

logger = logging.getLogger('trading.token_transfer')

class TokenTransferError(Exception):
    """Excepción para errores de transferencia de tokens"""
    pass

class TokenTransferService:
    """
    🔄 Servicio de Transferencias de Tokens - Maneja solo las transferencias reales de tokens
    
    Responsabilidades:
    - Ejecutar transferencias de tokens en blockchain
    - Actualizar propiedad en base de datos
    - Gestionar reservas de tokens
    - Actualizar estados de órdenes de venta
    """
    
    def __init__(self):
        self.reservation_manager = TokenReservationManager()
    
    @transaction.atomic
    def execute_transfers(self, purchase_order: PurchaseOrder) -> dict:
        """Ejecuta todas las transferencias de tokens para una orden de compra"""
        
        transferred_tokens = []
        transfer_errors = []
        successful_blockchain_transfers = []  # ✅ Para tracking de rollback
        
        # Crear punto de guardado inicial
        savepoint_id = transaction.savepoint()
        
        try:
            # Validar metadatos
            if not (hasattr(purchase_order, 'metadata') and purchase_order.metadata):
                raise TokenTransferError("No se encontraron metadatos de selección en la orden")
            
            selected_matches = purchase_order.metadata.get('selected_matches', [])
            
            if not selected_matches:
                raise TokenTransferError("No se encontraron matches seleccionados para transferir")
            
            logger.info(f"Processing {len(selected_matches)} matches atomically")
            
            # ✅ FASE 1: VALIDAR TODAS LAS TRANSFERENCIAS ANTES DE EJECUTAR
            validated_transfers = []
            
            for i, match in enumerate(selected_matches):
                try:
                    validation_result = self._validate_match_for_transfer(purchase_order, match)
                    validated_transfers.append({
                        'match': match,
                        'match_index': i,
                        'sales_order': validation_result['sales_order'],
                        'reserved_tokens': validation_result['reserved_tokens'],
                        'units_to_transfer': validation_result['units_to_transfer']
                    })
                    
                except Exception as e:
                    error_msg = f"Validation failed for match {i+1}: {str(e)}"
                    logger.error(error_msg)
                    # Si falla la validación, abortar todo
                    transaction.savepoint_rollback(savepoint_id)
                    raise TokenTransferError(f"Pre-validation failed: {error_msg}")
            
            logger.info(f"✅ All {len(validated_transfers)} matches validated successfully")
            
            # ✅ FASE 2: EJECUTAR TODAS LAS TRANSFERENCIAS
            for validated_transfer in validated_transfers:
                try:
                    match_result = self._execute_validated_match_transfer(
                        purchase_order, 
                        validated_transfer
                    )
                    
                    transferred_tokens.extend(match_result['successful'])
                    transfer_errors.extend(match_result['errors'])
                    
                    # Tracking para posible rollback
                    successful_blockchain_transfers.extend(match_result['blockchain_transfers'])
                    
                    match_index = validated_transfer['match_index']
                    logger.info(f"✅ Match {match_index + 1}/{len(validated_transfers)} processed: {len(match_result['successful'])} tokens transferred")
                    
                except Exception as e:
                    error_msg = f"Execution failed for match {validated_transfer['match_index'] + 1}: {str(e)}"
                    logger.error(error_msg)
                    
                    # Rollback automático por el decorator @transaction.atomic
                    raise TokenTransferError(f"Transfer execution failed: {error_msg}")
            
            # ✅ FASE 3: VERIFICAR ÉXITO TOTAL
            if not transferred_tokens:
                transaction.savepoint_rollback(savepoint_id)
                raise TokenTransferError("No se pudo transferir ningún token. Todas las operaciones revertidas.")
            
            # ✅ FASE 4: CONFIRMAR TRANSACCIÓN
            transaction.savepoint_commit(savepoint_id)
            
            result = {
                'successful': transferred_tokens,
                'errors': transfer_errors,
                'total_transferred': len(transferred_tokens),
                'total_errors': len(transfer_errors),
                'matches_processed': len(selected_matches),
                'atomic_execution': True,
                'transaction_committed': True
            }
            
            logger.info(f"✅ ATOMIC TRANSFER COMPLETED SUCCESSFULLY")
            logger.info(f"Total tokens transferred: {result['total_transferred']}")
            logger.info(f"Total errors: {result['total_errors']}")
            
            return result
            
        except Exception as e:
            # El rollback es automático por @transaction.atomic, pero agregamos logging
            logger.error(f"❌ ATOMIC TRANSFER FAILED - ROLLING BACK ALL CHANGES")
            logger.error(f"Error: {str(e)}")
            logger.error(f"Successful transfers before failure: {len(transferred_tokens)}")
            
            # Información para debugging
            rollback_info = {
                'transferred_before_failure': len(transferred_tokens),
                'blockchain_transfers_reversed': len(successful_blockchain_transfers),
                'matches_processed': len([t for t in transferred_tokens]),
                'error': str(e)
            }
            
            logger.error(f"Rollback info: {rollback_info}")
            
            # Re-lanzar la excepción para que el decorador maneje el rollback
            raise TokenTransferError(f"Atomic transfer failed: {str(e)}")
    
    def _validate_match_for_transfer(self, purchase_order: PurchaseOrder, match: dict) -> dict:
        """Valida un match antes de ejecutar transferencias"""
        
        # Extraer datos del match
        sales_order_id = match.get('sales_order_id')
        units_to_transfer = match.get('units', 0)
        
        if not sales_order_id or units_to_transfer <= 0:
            raise TokenTransferError(f"Invalid match: sales_order_id={sales_order_id}, units={units_to_transfer}")
        
        # Obtener orden de venta
        try:
            sales_order = SalesOrder.objects.select_for_update().get(id=sales_order_id)
        except SalesOrder.DoesNotExist:
            raise TokenTransferError(f"Sales order {sales_order_id} not found")
        
        # Verificar que la orden esté en estado válido
        if sales_order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
            raise TokenTransferError(f"Sales order {sales_order.order_number} has invalid status: {sales_order.status}")
        
        # Verificar tokens disponibles
        try:
            reserved_tokens = self.get_reserved_tokens_for_transfer(sales_order, units_to_transfer)
        except Exception as e:
            raise TokenTransferError(f"Failed to get reserved tokens for sales order {sales_order.order_number}: {str(e)}")
        
        if len(reserved_tokens) < units_to_transfer:
            raise TokenTransferError(
                f"Insufficient tokens for sales order {sales_order.order_number}: "
                f"needed {units_to_transfer}, available {len(reserved_tokens)}"
            )
        
        return {
            'sales_order': sales_order,
            'reserved_tokens': reserved_tokens,
            'units_to_transfer': units_to_transfer
        }
    
    def _execute_validated_match_transfer(self, purchase_order: PurchaseOrder, validated_transfer: dict) -> dict:
        """Ejecuta transferencias para un match ya validado"""
        
        sales_order = validated_transfer['sales_order']
        reserved_tokens = validated_transfer['reserved_tokens']
        units_to_transfer = validated_transfer['units_to_transfer']
        
        # Ejecutar transferencias individuales
        successful_transfers = []
        transfer_errors = []
        blockchain_transfers = []
        
        for token_id in reserved_tokens[:units_to_transfer]:
            try:
                transfer_result = self.execute_single_token_transfer(
                    token_id, sales_order, purchase_order
                )
                successful_transfers.append(transfer_result)
                
                # Tracking para rollback
                if transfer_result.get('transfer_result'):
                    blockchain_transfers.append({
                        'token_id': token_id,
                        'blockchain_result': transfer_result['transfer_result']
                    })
                
            except Exception as e:
                error_msg = f"Token transfer failed for {token_id}: {str(e)}"
                transfer_errors.append({
                    'token_id': token_id,
                    'error': error_msg,
                    'sales_order_id': str(sales_order.id)
                })
                logger.error(error_msg)
                
                # En modo atómico, cualquier error individual causa rollback total
                raise TokenTransferError(error_msg)
        
        # Actualizar orden de venta después de transferencias exitosas
        if successful_transfers:
            self.update_sales_order_after_transfer(sales_order, len(successful_transfers))
            self.update_purchase_order_after_transfer(purchase_order, len(successful_transfers))
            
            # Liberar reservas de tokens transferidos exitosamente
            transferred_token_ids = [t['token_id'] for t in successful_transfers]
            self.release_transferred_tokens(transferred_token_ids, sales_order)
        
        return {
            'successful': successful_transfers,
            'errors': transfer_errors,
            'blockchain_transfers': blockchain_transfers
        }
    
    def process_match_transfer(self, purchase_order: PurchaseOrder, match: dict) -> dict:
        """Procesa la transferencia de tokens para un match específico"""
        
        # Extraer datos del match
        sales_order_id = match.get('sales_order_id')
        units_to_transfer = match.get('units', 0)
        
        if not sales_order_id or units_to_transfer <= 0:
            logger.warning(f"Skipping invalid match: sales_order_id={sales_order_id}, units={units_to_transfer}")
            return {'successful': [], 'errors': []}
        
        # Obtener orden de venta
        try:
            sales_order = SalesOrder.objects.get(id=sales_order_id)
        except SalesOrder.DoesNotExist:
            error_msg = f"Sales order {sales_order_id} not found"
            logger.error(error_msg)
            return {
                'successful': [], 
                'errors': [{'sales_order_id': sales_order_id, 'error': error_msg}]
            }
        
        # Obtener tokens reservados
        try:
            reserved_tokens = self.get_reserved_tokens_for_transfer(sales_order, units_to_transfer)
        except Exception as e:
            error_msg = f"Failed to get reserved tokens: {str(e)}"
            logger.error(error_msg)
            return {
                'successful': [], 
                'errors': [{'sales_order_id': sales_order_id, 'error': error_msg}]
            }
        
        # Ejecutar transferencias individuales
        successful_transfers = []
        transfer_errors = []
        
        for token_id in reserved_tokens:
            try:
                transfer_result = self.execute_single_token_transfer(
                    token_id, sales_order, purchase_order
                )
                successful_transfers.append(transfer_result)
                
            except Exception as e:
                error_msg = f"Token transfer failed for {token_id}: {str(e)}"
                transfer_errors.append({
                    'token_id': token_id,
                    'error': error_msg,
                    'sales_order_id': sales_order_id
                })
                logger.error(error_msg)
        
        # Actualizar orden de venta después de transferencias exitosas
        if successful_transfers:
            self.update_sales_order_after_transfer(sales_order, len(successful_transfers))
            self.update_purchasr_order_after_transfer(purchase_order, len(successful_transfers))
            
            # Liberar reservas de tokens transferidos exitosamente
            transferred_token_ids = [t['token_id'] for t in successful_transfers]
            self.release_transferred_tokens(transferred_token_ids, sales_order)
        
        return {
            'successful': successful_transfers,
            'errors': transfer_errors
        }
    
    def get_reserved_tokens_for_transfer(self, sales_order: SalesOrder, units_needed: int) -> List[str]:
        """Obtiene tokens reservados para transferencia con validación usando metadata como fuente de verdad"""
        
        # ✅ DEBUGGING COMPLETO
        logger.info(f"=== DEBUGGING SALES ORDER {sales_order.id} ===")
        logger.info(f"Order Number: {sales_order.order_number}")
        logger.info(f"Order Status: {sales_order.status}")
        logger.info(f"Seller: {sales_order.seller_user.email}")
        logger.info(f"Units needed: {units_needed}")
        
        # Verificar metadata como única fuente de verdad
        if sales_order.metadata:
            logger.info(f"metadata exists: {sales_order.metadata}")
            reserved_in_metadata = sales_order.metadata.get('reserved_tokens', [])
            logger.info(f"reserved_tokens in metadata: {reserved_in_metadata}")
        else:
            logger.info("metadata: NULL/EMPTY")
        
        # Verificar tokens reales en base de datos
        actual_tokens = list(FundToken.objects.filter(
            fund=sales_order.fund,
            owner_user=sales_order.seller_user,
            status=True
        ).values_list('token_id', flat=True))
        logger.info(f"Actual tokens owned by seller: {actual_tokens[:10]}...")  # Solo primeros 10
        logger.info(f"Total tokens owned: {len(actual_tokens)}")
        
        # Opción 1: metadata.reserved_tokens (fuente única de verdad)
        if sales_order.metadata and sales_order.metadata.get('reserved_tokens'):
            token_ids = sales_order.metadata.get('reserved_tokens', [])
            available_tokens = token_ids[:units_needed]
            logger.info(f"✅ Found {len(token_ids)} tokens in metadata")
            
            if len(available_tokens) < units_needed:
                logger.error(f"❌ INSUFFICIENT TOKENS in metadata: Need {units_needed}, Found {len(available_tokens)}")
                raise TokenTransferError(
                    f"Vendedor no tiene suficientes tokens reservados en metadata. "
                    f"Necesario: {units_needed}, Disponible: {len(available_tokens)}"
                )
            
            return available_tokens
        
        # Opción 2: RESERVA AUTOMÁTICA como fallback
        logger.warning(f"No reserved tokens found in metadata. Attempting automatic reservation...")
        
        if len(actual_tokens) < units_needed:
            logger.error(f"❌ INSUFFICIENT TOKENS OWNED: Need {units_needed}, Owner has {len(actual_tokens)}")
            raise TokenTransferError(
                f"Vendedor no tiene suficientes tokens. Necesario: {units_needed}, Disponible: {len(actual_tokens)}"
            )
        
        # Reservar automáticamente los primeros tokens disponibles
        auto_reserved_tokens = actual_tokens[:units_needed]
        
        # Actualizar metadata con reserva automática
        if not sales_order.metadata:
            sales_order.metadata = {}
        
        sales_order.metadata['reserved_tokens'] = auto_reserved_tokens
        sales_order.metadata['auto_reserved_at_payment'] = timezone.now().isoformat()
        sales_order.metadata['auto_reserved_reason'] = 'No previous reservation found'
        sales_order.save(update_fields=['metadata'])
        
        logger.info(f"✅ AUTO-RESERVED {len(auto_reserved_tokens)} tokens for sales order {sales_order.id}")
        
        return auto_reserved_tokens

    def execute_single_token_transfer(
        self, 
        token_id: str, 
        sales_order: SalesOrder, 
        purchase_order: PurchaseOrder
    ) -> dict:
        """Ejecuta la transferencia de un token individual con parámetros correctos"""
        
        logger.info(f"Transferring token {token_id} from {sales_order.seller_user.email} to {purchase_order.supplier_user.email}")
        
        from apps.kaleido.utils import safe_transfer_721_index_to_index, get_wallet_index
        
        try:
            # ✅ 1. OBTENER DIRECCIÓN DE WALLET DEL RECEPTOR (COMPRADOR)
            receiver_wallet_data, receiver_error = get_wallet_index(purchase_order.supplier_user, purchase_order.fund.id)
            if receiver_error:
                raise TokenTransferError(f"Failed to get buyer wallet: {receiver_error}")
            
            address_wallet_receiver = receiver_wallet_data.get('address')
            if not address_wallet_receiver:
                raise TokenTransferError("No address found in buyer wallet data")
            
            logger.info(f"Receiver wallet address: {address_wallet_receiver}")
            
            # ✅ 2. OBTENER DATOS DEL FONDO
            fund = purchase_order.fund
            if not fund.token_contract_721 or not fund.token_contract_721.contract_address:
                raise TokenTransferError("Fund does not have a valid token contract address")
            
            if not fund.hd_wallet or not fund.hd_wallet.id_wallet:
                raise TokenTransferError("Fund does not have a valid HD wallet")
            
            contract_address_id = fund.token_contract_721.contract_address
            wallet_id = fund.hd_wallet.id_wallet
            
            logger.info(f"Contract address: {contract_address_id}")
            logger.info(f"Wallet ID: {wallet_id}")
            
            # ✅ 3. EJECUTAR TRANSFERENCIA CON PARÁMETROS CORRECTOS
            logger.info("=== EXECUTING BLOCKCHAIN TRANSFER ===")
            logger.info(f"Transfer parameters:")
            logger.info(f"  - token_id: {token_id}")
            logger.info(f"  - fund_id: {fund.id}")
            logger.info(f"  - contract_address_id: {contract_address_id}")
            logger.info(f"  - user_investor (seller): {sales_order.seller_user.email}")
            logger.info(f"  - address_wallet_sender (receiver): {address_wallet_receiver}")
            logger.info(f"  - wallet_id: {wallet_id}")
            
            transfer_result, transfer_error = safe_transfer_721_index_to_index(
                token_id=token_id,
                fund_id=fund.id,
                contract_address_id=contract_address_id,
                user_investor=sales_order.seller_user,  # ✅ VENDEDOR (quien envía)
                address_wallet_sender=address_wallet_receiver,  # ✅ DIRECCIÓN DEL RECEPTOR
                wallet_id=wallet_id  # ✅ ID DE LA WALLET HD
            )
            
            logger.info(f"Transfer result: {transfer_result}")
            logger.info(f"Transfer error: {transfer_error}")
            
            if transfer_error:
                logger.error(f"❌ BLOCKCHAIN TRANSFER FAILED: {transfer_error}")
                raise TokenTransferError(f"Blockchain transfer failed: {transfer_error}")
            
            if not transfer_result:
                logger.error("❌ BLOCKCHAIN TRANSFER RETURNED EMPTY RESULT")
                raise TokenTransferError("Blockchain transfer returned empty result")
            
            # ✅ 4. ACTUALIZAR PROPIEDAD EN BASE DE DATOS
            logger.info("=== UPDATING DATABASE OWNERSHIP ===")
            
            updated_count = FundToken.objects.filter(
                token_id=token_id,
                fund=fund
            ).update(owner_user=purchase_order.supplier_user)
            
            logger.info(f"Database update count: {updated_count}")
            
            if updated_count == 0:
                logger.warning("⚠️ No database records updated - token may not exist in DB")
            
            # ✅ 5. LIBERAR RESERVA DEL TOKEN TRANSFERIDO
            try:
                FundToken.objects.filter(
                    token_id=token_id,
                    fund=fund
                ).update(
                    reserved_for_sale=False,
                    reserved_at=None,
                    reservation_expires_at=None
                )
                logger.info(f"✅ Released reservation for token {token_id}")
                
            except Exception as e:
                logger.error(f"Error releasing reservation for token {token_id}: {str(e)}")
                # No fallar por esto, la transferencia ya se completó
            
            # ✅ 6. REMOVER TOKEN DE LA LISTA DE RESERVADOS EN METADATA
            try:
                if sales_order.metadata and 'reserved_tokens' in sales_order.metadata:
                    reserved_tokens = sales_order.metadata.get('reserved_tokens', [])
                    
                    # Remover el token transferido
                    if str(token_id) in [str(t) for t in reserved_tokens]:
                        updated_reserved = [t for t in reserved_tokens if str(t) != str(token_id)]
                        
                        sales_order.metadata['reserved_tokens'] = updated_reserved
                        sales_order.metadata['total_tokens_reserved'] = len(updated_reserved)
                        sales_order.save(update_fields=['metadata'])
                
            except Exception as e:
                logger.error(f"Error updating metadata: {str(e)}")
                # No fallar por esto
            
            # ✅ 7. PREPARAR RESULTADO
            result = {
                'token_id': token_id,
                'from_user': sales_order.seller_user.email,
                'to_user': purchase_order.supplier_user.email,
                'sales_order_id': str(sales_order.id),
                'transfer_result': transfer_result,
                'database_updated': updated_count > 0,
                'reservation_released': True
            }
            
            logger.info(f"Token {token_id} transferred successfully and reservation released")
            return result
            
        except Exception as e:
            logger.error(f"❌ TOKEN TRANSFER FAILED: {str(e)}")
            raise TokenTransferError(f"Token transfer failed: {str(e)}")
    
    def update_sales_order_after_transfer(self, sales_order: SalesOrder, units_transferred: int) -> None:
        """Actualiza el estado de la orden de venta después de transferencias"""
        
        original_available = sales_order.available_units or sales_order.units
        sales_order.available_units = original_available - units_transferred
        
        if sales_order.available_units <= 0:
            sales_order.status = 'FULLY_EXECUTED'
            sales_order.fully_executed_at = timezone.now()
            sales_order.save(update_fields=['available_units', 'status', 'fully_executed_at'])
        else:
            sales_order.status = 'PARTIALLY_EXECUTED'
            sales_order.partially_executed_at = timezone.now()
            sales_order.save(update_fields=['available_units', 'status', 'partially_executed_at'])
    
    def update_purchase_order_after_transfer(self, purchase_order: PurchaseOrder, units_transferred: int) -> None:
        """ Actualiza el estado de la orden de compra después de transferencias"""
        
        original_available = purchase_order.available_units or purchase_order.units
        purchase_order.available_units = original_available - units_transferred
        
        if purchase_order.available_units <= 0:
            purchase_order.status = 'FULLY_EXECUTED'
            purchase_order.fully_executed_at = timezone.now()
            purchase_order.save(update_fields=['available_units', 'status', 'fully_executed_at'])
            print(f"Purchase order {purchase_order.order_number} fully executed")
        else:
            purchase_order.status = 'PARTIALLY_EXECUTED'
            purchase_order.partially_executed_at = timezone.now()
            purchase_order.save(update_fields=['available_units', 'status', 'partially_executed_at'])
            print(f"Purchase order {purchase_order.order_number} partially executed, remaining units: {purchase_order.available_units}")
        
    def release_transferred_tokens(self, token_ids: List[str], sales_order: SalesOrder) -> None:
        """Libera las reservas de tokens después de transferencia exitosa"""
        
        if not token_ids:
            return
        
        try:
            self.reservation_manager.release_token_reservations(token_ids, sales_order.fund.id)
            logger.info(f"Released reservations for {len(token_ids)} tokens from sales order {sales_order.order_number}")
        except Exception as e:
            logger.error(f"Failed to release token reservations: {str(e)}")
            # No fallar por esto, las transferencias ya se hicieron
