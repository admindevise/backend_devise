from django.db import transaction
from typing import Dict, Any

from apps.trading.models.core_models import PurchaseOrder
from apps.trading.models.selection_models import MatchSelection  # ← Agregado
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
    - Orquesta: selección activa → verificación de contratos → pago → transferencias → finalización
    - Delegación a servicios especializados
    - Usa selection_models como fuente de verdad (NO metadata)
    - Requiere aprobación de contratos antes de proceder
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
        - Falla si no hay selección activa o si está expirada
        - Verifica que los contratos estén aprobados antes de proceder
        - Usa modelos como fuente de verdad (NO metadata)
        """
        # 1. Obtener selección activa (limpia expiradas automáticamente)
        selection = self._get_active_selection_for_purchase_order(purchase_order)
        if not selection:
            raise PaymentCoreError("No hay una selección de matches activa para esta orden")

        # 2. Verificar que los contratos estén aprobados
        self._verify_contracts_approved(selection)

        # 3. Validaciones mínimas usando datos de modelos
        try:
            self.validator.validate_payment_execution(purchase_order)
            
            # ✅ USAR DATOS DE MODELO: preparar payment_data desde selection
            prepared_payment_data = self._prepare_payment_data_from_selection(selection, payment_data)
            
            self.validator.validate_payment_preconditions_from_selection(
                purchase_order, selection, prepared_payment_data
            )
            
        except PaymentValidationError as e:
            raise PaymentCoreError(str(e))

        try:
            # 4. Pago bancario (ficticio) - usando datos de modelo
            payment_result = self.processor.process_payment(purchase_order, prepared_payment_data)

            # 5. Transferencias reales de tokens (basadas en selección activa)
            transfer_result = self.transfer.execute_selection_transfers(purchase_order)

            # 6. Finalización, estados y auditoría
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

    def _verify_contracts_approved(self, selection: MatchSelection) -> None:
        """
        Verifica que todos los contratos relacionados con la selección estén aprobados.
        Solo procede al pago si el admin ha aprobado los documentos.
        """
        from apps.trading.models.core_models import OrderContract
        
        # Obtener todos los contratos relacionados con la selección
        selection_items = selection.items.select_related('purchase_order', 'sales_order').all()
        
        if not selection_items.exists():
            raise PaymentCoreError("No hay items en la selección para verificar contratos")
        
        pending_contracts = []
        missing_contracts = []
        
        for item in selection_items:
            # Buscar contrato entre purchase_order y sales_order
            contract = OrderContract.objects.filter(
                purchase_order=item.purchase_order,
                sales_order=item.sales_order
            ).first()
            
            if not contract:
                missing_contracts.append({
                    'purchase_order': item.purchase_order.order_number,
                    'sales_order': item.sales_order.order_number
                })
            elif contract.status != 'APPROVED':
                pending_contracts.append({
                    'contract_id': str(contract.id),
                    'status': contract.status,
                    'purchase_order': item.purchase_order.order_number,
                    'sales_order': item.sales_order.order_number
                })
        
        # Validar que todos los contratos existan y estén aprobados
        if missing_contracts:
            raise PaymentCoreError(
                f"Faltan contratos para proceder al pago. "
                f"Contratos faltantes: {len(missing_contracts)}. "
                f"Primero se deben crear los contratos para todas las órdenes."
            )
        
        if pending_contracts:
            raise PaymentCoreError(
                f"No se puede proceder al pago. Hay {len(pending_contracts)} contratos pendientes de aprobación del administrador. "
                f"Estados encontrados: {[c['status'] for c in pending_contracts]}"
            )
        
        print(f"✅ Verificación de contratos exitosa: {len(selection_items)} contratos aprobados")

    def _prepare_payment_data_from_selection(
        self, 
        selection: MatchSelection, 
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepara datos de pago usando el modelo MatchSelection como fuente de verdad.
        NO usa metadata de órdenes.
        """
        # ✅ FUENTE DE VERDAD: Usar campos del modelo MatchSelection
        prepared_data = dict(payment_data or {})
        
        # Datos obligatorios desde el modelo
        prepared_data['amount'] = float(selection.total_amount)
        prepared_data['selection_id'] = str(selection.id)
        
        # Datos opcionales con defaults
        prepared_data.setdefault('method', 'automatic')
        prepared_data.setdefault('currency', 'COP')
        prepared_data.setdefault('metadata', {})
        
        # ✅ ENRIQUECER: Agregar información de la selección para auditoría
        prepared_data['metadata'].update({
            'selection_total_units': selection.total_units,
            'selection_expected_savings': float(selection.expected_savings),
            'selection_items_count': selection.items.count(),
            'selection_status': selection.status,
            'selection_expires_at': selection.expires_at.isoformat(),
            'payment_source': 'selection_model',  # Indicar fuente de datos
        })
        
        return prepared_data

    def get_payment_validation_info(self, purchase_order: PurchaseOrder) -> Dict[str, Any]:
        """
        Obtiene información para validación de pago usando modelos como fuente de verdad.
        Reemplaza la dependencia en metadata.
        """
        # 1. Verificar selección activa
        selection = self._get_active_selection_for_purchase_order(purchase_order)
        if not selection:
            return {
                'can_pay': False,
                'reason': 'no_active_selection',
                'message': 'No hay una selección de matches activa para esta orden'
            }
            
        # 2. Verificar estado de contratos
        try:
            self._verify_contracts_approved(selection)
            contracts_status = 'approved'
            contracts_message = 'Todos los contratos están aprobados'
        except PaymentCoreError as e:
            contracts_status = 'pending'
            contracts_message = str(e)
        
        # 3. ✅ INFORMACIÓN DESDE MODELOS: No metadata
        selection_items = selection.items.select_related(
            'purchase_order', 'sales_order'
        ).all()
        
        items_detail = []
        for item in selection_items:
            items_detail.append({
                'purchase_order_number': item.purchase_order.order_number,
                'sales_order_number': item.sales_order.order_number,
                'units': item.units,
                'price_per_unit': float(item.price_per_unit),
                'total_amount': float(item.units * item.price_per_unit),
                'buyer_savings': float(item.buyer_savings),
                'seller_gain': float(item.seller_gain)
            })
        
        return {
            'can_pay': contracts_status == 'approved',
            'reason': contracts_status,
            'message': contracts_message,
            'order_details': {
                'order_id': str(purchase_order.id),
                'order_number': purchase_order.order_number,
                'order_status': purchase_order.status,
                'buyer_email': purchase_order.supplier_user.email,
            },
            'selection_summary': {
                'selection_id': str(selection.id),
                'total_amount': float(selection.total_amount),
                'total_units': selection.total_units,
                'expected_savings': float(selection.expected_savings),
                'status': selection.status,
                'expires_at': selection.expires_at.isoformat(),
                'items_count': len(items_detail),
                'time_remaining_seconds': selection.time_remaining.total_seconds()
            },
            'items_detail': items_detail,
            'contracts_status': contracts_status
        }

    # =========================
    # Métodos legacy (compatibilidad)
    # =========================

    def _ensure_minimum_payment_data(self, selection, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ⚠️ DEPRECATED: Usar _prepare_payment_data_from_selection() en su lugar.
        Método de compatibilidad con código legacy.
        """
        data = dict(payment_data or {})
        data.setdefault('method', 'automatic')
        # reference es generado por el processor si no viene (opcional)
        data.setdefault('amount', float(selection.total_amount) if hasattr(selection, 'total_amount') else None)
        # útil para trazabilidad
        data.setdefault('selection_id', str(selection.id))
        data.setdefault('metadata', data.get('metadata', {}))
        return data
    
# En apps/trading/services_core/payment_core_service.py
# Agregar este método después de get_payment_validation_info:

    def _get_active_selection_for_purchase_order(self, purchase_order: PurchaseOrder) -> MatchSelection:
        """
        Busca selecciones activas que incluyan esta purchase order en sus items.
        Para el nuevo flujo donde las selecciones se crean desde sales orders.
        """
        try:
            # Buscar selecciones que incluyan esta purchase order en sus items
            selection = MatchSelection.objects.filter(
                items__purchase_order=purchase_order,
                status='ACTIVE'
            ).select_related('sales_order').prefetch_related(
                'items__purchase_order',
                'items__sales_order'
            ).first()
            
            # Verificar que no esté expirada
            if selection and selection.is_expired:
                # Marcar como expirada automáticamente
                selection.status = 'EXPIRED'
                selection.save(update_fields=['status'])
                return None
                
            return selection
            
        except Exception as e:
            print(f"❌ Error buscando selección activa: {str(e)}")
            return None