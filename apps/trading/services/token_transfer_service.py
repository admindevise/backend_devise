from django.utils import timezone
from typing import Dict, Any, List
import logging

from apps.trading.models import PurchaseOrder, SalesOrder
from apps.fund.models import FundToken
from apps.kaleido.utils import safe_transfer_721
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
    
    def execute_transfers(self, purchase_order: PurchaseOrder) -> dict:
        """Ejecuta todas las transferencias de tokens para una orden de compra"""
        
        transferred_tokens = []
        transfer_errors = []
        
        # Validar metadatos
        if not (hasattr(purchase_order, 'metadata') and purchase_order.metadata):
            raise TokenTransferError("No se encontraron metadatos de selección en la orden")
        
        selected_matches = purchase_order.metadata.get('selected_matches', [])
        
        if not selected_matches:
            raise TokenTransferError("No se encontraron matches seleccionados para transferir")
        
        logger.info(f"Starting token transfers for order {purchase_order.order_number}: {len(selected_matches)} matches")
        
        # Procesar cada match
        for i, match in enumerate(selected_matches):
            try:
                match_result = self.process_match_transfer(purchase_order, match)
                transferred_tokens.extend(match_result['successful'])
                transfer_errors.extend(match_result['errors'])
                
                logger.info(f"Match {i+1}/{len(selected_matches)} processed: {len(match_result['successful'])} tokens transferred")
                
            except Exception as e:
                error_msg = f"Error processing match {i+1}: {str(e)}"
                transfer_errors.append({
                    'sales_order_id': match.get('sales_order_id'),
                    'match_index': i,
                    'error': error_msg
                })
                logger.error(error_msg)
        
        # Verificar que al menos algunos tokens se transfirieron
        if not transferred_tokens:
            raise TokenTransferError("No se pudo transferir ningún token. Revisa las reservas de los vendedores.")
        
        result = {
            'successful': transferred_tokens,
            'errors': transfer_errors,
            'total_transferred': len(transferred_tokens),
            'total_errors': len(transfer_errors),
            'matches_processed': len(selected_matches)
        }
        
        logger.info(f"Token transfers completed for order {purchase_order.order_number}: {result['total_transferred']} tokens transferred, {result['total_errors']} errors")
        
        return result
    
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
            
            # Liberar reservas de tokens transferidos exitosamente
            transferred_token_ids = [t['token_id'] for t in successful_transfers]
            self.release_transferred_tokens(transferred_token_ids, sales_order)
        
        return {
            'successful': successful_transfers,
            'errors': transfer_errors
        }
    
    def get_reserved_tokens_for_transfer(self, sales_order: SalesOrder, units_needed: int) -> List[str]:
        """Obtiene tokens reservados para transferencia con validación"""
        
        # ✅ DEBUGGING COMPLETO
        logger.info(f"=== DEBUGGING SALES ORDER {sales_order.id} ===")
        logger.info(f"Order Number: {sales_order.order_number}")
        logger.info(f"Order Status: {sales_order.status}")
        logger.info(f"Seller: {sales_order.seller_user.email}")
        logger.info(f"Units needed: {units_needed}")
        
        # Verificar reserved_tokens_info
        if hasattr(sales_order, 'reserved_tokens_info'):
            logger.info(f"reserved_tokens_info exists: {sales_order.reserved_tokens_info}")
        else:
            logger.info("reserved_tokens_info: NOT FOUND")
        
        # Verificar metadata
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
        
        # Opción 1: reserved_tokens_info (estructura actual)
        if hasattr(sales_order, 'reserved_tokens_info') and sales_order.reserved_tokens_info:
            token_ids = sales_order.reserved_tokens_info.get('token_ids', [])
            available_tokens = token_ids[:units_needed]
            logger.info(f"✅ Found {len(token_ids)} tokens in reserved_tokens_info")
            
            if len(available_tokens) < units_needed:
                logger.error(f"❌ INSUFFICIENT TOKENS in reserved_tokens_info: Need {units_needed}, Found {len(available_tokens)}")
                raise TokenTransferError(
                    f"Vendedor no tiene suficientes tokens reservados en reserved_tokens_info. "
                    f"Necesario: {units_needed}, Disponible: {len(available_tokens)}"
                )
            
            return available_tokens
        
        # Opción 2: metadata.reserved_tokens (estructura legacy)
        if sales_order.metadata and sales_order.metadata.get('reserved_tokens'):
            token_ids = sales_order.metadata.get('reserved_tokens', [])
            available_tokens = token_ids[:units_needed]
            logger.info(f"✅ Found {len(token_ids)} tokens in metadata (legacy)")
            
            if len(available_tokens) < units_needed:
                logger.error(f"❌ INSUFFICIENT TOKENS in metadata: Need {units_needed}, Found {len(available_tokens)}")
                raise TokenTransferError(
                    f"Vendedor no tiene suficientes tokens reservados en metadata. "
                    f"Necesario: {units_needed}, Disponible: {len(available_tokens)}"
                )
            
            return available_tokens
        
        # ✅ Opción 3: RESERVA AUTOMÁTICA como fallback
        logger.warning(f"⚠️ No reserved tokens found. Attempting automatic reservation...")
        
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
        """Ejecuta la transferencia de un token individual"""
        
        logger.info(f"Transferring token {token_id} from {sales_order.seller_user.email} to {purchase_order.supplier_user.email}")
        
        from apps.kaleido.utils import safe_transfer_721_index_to_index, get_wallet_index
        
        address_wallet_sender = get_wallet_index(sales_order.seller_user, purchase_order.fund.id)
        if not address_wallet_sender:
            raise TokenTransferError(f"Wallet address not found for user {sales_order.seller_user.email}")
        
        # TRANSFERENCIA CORRECTA: De un usuario a otro usuario
        transfer_result, transfer_error = safe_transfer_721_index_to_index(
            token_id=token_id,
            fund_id=purchase_order.fund.id,
            contract_address_id=purchase_order.fund.token_contract_721.contract_address,
            user_investor=sales_order.seller_user,
            address_wallet_sender= address_wallet_sender,
            wallet_id=purchase_order.fund.hd_wallet.id_wallet,
        )
        
        if transfer_error:
            raise TokenTransferError(f"Blockchain transfer failed: {transfer_error}")
        
        # Actualizar propiedad en base de datos
        updated_count = FundToken.objects.filter(
            token_id=token_id,
            fund=purchase_order.fund
        ).update(owner_user=purchase_order.supplier_user)
        
        if updated_count == 0:
            logger.warning(f"No FundToken record found for token_id {token_id} in fund {purchase_order.fund.id}")
            
        try:
            FundToken.objects.filter(
                token_id=token_id,
                fund=purchase_order.fund
            ).update(
                reserved_for_sale=False,
                reserved_at=None,
                reservation_expires_at=None
            )
            logger.info(f"✅ Released reservation for token {token_id}")
            
        except Exception as e:
            logger.error(f"Error releasing reservation for token {token_id}: {str(e)}")
            # No fallar por esto, la transferencia ya se completó
        
        # ✅ 3. REMOVER TOKEN DE LA LISTA DE RESERVADOS EN METADATA
        try:
            if sales_order.metadata and 'reserved_tokens' in sales_order.metadata:
                reserved_tokens = sales_order.metadata.get('reserved_tokens', [])
                
                # Remover el token transferido
                if str(token_id) in [str(t) for t in reserved_tokens]:
                    updated_reserved = [t for t in reserved_tokens if str(t) != str(token_id)]
                    sales_order.metadata['reserved_tokens'] = updated_reserved
                    sales_order.save(update_fields=['metadata'])
                    logger.info(f"✅ Removed token {token_id} from reserved list in metadata")
            
        except Exception as e:
            logger.error(f"Error updating metadata: {str(e)}")
            # No fallar por esto
        
        # Preparar resultado
        result = {
            'token_id': token_id,
            'from_user': sales_order.seller_user.email,
            'to_user': purchase_order.supplier_user.email,
            'sales_order_id': str(sales_order.id),
            'transfer_result': transfer_result,
            'database_updated': updated_count > 0,
            'reservation_released': True  # ✅ Nuevo campo
        }
        
        logger.info(f"Token {token_id} transferred successfully and reservation released")
        return result
    
    def update_sales_order_after_transfer(self, sales_order: SalesOrder, units_transferred: int) -> None:
        """Actualiza el estado de la orden de venta después de transferencias"""
        
        original_available = sales_order.available_units or sales_order.units
        sales_order.available_units = original_available - units_transferred
        
        if sales_order.available_units <= 0:
            sales_order.status = 'FULLY_EXECUTED'
            sales_order.fully_executed_at = timezone.now()
            sales_order.save(update_fields=['available_units', 'status', 'fully_executed_at'])
            logger.info(f"Sales order {sales_order.order_number} fully executed")
        else:
            sales_order.status = 'PARTIALLY_EXECUTED'
            sales_order.partially_executed_at = timezone.now()
            sales_order.save(update_fields=['available_units', 'status', 'partially_executed_at'])
            logger.info(f"Sales order {sales_order.order_number} partially executed: {sales_order.available_units} units remaining")
    
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
