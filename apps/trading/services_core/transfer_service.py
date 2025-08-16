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
        
        # 1. ✅ CORREGIDO: Buscar selección que contenga esta PO en sus items
        selection = self._get_active_selection_for_purchase_order(purchase_order)
        if not selection:
            raise TransferServiceError("La seleccion de matches no existe para esta purchase order")
        
        if selection.is_expired:
            raise TransferServiceError("La seleccion ha expirado")
        
        # 2. Marcar seleccion como procesando
        selection.status = MatchSelection.MatchSelectionStatus.PROCESSING
        selection.save(update_fields=['status'])
        
        # 3. ✅ PROCESAR SOLO LOS ITEMS DE ESTA PURCHASE ORDER
        po_items = selection.items.filter(purchase_order=purchase_order).select_related(
            'sales_order', 'purchase_order'
        )
        
        if not po_items.exists():
            raise TransferServiceError("No hay items válidos para esta purchase order en la selección")
        
        # 4. Procesar cada item de la seleccion
        transfer_results = []
        transfer_errors = []
        total_transferred = 0
        
        for item in po_items:
            try:
                # ✅ CORREGIDO: Método correcto
                item_result = self._execute_item_transfers(purchase_order, item)
                
                # ✅ MEJORADO: Manejo más robusto de resultados
                successful = item_result.get('successful', [])
                errors = item_result.get('errors', [])
                
                if successful:
                    transfer_results.extend(successful)
                    total_transferred += len(successful)
                
                if errors:
                    transfer_errors.extend(errors)
                    
            except Exception as e:
                error_detail = {
                    'item_id': str(item.id),
                    'sales_order_id': str(item.sales_order.id),
                    'sales_order_number': item.sales_order.order_number,
                    'units_attempted': item.units,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                }
                transfer_errors.append(error_detail)
                print(f"❌ Error procesando item {item.id}: {str(e)}")
        
        # 5. ✅ MEJORADO: Mejor lógica de estado final
        if total_transferred == 0:
            # Sin transferencias exitosas
            selection.status = MatchSelection.MatchSelectionStatus.FAILED
        elif transfer_errors:
            # Transferencias parciales
            selection.status = MatchSelection.MatchSelectionStatus.PARTIALLY_COMPLETED
        else:
            # Todas las transferencias exitosas
            selection.status = MatchSelection.MatchSelectionStatus.COMPLETED
            
        selection.save(update_fields=['status'])
        
        print(f"🔍 Transfer completed - Status: {selection.status}")
        print(f"🔍 Successful transfers: {total_transferred}")
        print(f"🔍 Transfer errors: {len(transfer_errors)}")
        
        # 6. ✅ MEJORADO: Retornar resultados más completos
        return {
            'successful': transfer_results,
            'errors': transfer_errors,
            'total_transferred': total_transferred,
            'total_errors': len(transfer_errors),
            'matches_processed': po_items.count(),
            'selection_final_status': selection.status,
            'selection_id': str(selection.id),
            'purchase_order_id': str(purchase_order.id)
        }
        
    # ==========================================
    # Funciones Auxiliares CORREGIDAS
    # ==========================================
        
    def _execute_item_transfers(
        self, 
        purchase_order: PurchaseOrder, 
        item
    ) -> Dict[str, List]:
        """Ejecuta transferencias para un item específico de selección"""
        
        successful_transfers = []
        failed_transfers = []
        
        # ✅ DEBUG: Verificar que los objetos estén correctos
        print(f"🔍 DEBUG _execute_item_transfers:")
        print(f"   - Purchase Order: {purchase_order.id} - {purchase_order.order_number}")
        print(f"   - Sales Order: {item.sales_order.id} - {item.sales_order.order_number}")
        print(f"   - Item units: {item.units}")
        
        try:
            # 1. Obtener tokens reservados para este sales order
            reserved_tokens = self._get_reserved_tokens_for_sales_order(
                item.sales_order, item.units
            )
            
            if len(reserved_tokens) < item.units:
                raise TransferServiceError(
                    f"Insufficient reserved tokens. Need {item.units}, got {len(reserved_tokens)}"
                )
            
            print(f"🔍 Reserved tokens found: {reserved_tokens[:item.units]}")
            
            # 2. Ejecutar transferencias individuales
            for token_id in reserved_tokens[:item.units]:
                try:
                    # ✅ ASEGURAR que todos los parámetros estén correctos
                    print(f"🔍 Executing transfer for token {token_id}")
                    
                    transfer_record = self._execute_single_transfer(
                        purchase_order=purchase_order,  # ✅ Pasar explícitamente
                        sales_order=item.sales_order,   # ✅ Pasar explícitamente
                        match_item=item,
                        token_id=token_id
                    )
                    
                    successful_transfers.append({
                        'token_id': token_id,
                        'transfer_record_id': str(transfer_record.id),
                        'transaction_uuid': transfer_record.transaction_uuid,
                        'sales_order_id': str(item.sales_order.id),
                        'sales_order_number': item.sales_order.order_number,
                        'from_user': item.sales_order.seller_user.email,
                        'to_user': purchase_order.supplier_user.email,
                        'completed_at': transfer_record.completed_at.isoformat() if transfer_record.completed_at else None
                    })
                    
                except Exception as e:
                    error_msg = f"Error transferring token {token_id}: {str(e)}"
                    print(f"❌ {error_msg}")
                    
                    failed_transfers.append({
                        'token_id': token_id,
                        'sales_order_id': str(item.sales_order.id),
                        'sales_order_number': item.sales_order.order_number,
                        'error': str(e),
                        'timestamp': timezone.now().isoformat()
                    })
            
        except Exception as e:
            error_msg = f"Error en preparación de transferencias: {str(e)}"
            print(f"❌ {error_msg}")
            
            failed_transfers.append({
                'item_id': str(item.id),
                'sales_order_id': str(item.sales_order.id),
                'error': error_msg,
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
        
        # 1. ✅ CORREGIDO: Crear registro con campos correctos
        transfer_record = TokenTransferRecord.objects.create(
            selection=match_item.selection,
            selection_item=match_item,
            purchase_order=purchase_order,  # ✅ ASEGURAR que se asigne
            sales_order=sales_order,        # ✅ ASEGURAR que se asigne
            token_id=token_id,
            from_user=sales_order.seller_user,
            to_user=purchase_order.supplier_user,
            status='PENDING',
            metadata={'created_via': 'core_transfer_service'}
        )
        
        try:
            # 2. Marcar como en progreso
            transfer_record.status = 'IN_PROGRESS'
            transfer_record.save(update_fields=['status'])
            
            # 3. Ejecutar transferencia blockchain
            blockchain_result = self._execute_blockchain_transfer(
                token_id, sales_order, purchase_order
            )
            
            # 4. ✅ CORREGIDO: Actualizar registro como completado
            transfer_record.status = 'COMPLETED'
            transfer_record.completed_at = timezone.now()  # ✅ Campo correcto
            transfer_record.transaction_uuid = blockchain_result.get('tx_id')
            transfer_record.metadata.update({
                'blockchain_result': blockchain_result,
                'transfer_method': 'direct_blockchain',
                'completed_at': timezone.now().isoformat()
            })
            transfer_record.save(update_fields=[
                'status', 'completed_at', 'transaction_uuid', 'metadata'
            ])
            
            # 5. Actualizar propiedad del token en base de datos
            self._update_token_ownership(token_id, purchase_order.supplier_user)
            
            # 6. Liberar reserva
            self.reservation_manager.release_token_reservations(
                [token_id], 
                purchase_order.fund.id
            )
    
            return transfer_record
            
        except Exception as e:
            # ✅ CORREGIDO: Marcar como fallida
            transfer_record.status = 'FAILED'
            transfer_record.metadata.update({
                'error': str(e),
                'failed_at': timezone.now().isoformat()
            })
            transfer_record.save(update_fields=['status', 'metadata'])
            raise TransferServiceError(f"Transfer failed for token {token_id}: {str(e)}")

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

    def _get_active_selection_for_purchase_order(self, purchase_order: PurchaseOrder) -> MatchSelection:
        """
        ✅ CORREGIDO: Busca selecciones que incluyan esta purchase order en sus items
        """
        try:
            # Buscar selecciones que incluyan esta purchase order en sus items
            selection = MatchSelection.objects.filter(
                items__purchase_order=purchase_order,
                status__in=['ACTIVE', 'PROCESSING']  # Permitir PROCESSING también
            ).select_related('sales_order').prefetch_related(
                'items__purchase_order',
                'items__sales_order'
            ).first()
            
            return selection
            
        except Exception as e:
            print(f"❌ Error buscando selección activa: {str(e)}")
            return None