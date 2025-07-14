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
        """Ejecuta la transferencia de un token individual"""
        
        logger.info(f"=== STARTING TOKEN TRANSFER ===")
        logger.info(f"Token ID: {token_id}")
        logger.info(f"From: {sales_order.seller_user.email}")
        logger.info(f"To: {purchase_order.supplier_user.email}")
        logger.info(f"Fund ID: {purchase_order.fund.id}")
        
        try:
            from apps.kaleido.utils import safe_transfer_721, get_wallet_index
            
            # 1. Get wallet addresses
            logger.info("=== GETTING WALLET ADDRESSES ===")
            
            sender_wallet = get_wallet_index(sales_order.seller_user, purchase_order.fund.id)
            logger.info(f"Sender wallet result: {sender_wallet}")
            
            receiver_wallet = get_wallet_index(purchase_order.supplier_user, purchase_order.fund.id)
            logger.info(f"Receiver wallet result: {receiver_wallet}")
            
            if not sender_wallet or not receiver_wallet:
                error_msg = f"Wallet address not found - Sender: {bool(sender_wallet)}, Receiver: {bool(receiver_wallet)}"
                logger.error(error_msg)
                raise TokenTransferError(error_msg)
            
            # 2. Execute blockchain transfer
            logger.info("=== EXECUTING BLOCKCHAIN TRANSFER ===")
            logger.info(f"Transfer parameters:")
            logger.info(f"  - token_id: {token_id}")
            logger.info(f"  - fund_id: {purchase_order.fund.id}")
            logger.info(f"  - from_user: {sales_order.seller_user}")
            logger.info(f"  - to_user: {purchase_order.supplier_user}")
            
            transfer_result, transfer_error = safe_transfer_721(
                token_id=token_id,
                fund_id=purchase_order.fund.id,
                from_user=sales_order.seller_user,
                to_user=purchase_order.supplier_user
            )
            
            logger.info(f"Transfer result: {transfer_result}")
            logger.info(f"Transfer error: {transfer_error}")
            
            if transfer_error:
                logger.error(f"❌ BLOCKCHAIN TRANSFER FAILED: {transfer_error}")
                raise TokenTransferError(f"Blockchain transfer failed: {transfer_error}")
            
            if not transfer_result:
                logger.error("❌ BLOCKCHAIN TRANSFER RETURNED EMPTY RESULT")
                raise TokenTransferError("Blockchain transfer returned empty result")
            
            # 3. Update database ownership
            logger.info("=== UPDATING DATABASE OWNERSHIP ===")
            
            updated_count = FundToken.objects.filter(
                token_id=token_id,
                fund=purchase_order.fund
            ).update(owner_user=purchase_order.supplier_user)
            
            logger.info(f"Database update count: {updated_count}")
            
            if updated_count == 0:
                logger.warning("⚠️ No database records updated - token may not exist in DB")
            
            # 4. Release token reservation
            logger.info("=== RELEASING TOKEN RESERVATION ===")
            
            try:
                from apps.trading.security.token_validators import TokenReservationManager
                manager = TokenReservationManager()
                release_result = manager.release_token_reservations([token_id], purchase_order.fund.id)
                logger.info(f"Release result: {release_result}")
            except Exception as e:
                logger.error(f"Error releasing reservation: {str(e)}")
            
            # 5. Update metadata
            logger.info("=== UPDATING METADATA ===")
            
            try:
                if sales_order.metadata and 'reserved_tokens' in sales_order.metadata:
                    reserved_tokens = sales_order.metadata.get('reserved_tokens', [])
                    if str(token_id) in [str(t) for t in reserved_tokens]:
                        updated_reserved = [t for t in reserved_tokens if str(t) != str(token_id)]
                        sales_order.metadata['reserved_tokens'] = updated_reserved
                        sales_order.save(update_fields=['metadata'])
                        logger.info(f"✅ Removed token {token_id} from reserved list")
            except Exception as e:
                logger.error(f"Error updating metadata: {str(e)}")
            
            logger.info("=== TOKEN TRANSFER COMPLETED SUCCESSFULLY ===")
            
            return {
                'success': True,
                'token_id': token_id,
                'from_user': sales_order.seller_user.email,
                'to_user': purchase_order.supplier_user.email,
                'transfer_result': transfer_result,
                'database_updated': updated_count > 0
            }
            
        except Exception as e:
            logger.error(f"=== TOKEN TRANSFER FAILED ===")
            logger.error(f"Error: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                'success': False,
                'token_id': token_id,
                'error': str(e),
                'error_type': type(e).__name__
            }    
    
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
