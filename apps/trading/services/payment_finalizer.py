from django.utils import timezone
from typing import List
import logging

from apps.trading.models import PurchaseOrder, SalesOrder
from apps.audit.audit_service import AuditService

logger = logging.getLogger('trading.payment_finalizer')

class PaymentFinalizerService:
    """
    ✅ Servicio de Finalización de Pagos - Maneja la finalización y auditoría
    
    Responsabilidades:
    - Actualizar metadatos finales
    - Actualizar estados finales de órdenes
    - Registrar auditoría completa
    - Construir respuestas
    """
    
    def finalize_payment(
        self, 
        purchase_order: PurchaseOrder, 
        payment_result: dict, 
        transfer_result: dict,
        user,
        request=None
    ) -> dict:
        """Finaliza el proceso completo de pago"""
        
        # 1. Actualizar metadatos
        self.update_order_metadata(purchase_order, payment_result, transfer_result)
        
        # 2. Actualizar estado final
        self.update_final_order_status(purchase_order)
        
        transactions_created = self.create_transactions(
            purchase_order=purchase_order, 
            transfer_result=transfer_result, 
            user=user,
            request=request
        )
        
        # 3. Registrar auditoría
        self.log_payment_success(purchase_order, payment_result, transfer_result, user, request)
        
        # 4. Construir respuesta
        return self.build_success_response(
            purchase_order, 
            payment_result, 
            transfer_result, 
            transactions_created)
    
    def create_transactions(
        self, 
        purchase_order: PurchaseOrder, 
        transfer_result: dict, 
        user,
        request=None
    ) -> List[dict]:
        """
        Crea registros de transacciones formales por cada match ejecutado
        """
        from apps.trading.models import Transaction
        
        transactions_created = []
        
        if not purchase_order.metadata:
            logger.warning(f"Cannot create transactions for order {purchase_order.id}: no metadata")
            return transactions_created
        
        selected_matches = purchase_order.metadata.get('selected_matches', [])
        
        # Agrupar transferencias exitosas por sales_order_id
        transfers_by_sales_order = {}
        for transfer in transfer_result['successful']:
            sales_order_id = transfer['sales_order_id']
            if sales_order_id not in transfers_by_sales_order:
                transfers_by_sales_order[sales_order_id] = []
            transfers_by_sales_order[sales_order_id].append(transfer)
        
        # Crear una transacción por cada sales order que tuvo transferencias exitosas
        for match in selected_matches:
            sales_order_id = match.get('sales_order_id')
            units_requested = match.get('units', 0)
            
            if not sales_order_id or sales_order_id not in transfers_by_sales_order:
                continue
            
            try:
                # Obtener la sales order
                sales_order = SalesOrder.objects.get(id=sales_order_id)
                
                # Contar tokens transferidos para esta sales order
                transferred_tokens = transfers_by_sales_order[sales_order_id]
                units_transferred = len(transferred_tokens)
                
                if units_transferred == 0:
                    continue
                
                # Crear registro de transacción
                transaction = Transaction.objects.create(
                    purchase_order=purchase_order,
                    sales_order=sales_order,
                    buyer=purchase_order.supplier_user,  # Usuario que compra
                    seller=sales_order.seller_user,     # Usuario que vende
                    fund=purchase_order.fund,
                    units=units_transferred,
                    price_per_unit=sales_order.price_per_unit,
                    total_amount=units_transferred * sales_order.price_per_unit,
                    
                    # Metadatos adicionales
                    metadata={
                        'transferred_tokens': [t['token_id'] for t in transferred_tokens],
                        'transfer_details': transferred_tokens,
                        'units_requested': units_requested,
                        'units_transferred': units_transferred,
                        'blockchain_confirmed': True,
                        'created_via': 'payment_execution_service',
                        'payment_reference': purchase_order.metadata.get('payment_data', {}).get('reference'),
                        'execution_flow': 'select_matches -> pay_selection -> token_transfer'
                    }
                )
                
                transaction_info = {
                    'transaction_id': str(transaction.id),
                    'sales_order_id': str(sales_order.id),
                    'sales_order_number': sales_order.order_number,
                    'buyer': purchase_order.supplier_user.email,
                    'seller': sales_order.seller_user.email,
                    'units_transferred': units_transferred,
                    'price_per_unit': float(sales_order.price_per_unit),
                    'total_amount': float(transaction.total_amount),
                    'tokens_transferred': [t['token_id'] for t in transferred_tokens]
                }
                
                transactions_created.append(transaction_info)
                
                logger.info(
                    f"✅ Transaction created: {transaction.id} - "
                    f"{units_transferred} units from {sales_order.order_number} to {purchase_order.order_number}"
                )
                
                # ✅ DEBUGGING: Verificar que se creó correctamente
                logger.info(f"=== TRANSACTION CREATED ===")
                logger.info(f"Transaction ID: {transaction.id}")
                logger.info(f"Purchase Order: {purchase_order.order_number}")
                logger.info(f"Sales Order: {sales_order.order_number}")
                logger.info(f"Buyer: {purchase_order.supplier_user.email}")
                logger.info(f"Seller: {sales_order.seller_user.email}")
                logger.info(f"Units: {units_transferred}")
                logger.info(f"Total Amount: {transaction.total_amount}")
                logger.info(f"Created At: {transaction.created_at}")

                # ✅ VERIFICAR EN BASE DE DATOS
                db_transaction = Transaction.objects.get(id=transaction.id)
                logger.info(f"Verified in DB: {db_transaction.id} exists")
                
                # Registrar auditoría de transacción individual
                """ if request:
                    try:
                        AuditService.log_action(
                            request=request,
                            action_code='TRANSACTION_CREATED',
                            obj=transaction,
                            details={
                                'transaction_id': str(transaction.id),
                                'purchase_order_id': str(purchase_order.id),
                                'sales_order_id': str(sales_order.id),
                                'buyer_id': str(purchase_order.supplier_user.id),
                                'seller_id': str(sales_order.seller_user.id),
                                'units_transferred': units_transferred,
                                'total_amount': float(transaction.total_amount),
                                'tokens_transferred': [t['token_id'] for t in transferred_tokens],
                                'created_via': 'payment_execution_service'
                            },
                            status='SUCCESS'
                        )
                    except Exception as e:
                        logger.error(f"Failed to log transaction audit: {str(e)}") """
                
            except SalesOrder.DoesNotExist:
                logger.error(f"Sales order {sales_order_id} not found for transaction creation")
                continue
            except Exception as e:
                logger.error(f"Error creating transaction for sales order {sales_order_id}: {str(e)}")
                continue
        
        logger.info(f"Created {len(transactions_created)} transactions for purchase order {purchase_order.order_number}")
        return transactions_created    
    
    def update_order_metadata(
        self, 
        purchase_order: PurchaseOrder, 
        payment_result: dict, 
        transfer_result: dict
    ) -> None:
        """Actualiza los metadatos de la orden con información completa"""
        
        if not hasattr(purchase_order, 'metadata') or not purchase_order.metadata:
            logger.warning(f"Purchase order {purchase_order.id} has no metadata to update")
            return
        
        metadata = purchase_order.metadata.copy()
        
        # Información REAL de transferencias
        metadata.update({
            'transferred_tokens': [t['token_id'] for t in transfer_result['successful']],
            'transfer_details': transfer_result['successful'],
            'transfer_errors': transfer_result['errors'],
            'tokens_successfully_transferred': transfer_result['total_transferred'],
            'payment_processed_at': payment_result.get('payment_processed_at').isoformat() if payment_result.get('payment_processed_at') else None,
            
            # Información FICTICIA de pago bancario
            'payment_data': {
                'method': payment_result.get('payment_method'),
                'reference': payment_result.get('payment_reference'),
                'metadata': payment_result.get('payment_metadata', {})
            },
            
            # Flujo temporal completo
            'payment_flow': {
                'step_1_matches_selected': purchase_order.matched_at.isoformat() if purchase_order.matched_at else None,
                'step_2_processing_payment': payment_result.get('processing_started_at').isoformat() if payment_result.get('processing_started_at') else None,
                'step_3_payment_completed': payment_result.get('payment_processed_at').isoformat() if payment_result.get('payment_processed_at') else None,
                'step_4_tokens_transferred': timezone.now().isoformat(),
                'step_5_finalized': timezone.now().isoformat()
            },
            
            # Estadísticas finales
            'final_statistics': {
                'total_matches_processed': transfer_result.get('matches_processed', 0),
                'successful_transfers': transfer_result['total_transferred'],
                'failed_transfers': transfer_result['total_errors'],
                'success_rate': (transfer_result['total_transferred'] / (transfer_result['total_transferred'] + transfer_result['total_errors'])) * 100 if (transfer_result['total_transferred'] + transfer_result['total_errors']) > 0 else 0
            }
        })
        
        purchase_order.metadata = metadata
        purchase_order.save(update_fields=['metadata'])
        
        logger.info(f"Updated metadata for purchase order {purchase_order.order_number}")
    
    def update_final_order_status(self, purchase_order: PurchaseOrder) -> None:
        """Actualiza el estado final de la orden de compra"""
        
        if not purchase_order.metadata:
            logger.warning(f"Cannot update final status for order {purchase_order.id}: no metadata")
            return
        
        selected_matches = purchase_order.metadata.get('selected_matches', [])
        total_units_purchased = sum(match.get('units', 0) for match in selected_matches)
        
        if total_units_purchased >= purchase_order.units:
            purchase_order.status = 'FULLY_EXECUTED'
            purchase_order.fully_executed_at = timezone.now()
            status_field = 'fully_executed_at'
            logger.info(f"Purchase order {purchase_order.order_number} fully executed")
        else:
            purchase_order.status = 'PARTIALLY_EXECUTED'
            purchase_order.partially_executed_at = timezone.now()
            status_field = 'partially_executed_at'
            logger.info(f"Purchase order {purchase_order.order_number} partially executed: {total_units_purchased}/{purchase_order.units} units")
        
        purchase_order.save(update_fields=['status', status_field])
    
    def log_payment_success(
        self, 
        purchase_order: PurchaseOrder, 
        payment_result: dict, 
        transfer_result: dict, 
        user,
        request=None
    ) -> None:
        """Registra auditoría completa de éxito"""
        
        if not request:
            logger.info("No request provided for audit logging")
            return
        
        audit_details = {
            'order_id': str(purchase_order.id),
            'order_number': purchase_order.order_number,
            'final_status': purchase_order.status,
            
            # Información de pago
            'payment_method': payment_result.get('payment_method'),
            'payment_reference': payment_result.get('payment_reference'),
            'payment_amount': purchase_order.metadata.get('selection_summary', {}).get('total_amount') if purchase_order.metadata else None,
            'payment_processed_at': payment_result.get('payment_processed_at').isoformat() if payment_result.get('payment_processed_at') else None,
            
            # Información REAL de transferencias
            'tokens_transferred': transfer_result['total_transferred'],
            'real_token_ids': [t['token_id'] for t in transfer_result['successful']],
            'transfer_errors_count': transfer_result['total_errors'],
            'transfer_details': transfer_result['successful'],
            'matches_processed': transfer_result.get('matches_processed', 0),
            
            # Metadatos de operación
            'operation': 'complete_purchase_order_with_real_transfers',
            'blockchain_transfers': True,
            'executed_by': user.email,
            'flow': 'MATCHES_SELECTED → PROCESSING_PAYMENT → PAID → TOKENS_TRANSFERRED → COMPLETED'
        }
        
        try:
            AuditService.log_action(
                request=request,
                action_code='PURCHASE_ORDER_COMPLETE',
                obj=purchase_order,
                details=audit_details,
                status='SUCCESS'
            )
            
            logger.info(f"Audit logged successfully for purchase order {purchase_order.order_number}")
            
        except Exception as e:
            logger.error(f"Failed to log audit for purchase order {purchase_order.id}: {str(e)}")
            # No fallar por esto, el proceso principal ya terminó exitosamente
    
    def build_success_response(
        self, 
        purchase_order: PurchaseOrder, 
        payment_result: dict, 
        transfer_result: dict,
        transactions_created: List[dict] = None
    ) -> dict:
        """Construye la respuesta final de éxito"""
        
        # Extraer información de selección si está disponible
        selection_info = {}
        if purchase_order.metadata and purchase_order.metadata.get('selection_summary'):
            selection_summary = purchase_order.metadata['selection_summary']
            selection_info = {
                'total_amount': float(str(selection_summary.get('total_amount', 0))),
                'total_units': selection_summary.get('total_units', 0),
                'matches_count': len(purchase_order.metadata.get('selected_matches', [])),
                'savings': selection_summary.get('savings', 0)
            }
        
        response = {
            'success': True,
            'message': f'Pago ejecutado exitosamente para orden {purchase_order.order_number}',
            
            # Detalles de la orden
            'order_details': {
                'order_id': str(purchase_order.id),
                'order_number': purchase_order.order_number,
                'final_status': purchase_order.status,
                'completed_at': timezone.now().isoformat()
            },
            
            # Resumen de pago (ficticio)
            'payment_summary': {
                'method': payment_result.get('payment_method'),
                'reference': payment_result.get('payment_reference'),
                'amount_paid': selection_info.get('total_amount', 0),
                'currency': 'COP',
                'processed_at': payment_result.get('payment_processed_at').isoformat() if payment_result.get('payment_processed_at') else None
            },
            
            # Resumen de transferencias (real)
            'transfer_summary': {
                'tokens_transferred': transfer_result['total_transferred'],
                'transfer_details': transfer_result['successful'],
                'transfer_errors': transfer_result['errors'],
                'blockchain_confirmed': True,
                'matches_processed': transfer_result.get('matches_processed', 0)
            },
            
            # Transacciones creadas (si aplica)
            'transactions_summary': {
                'transactions_created': len(transactions_created) if transactions_created else 0,
                'transactions_details': transactions_created or [],
                'formal_records': True
            },
            
            # Flujo de ejecución
            'execution_flow': {
                'step_1': 'Validación de selección',
                'step_2': 'Procesamiento de pago bancario (ficticio)',
                'step_3': 'Transferencia real de tokens',
                'step_4': 'Actualización de estados',
                'step_5': 'Finalización y auditoría',
                'status': 'COMPLETED'
            }
        }
        
        # Agregar detalles de selección si están disponibles
        if selection_info:
            response['selection_details'] = {
                'original_amount': selection_info['total_amount'],
                'matches_count': selection_info['matches_count'],
                'savings': selection_info['savings']
            }
        
        return response
    
    def handle_payment_error(
        self, 
        purchase_order: PurchaseOrder, 
        error_msg: str, 
        user,
        request=None
    ) -> None:
        """Maneja errores durante el procesamiento de pago"""
        
        # Revertir estado si es necesario
        if purchase_order.status in ['PROCESSING_PAYMENT', 'PAID']:
            purchase_order.status = 'MATCHES_SELECTED'
            purchase_order.processing_payment_at = None
            purchase_order.paid_at = None
            purchase_order.save(update_fields=['status', 'processing_payment_at', 'paid_at'])
            logger.info(f"Reverted purchase order {purchase_order.order_number} to MATCHES_SELECTED due to error")
        
        # Registrar auditoría de error
        if request:
            try:
                AuditService.log_action(
                    request=request,
                    action_code='PURCHASE_ORDER_PAYMENT_ERROR',
                    obj=purchase_order,
                    details={
                        'order_id': str(purchase_order.id),
                        'order_number': purchase_order.order_number,
                        'error': error_msg,
                        'error_type': 'PaymentExecutionError',
                        'executed_by': user.email,
                        'operation': 'complete_purchase_order'
                    },
                    status='ERROR'
                )
            except Exception as e:
                logger.error(f"Failed to log error audit: {str(e)}")
        
        logger.error(f"Payment error for purchase order {purchase_order.id}: {error_msg}")
