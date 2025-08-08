from django.db import transaction
from typing import Dict, Any

from apps.trading.models.core_models import PurchaseOrder
from apps.trading.services.payment_validator import PaymentValidator, PaymentValidationError
from apps.trading.services.payment_processor import PaymentProcessingService
from apps.trading.services.payment_finalizer import PaymentFinalizerService
from apps.trading.services_core.selection_service import MatchSelectionService
from apps.trading.services_core.transfer_service import TokenTransferService as CoreTokenTransferService


class PaymentCoreError(Exception):
    """Errores de orquestación de pago en services_core"""
    pass


class PaymentCoreService:
    """
    Core Payment Service (services_core)
    - Orquesta: selección activa → pago → transferencias → finalización
    - Delegación a servicios especializados
    - Sin dependencias de metadata legacy para selección
    """

    def __init__(self):
        self.validator = PaymentValidator()
        self.processor = PaymentProcessingService()
        self.finalizer = PaymentFinalizerService()
        self.selection_service = MatchSelectionService()
        self.transfer = CoreTokenTransferService()

    @transaction.atomic
    def execute_with_selection(
        self,
        purchase_order: PurchaseOrder,
        payment_data: Dict[str, Any],
        user,
        request=None
    ) -> Dict[str, Any]:
        """
        Ejecuta el flujo de pago completo usando la selección activa del PurchaseOrder.
        - Falla si no hay selección activa o si está expirada.
        """
        # 1. Selección activa (limpia expiradas automáticamente)
        selection = self.selection_service.get_active_selection(purchase_order)
        if not selection:
            raise PaymentCoreError("No hay una selección de matches activa para esta orden")

        # 2. Validaciones mínimas
        try:
            self.validator.validate_payment_execution(purchase_order)
            self.validator.validate_payment_preconditions(
                purchase_order,
                self._ensure_minimum_payment_data(selection, payment_data)
            )
        except PaymentValidationError as e:
            raise PaymentCoreError(str(e))

        try:
            # 3. Pago bancario (ficticio)
            prepared_payment_data = self._ensure_minimum_payment_data(selection, payment_data)
            payment_result = self.processor.process_payment(purchase_order, prepared_payment_data)

            # 4. Transferencias reales de tokens (basadas en selección activa)
            transfer_result = self.transfer.execute_selection_transfers(purchase_order)

            # 5. Finalización, estados y auditoría
            return self.finalizer.finalize_payment(
                purchase_order=purchase_order,
                payment_result=payment_result,
                transfer_result=transfer_result,
                user=user,
                request=request
            )

        except Exception as e:
            # Registrar error y propagar como CoreError
            try:
                self.finalizer.handle_payment_error(purchase_order, str(e), user, request)
            finally:
                raise PaymentCoreError(f"Error ejecutando pago y transferencias: {str(e)}")

    def _ensure_minimum_payment_data(self, selection, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Garantiza que payment_data tenga valores mínimos requeridos por el processor.
        - method, reference (si aplica), amount desde la selección.
        """
        data = dict(payment_data or {})
        data.setdefault('method', 'automatic')
        # reference es generado por el processor si no viene (opcional)
        data.setdefault('amount', float(selection.total_amount) if hasattr(selection, 'total_amount') else None)
        # útil para trazabilidad
        data.setdefault('selection_id', str(selection.id))
        data.setdefault('metadata', data.get('metadata', {}))
        return data