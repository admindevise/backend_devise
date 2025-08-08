from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Any

from apps.trading.models.selection_models import (
    MatchSelection,
    TokenTransferRecord
)
from apps.trading.models.core_models import PurchaseOrder
from apps.trading.security.token_validators import TokenReservationManager

class TransferServiceError(Exception):
    pass

class TokenTransferService:
    """Servicio dedicado para manejo de transferencias de tokens"""
    
    def __init__(self):
        self.reservation_manager = TokenReservationManager()
        
    @transaction.atomic
    def execute_selection_transfers(
        self,
        purchase_order: PurchaseOrder
    ) -> Dict[str, Any]:
        """Ejecuta las transferencias de tokens basadas en la selección activa"""
        
        # 1. Obtener seleccion activa
        try:
            selection = purchase_order.match_selection
        except MatchSelection.DoesNotExist:
            raise TransferServiceError("La seleccion de matches no existe")
        
        if selection.is_expired:
            raise TransferServiceError("La seleccion ha expirado")
        
        # 2. Marcar seleccion como procesando
        selection.status = MatchSelection.MatchSelectionStatus.PROCESSING
        selection.save(update_fields=['status'])
        
        # 3. Procesar cada item de la seleccion
        transfer_results = []
        transfer_errors = []
        
        for item in selection.items.select_realted('sales_order'):
            try:
                item_results = self._execute_item_transfers(
                    purchase_order, item
                )
                transfer_results.extend(item_results['successful'])
                transfer_errors.extend(item_results['errors'])
                
            except Exception as e:
                transfer_errors.append({
                    'item_id': item.id,
                    'sales_order_id': str(item.sales_order.id),
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                })
        
        # 4. Actualizar estado de seleccion
        if transfer_errors:
            selection.status = MatchSelection.MatchSelectionStatus.COMPLETED
        else:
            selection.status = MatchSelection.MatchSelectionStatus.COMPLETED
        
        selection.metadata.update({
            'transfers_completed_at': timezone.now().isoformat(),
            'successful_transfers': len(transfer_results),
            'failed_transfers': len(transfer_errors)
        })
        selection.save(update_fields=['status', 'metadata'])
        
        return {
            'successful': transfer_results,
            'errors': transfer_errors,
            'total_transferred': len(transfer_results),
            'total_errors': len(transfer_errors),
            'selection_id': selection.id,
            'completed_at': timezone.now().isoformat()
        }
        
        
    # ==========================================
    # Funciones Auxiliares
    # ==========================================
        
    def _execute_item_transfers(
            self, 
            purchase_order: PurchaseOrder, 
            item
        ) -> Dict[str, List]:
            """Ejecuta transferencias para un item específico de selección"""
            
            successful_transfers = []
            failed_transfers = []
            
            # 1. Obtener tokens reservados para este sales order
            reserved_tokens = self._get_reserved_tokens_for_sales_order(
                item.sales_order, item.units
            )
            
            if len(reserved_tokens) < item.units:
                raise TransferServiceError(
                    f"Insufficient reserved tokens. Need {item.units}, got {len(reserved_tokens)}"
                )
            
            # 2. Ejecutar transferencias individuales
            for token_id in reserved_tokens[:item.units]:
                try:
                    transfer_record = self._execute_single_transfer(
                        purchase_order=purchase_order,
                        sales_order=item.sales_order,
                        match_item=item,
                        token_id=token_id
                    )
                    
                    successful_transfers.append({
                        'token_id': token_id,
                        'transfer_record_id': transfer_record.id,
                        'blockchain_tx_id': transfer_record.blockchain_tx_id,
                        'sales_order_id': str(item.sales_order.id),
                        'completed_at': transfer_record.completed_at.isoformat()
                    })
                    
                except Exception as e:
                    failed_transfers.append({
                        'token_id': token_id,
                        'sales_order_id': str(item.sales_order.id),
                        'error': str(e),
                        'timestamp': timezone.now().isoformat()
                    })
            
            return {
                'successful': successful_transfers,
                'errors': failed_transfers
            }
    
    @transaction.atomic
    def _execute_single_transfer(
        self,
        purchase_order: PurchaseOrder,
        sales_order,
        match_item,
        token_id: str
    ) -> TokenTransferRecord:
        """Ejecuta una transferencia individual de token"""
        
        # 1. Crear registro de transferencia
        transfer_record = TokenTransferRecord.objects.create(
            purchase_order=purchase_order,
            sales_order=sales_order,
            match_item=match_item,
            token_id=token_id,
            from_user=sales_order.seller_user,
            to_user=purchase_order.supplier_user,
            status='PENDING'
        )
        
        try:
            # 2. Marcar como en progreso
            transfer_record.status = 'IN_PROGRESS'
            transfer_record.save(update_fields=['status'])
            
            # 3. Ejecutar transferencia blockchain
            blockchain_result = self._execute_blockchain_transfer(
                token_id, sales_order, purchase_order
            )
            
            # 4. Actualizar registro como completado
            transfer_record.status = 'COMPLETED'
            transfer_record.completed_at = timezone.now()
            transfer_record.blockchain_tx_id = blockchain_result.get('tx_id')
            transfer_record.gas_used = blockchain_result.get('gas_used') or 'gas_user_test'
            transfer_record.metadata = {
                'blockchain_result': blockchain_result,
                'transfer_method': 'direct_blockchain'
            }
            transfer_record.save()
            
            # 5. Actualizar propiedad del token en base de datos
            self._update_token_ownership(token_id, purchase_order.supplier_user)
            
            # 6. Liberar reserva
            self.reservation_manager.release_token_reservations(
                [token_id], 
                purchase_order.fund.id
                )
    
            return transfer_record
            
        except Exception as e:
            # Marcar como fallida
            transfer_record.status = TokenTransferRecord.TokenTransferStatus.FAILED
            transfer_record.metadata = {
                'error': str(e),
                'failed_at': timezone.now().isoformat
            }
            transfer_record.save()
            raise
    
    def _execute_blockchain_transfer(
        self,
        token_id: str, 
        sales_order, 
        purchase_order: PurchaseOrder
    ) -> Dict[str, Any]:
        """Transfiere token desde metodo safe_transfer"""
        
        from apps.kaleido.utils import safe_transfer_721_index_to_index, get_wallet_index
        
        # 1. Obtener direccion de la wallet del receptor (comprador)
        receiver_wallet_data, receiver_error = get_wallet_index(purchase_order.supplier_user, purchase_order.fund.id)
        
        if receiver_error:
            raise TransferServiceError(f"Error obteniendo la wallet del comprador en proceso de transferencia de token: {receiver_error}")
        
        address_wallet_receiver = receiver_wallet_data.get('address')
        
        # 2. Obtener datos del fondo
        fund = purchase_order.fund
        contract_address_id = fund.token_contract_721.contract_address
        wallet_id = fund.hd_wallet.id_wallet
        
        # 3. Llamada al metodo safe_transfer
        transfer_result, transfer_error = safe_transfer_721_index_to_index(
            token_id=token_id,
            fund_id=fund.id,
            contract_address_id=contract_address_id,
            user_investor=sales_order.seller_user,  # Vendedor (quien envia)
            address_wallet_sender=address_wallet_receiver,
            wallet_id=wallet_id # ID de HD-Wallet
        )
        
        # 4. Manejo de la respuesta
        if transfer_error:
            raise TransferServiceError(f"Transaccion fallida en safe_transfer: {transfer_error}")
        
        if not transfer_result:
            raise TransferServiceError(f"Transaccion fallida en safe_transfer: No hay respuesta de safe_transfer")
        
        return {
            'tx_id': transfer_result.get('id'),
            'status': 'success',
            'token_id': token_id,
            'from_user': sales_order.seller_user.email,
            'to_user': purchase_order.supplier_user.email,
            'transfer_result_safe_transfer': transfer_result
        }

    
    def _update_token_ownership(self, token_id: str, new_owner):
        """Actualiza la propiedad del token en base de datos"""
        
        from apps.fund.models import FundToken
        
        try:
            fund_token = FundToken.objects.get(token_id=token_id)
            old_owner = fund_token.owner_user
            
            # Actualizar propietario
            fund_token.owner_user = new_owner
            fund_token.save(update_fields=['owner_user'])
            
            print(f"El propietario se ha actualizado antes: {old_owner}, ahora: {fund_token.owner_user}")
        
        except FundToken.DoesNotExist:
            raise TransferServiceError(f"El token {token_id} no existe")                
        except Exception as e:
            raise TransferServiceError(f"Erro inesperado en la ejecucion de actualizar ownership {e}")
    
    def _get_reserved_tokens_for_sales_order(self, sales_order, required_units: int) -> List[str]:
        """Obtiene tokens reservados para una sales order específica"""
        
        # Verificar en reserved_tokens_info (nuevo formato)
        if hasattr(sales_order, 'reserved_tokens_info') and sales_order.reserved_tokens_info:
            reserved_tokens = sales_order.reserved_tokens_info.get('reserved_tokens', [])
            if len(reserved_tokens) >= required_units:
                return reserved_tokens[:required_units]
        
        # Fallback a metadata (formato anterior)
        if sales_order.metadata and 'reserved_tokens' in sales_order.metadata:
            reserved_tokens = sales_order.metadata['reserved_tokens']
            if len(reserved_tokens) >= required_units:
                return reserved_tokens[:required_units]
        
        raise TransferServiceError(
            f"No hay suficientes tokens reservados para la orden de compra {sales_order.id}. "
            f"Requeridos: {required_units}, Disponibles: {len(reserved_tokens) if 'reserved_tokens' in locals() else 0}"
        )