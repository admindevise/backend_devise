from django.utils import timezone
from typing import List, Dict

from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from apps.trading.models.selection_models import (
    MatchSelection,
    MatchSelectionItem,
    PaymentRecord,
)
from apps.audit.audit_service import AuditService
from apps.fund.models.receipts import TransferReceipt


class PaymentFinalizerService:
    """
    Servicio de Finalización de Pagos - usa modelos selection_models como fuente de verdad
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
        selection = self._get_selection(purchase_order)

        # 1) Actualizar estados (derivados de DB/transfer_result, no de metadata)
        self.update_all_order_statuses_after_payment(
            purchase_order=purchase_order,
            transfer_result=transfer_result
        )

        # 2) Crear transacciones formales y recibos
        transactions_created = self.create_transactions(
            purchase_order=purchase_order,
            transfer_result=transfer_result,
            user=user,
            request=request
        )

        # 3) Actualizar metadata solo como cache/resumen (no verdad)
        self.update_order_metadata(
            purchase_order=purchase_order,
            payment_result=payment_result,
            transfer_result=transfer_result
        )

        # 4) Auditoría
        self.log_payment_success(purchase_order, payment_result, transfer_result, user, request)

        # 5) Respuesta
        return self.build_success_response(
            purchase_order=purchase_order,
            payment_result=payment_result,
            transfer_result=transfer_result,
            transactions_created=transactions_created
        )

    # =============================
    # Estados de órdenes
    # =============================

    def update_all_order_statuses_after_payment(
        self,
        purchase_order: PurchaseOrder,
        transfer_result: dict
    ) -> None:
        """Actualiza estados de purchase y sales orders basado en transferencias reales"""
        units_transferred = int(transfer_result.get('total_transferred') or len(transfer_result.get('successful', [])) or 0)

        # Purchase Order (acumulativo)
        self._update_purchase_order_status_after_transfer(
            purchase_order=purchase_order,
            units_transferred=units_transferred
        )

        # Sales Orders afectadas
        self._update_affected_sales_orders_status(
            purchase_order=purchase_order,
            transfer_result=transfer_result
        )

        # MatchSelection: marcar COMPLETED si corresponde
        selection = self._get_selection(purchase_order)
        if selection:
            # Si el total transferido acumulado de la PO alcanza las unidades seleccionadas
            try:
                po_total_executed = purchase_order.units_executed or 0
                if po_total_executed >= selection.total_units:
                    selection.status = MatchSelection.MatchSelectionStatus.COMPLETED
                    selection.save(update_fields=['status'])
            except Exception:
                pass

    def _update_purchase_order_status_after_transfer(
        self,
        purchase_order: PurchaseOrder,
        units_transferred: int
    ) -> None:
        """Acumula ejecución sobre la purchase order y actualiza estado"""
        if units_transferred <= 0:
            return

        original_units = purchase_order.units
        purchase_order.units_executed = (purchase_order.units_executed or 0) + units_transferred

        # available_units
        if purchase_order.available_units is None:
            purchase_order.available_units = max(original_units - purchase_order.units_executed, 0)
        else:
            purchase_order.available_units = max((purchase_order.available_units or original_units) - units_transferred, 0)

        # Estado
        if purchase_order.units_executed >= original_units:
            purchase_order.status = 'FULLY_EXECUTED'
            if hasattr(purchase_order, 'fully_executed_at'):
                purchase_order.fully_executed_at = timezone.now()
            update_fields = ['status', 'units_executed', 'available_units']
            if hasattr(purchase_order, 'fully_executed_at'):
                update_fields.append('fully_executed_at')
        else:
            purchase_order.status = 'PARTIALLY_EXECUTED'
            if hasattr(purchase_order, 'partially_executed_at') and not purchase_order.partially_executed_at:
                purchase_order.partially_executed_at = timezone.now()
            update_fields = ['status', 'units_executed', 'available_units']
            if hasattr(purchase_order, 'partially_executed_at'):
                update_fields.append('partially_executed_at')

        purchase_order.save(update_fields=update_fields)

    def _update_affected_sales_orders_status(
        self,
        purchase_order: PurchaseOrder,
        transfer_result: dict
    ) -> None:
        """Actualiza estado de cada sales order con base en tokens transferidos por SO"""
        # Agrupar por sales_order_id
        per_sales_units: Dict[str, int] = {}
        for t in transfer_result.get('successful', []):
            so_id = t.get('sales_order_id')
            if not so_id:
                continue
            per_sales_units[so_id] = per_sales_units.get(so_id, 0) + 1

        for so_id, moved in per_sales_units.items():
            try:
                sales_order = SalesOrder.objects.get(id=so_id)
            except SalesOrder.DoesNotExist:
                continue

            if moved <= 0:
                continue

            original_available = sales_order.available_units if sales_order.available_units is not None else sales_order.units
            sales_order.available_units = max((original_available or sales_order.units) - moved, 0)

            if sales_order.available_units <= 0:
                sales_order.status = 'FULLY_EXECUTED'
                if hasattr(sales_order, 'fully_executed_at'):
                    sales_order.fully_executed_at = timezone.now()
                update_fields = ['available_units', 'status']
                if hasattr(sales_order, 'fully_executed_at'):
                    update_fields.append('fully_executed_at')
            else:
                sales_order.status = 'PARTIALLY_EXECUTED'
                if hasattr(sales_order, 'partially_executed_at') and not sales_order.partially_executed_at:
                    sales_order.partially_executed_at = timezone.now()
                update_fields = ['available_units', 'status']
                if hasattr(sales_order, 'partially_executed_at'):
                    update_fields.append('partially_executed_at')

            sales_order.save(update_fields=update_fields)

    # =============================
    # Transacciones formales
    # =============================

    def create_transactions(
        self,
        purchase_order: PurchaseOrder,
        transfer_result: dict,
        user,
        request=None
    ) -> List[dict]:
        """
        Crea Transaction por cada SalesOrder con transferencias exitosas.
        Precios/unidades se derivan de MatchSelectionItem y del conteo de tokens transferidos.
        """
        from apps.trading.models.core_models import Transaction

        selection = self._get_selection(purchase_order)
        if not selection:
            return []

        # Agrupar tokens por sales_order_id
        per_sales_tokens: Dict[str, List[dict]] = {}
        for t in transfer_result.get('successful', []):
            so_id = t.get('sales_order_id')
            if not so_id:
                continue
            per_sales_tokens.setdefault(so_id, []).append(t)

        results: List[dict] = []

        for so_id, tokens in per_sales_tokens.items():
            try:
                sales_order = SalesOrder.objects.get(id=so_id)
            except SalesOrder.DoesNotExist:
                continue

            units_transferred = len(tokens)
            if units_transferred <= 0:
                continue

            # Obtener el item de la selección para esa SO (precio unitario)
            try:
                item: MatchSelectionItem = selection.items.get(sales_order=sales_order)
                unit_price = item.price_per_unit
            except MatchSelectionItem.DoesNotExist:
                # fallback al precio de la SO
                unit_price = sales_order.price_per_unit

            # Obtener un tx_id de blockchain si existe en alguno
            blockchain_transaction_id = None
            for token_transfer in tokens:
                tr = token_transfer.get('transfer_result', {})
                if isinstance(tr, dict) and tr.get('id'):
                    blockchain_transaction_id = tr.get('id')
                    break

            transaction = Transaction.objects.create(
                purchase_order=purchase_order,
                sales_order=sales_order,
                buyer=purchase_order.supplier_user,
                seller=sales_order.seller_user,
                fund=purchase_order.fund,
                units=units_transferred,
                price_per_unit=unit_price,
                total_amount=units_transferred * unit_price,
                metadata={
                    'transferred_tokens': [t['token_id'] for t in tokens],
                    'units_transferred': units_transferred,
                    'blockchain_confirmed': True,
                    'blockchain_transaction_id': blockchain_transaction_id,
                    'created_via': 'payment_core_finalizer',
                    'execution_flow': 'select_matches -> pay_selection -> token_transfer'
                }
            )
            
            transfer_receipt = TransferReceipt.objects.create(
                user=purchase_order.supplier_user,
                transaction_id=blockchain_transaction_id or str(transaction.id),
                fund=purchase_order.fund,
                description=f"Transferencia exitosa (Mercado Secundario). Tokens: {units_transferred}. Desde {sales_order.order_number}"
            )

            results.append({
                'transaction_id': str(transaction.id),
                'sales_order_id': str(sales_order.id),
                'sales_order_number': sales_order.order_number,
                'buyer': purchase_order.supplier_user.email,
                'seller': sales_order.seller_user.email,
                'units_transferred': units_transferred,
                'price_per_unit': float(unit_price),
                'total_amount': float(transaction.total_amount),
                'tokens_transferred': [t['token_id'] for t in tokens],
                'transfer_receipt_id': str(transfer_receipt.id) if transfer_receipt else None,
                'blockchain_transaction_id': blockchain_transaction_id,
                'receipt_created': transfer_receipt is not None
            })

        return results

    # =============================
    # Metadata (cache/resumen)
    # =============================

    def update_order_metadata(
        self,
        purchase_order: PurchaseOrder,
        payment_result: dict,
        transfer_result: dict
    ) -> None:
        """Actualiza metadata como resumen; la verdad viene de los modelos"""
        selection = self._get_selection(purchase_order)
        latest_payment = self._get_latest_payment_record(purchase_order)

        summary = {
            'selection': {
                'selection_id': str(selection.id) if selection else None,
                'total_units': selection.total_units if selection else None,
                'total_amount': float(selection.total_amount) if selection else None,
                'items_count': selection.items.count() if selection else 0,
                'status': selection.status if selection else None,
            },
            'payment': {
                'payment_record_id': latest_payment.id if latest_payment else None,
                'status': latest_payment.status if latest_payment else None,
                'reference': latest_payment.reference if latest_payment else None,
                'amount': float(latest_payment.amount) if latest_payment else None,
                'processed_at': latest_payment.processed_at.isoformat() if latest_payment and latest_payment.processed_at else None,
            },
            'transfers': {
                'successful_count': int(transfer_result.get('total_transferred') or len(transfer_result.get('successful', [])) or 0),
                'errors_count': int(transfer_result.get('total_errors') or 0),
                'last_update': timezone.now().isoformat()
            }
        }

        purchase_order.metadata = purchase_order.metadata or {}
        purchase_order.metadata['execution_summary'] = summary
        purchase_order.save(update_fields=['metadata'])

    # =============================
    # Auditoría y respuesta
    # =============================

    def log_payment_success(
        self,
        purchase_order: PurchaseOrder,
        payment_result: dict,
        transfer_result: dict,
        user,
        request=None
    ) -> None:
        """Auditoría usando modelos como base"""
        if not request:
            return

        latest_payment = self._get_latest_payment_record(purchase_order)

        audit_details = {
            'order_id': str(purchase_order.id),
            'order_number': purchase_order.order_number,
            'final_status': purchase_order.status,
            'payment_method': payment_result.get('payment_method'),
            'payment_reference': payment_result.get('payment_reference'),
            'payment_record_id': latest_payment.id if latest_payment else None,
            'payment_amount': float(latest_payment.amount) if latest_payment else None,
            'payment_processed_at': latest_payment.processed_at.isoformat() if latest_payment and latest_payment.processed_at else None,
            'tokens_transferred': int(transfer_result.get('total_transferred') or len(transfer_result.get('successful', [])) or 0),
            'real_token_ids': [t['token_id'] for t in transfer_result.get('successful', [])],
            'transfer_errors_count': int(transfer_result.get('total_errors') or 0),
            'transfer_details': transfer_result.get('successful', []),
            'matches_processed': transfer_result.get('matches_processed', 0),
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
        except Exception:
            pass

    def build_success_response(
        self,
        purchase_order: PurchaseOrder,
        payment_result: dict,
        transfer_result: dict,
        transactions_created: List[dict] = None
    ) -> dict:
        """Respuesta final basada en modelos (selection/payment/transfer)"""
        selection = self._get_selection(purchase_order)
        latest_payment = self._get_latest_payment_record(purchase_order)

        selection_info = {
            'selection_id': str(selection.id) if selection else None,
            'total_amount': float(selection.total_amount) if selection else 0.0,
            'total_units': selection.total_units if selection else 0,
            'items_count': selection.items.count() if selection else 0,
            'status': selection.status if selection else None,
        }

        return {
            'success': True,
            'message': f'Pago ejecutado exitosamente para orden {purchase_order.order_number}',
            'order_details': {
                'order_id': str(purchase_order.id),
                'order_number': purchase_order.order_number,
                'final_status': purchase_order.status,
                'completed_at': timezone.now().isoformat()
            },
            'payment_summary': {
                'method': payment_result.get('payment_method'),
                'reference': payment_result.get('payment_reference'),
                'amount_paid': float(latest_payment.amount) if latest_payment else selection_info['total_amount'],
                'currency': getattr(latest_payment, 'currency', 'COP') if latest_payment else 'COP',
                'processed_at': latest_payment.processed_at.isoformat() if latest_payment and latest_payment.processed_at else None
            },
            'transfer_summary': {
                'tokens_transferred': int(transfer_result.get('total_transferred') or len(transfer_result.get('successful', [])) or 0),
                'transfer_details': transfer_result.get('successful', []),
                'transfer_errors': transfer_result.get('errors', []),
                'blockchain_confirmed': True,
                'matches_processed': transfer_result.get('matches_processed', 0)
            },
            'transactions_summary': {
                'transactions_created': len(transactions_created) if transactions_created else 0,
                'transactions_details': transactions_created or [],
                'formal_records': True
            },
            'selection_details': selection_info,
            'execution_flow': {
                'step_1': 'Validación de selección',
                'step_2': 'Procesamiento de pago bancario (ficticio)',
                'step_3': 'Transferencia real de tokens',
                'step_4': 'Actualización de estados',
                'step_5': 'Finalización y auditoría',
                'status': 'COMPLETED'
            }
        }

    def handle_payment_error(
        self,
        purchase_order: PurchaseOrder,
        error_msg: str,
        user,
        request=None
    ) -> None:
        """Manejo de error manteniendo consistencia básica en PurchaseOrder"""
        if purchase_order.status in ['PROCESSING_PAYMENT', 'PAID']:
            purchase_order.status = 'MATCHES_SELECTED'
            if hasattr(purchase_order, 'processing_payment_at'):
                purchase_order.processing_payment_at = None
            if hasattr(purchase_order, 'paid_at'):
                purchase_order.paid_at = None
            try:
                purchase_order.save(update_fields=['status', 'processing_payment_at', 'paid_at'])
            except Exception:
                purchase_order.save()

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
            except Exception:
                pass

    # =============================
    # Helpers
    # =============================

    def _get_selection(self, purchase_order: PurchaseOrder) -> MatchSelection:
        try:
            return purchase_order.match_selection
        except MatchSelection.DoesNotExist:
            return None

    def _get_latest_payment_record(self, purchase_order: PurchaseOrder) -> PaymentRecord:
        try:
            return purchase_order.payment_records.order_by('-initiated_at').first()
        except Exception:
            return None