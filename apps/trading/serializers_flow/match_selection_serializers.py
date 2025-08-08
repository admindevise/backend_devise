from rest_framework import serializers
from typing import Dict, Any, List
from decimal import Decimal
from django.utils import timezone

from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from apps.trading.services_core.selection_service import MatchSelectionService


class CoreMatchSelectionSerializer(serializers.Serializer):
    """Serializer para selección manual de matches (services_core)"""

    purchase_order_id = serializers.UUIDField(required=True)
    selected_matches = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        min_length=1,
        help_text="Formato: [{'sales_order_id': 'uuid', 'units': 5}]"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_service = MatchSelectionService()
        self._purchase_order = None

    def validate_purchase_order_id(self, value):
        request = self.context.get('request')
        user = request.user if request else None

        if not user:
            raise serializers.ValidationError("Usuario no identificado")

        try:
            purchase_order = PurchaseOrder.objects.select_related('fund', 'supplier_user').get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")

        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para esta orden")

        if purchase_order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
            raise serializers.ValidationError(
                f"La orden debe estar PENDING o PARTIALLY_EXECUTED. Estado actual: {purchase_order.status}"
            )

        self._purchase_order = purchase_order
        return value

    def validate_selected_matches(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("selected_matches debe ser una lista")

        for i, match in enumerate(value):
            if not isinstance(match, dict):
                raise serializers.ValidationError(f"Match {i} debe ser un objeto")
            if not match.get('sales_order_id'):
                raise serializers.ValidationError(f"Match {i} debe tener 'sales_order_id'")
            units = match.get('units')
            if units is None or not isinstance(units, int) or units <= 0:
                raise serializers.ValidationError(f"Match {i}: 'units' debe ser un entero positivo")

        return value

    def _build_validated_matches(self, purchase_order: PurchaseOrder, raw_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida SOs y construye estructura para services_core"""
        validated: List[Dict[str, Any]] = []
        total_units_req = 0

        for m in raw_matches:
            so_id = m['sales_order_id']
            units_req = int(m['units'])

            try:
                sales_order = SalesOrder.objects.select_related('fund', 'seller_user').get(id=so_id)
            except SalesOrder.DoesNotExist:
                raise serializers.ValidationError(f"SalesOrder {so_id} no encontrada")

            if sales_order.fund_id != purchase_order.fund_id:
                raise serializers.ValidationError(f"SalesOrder {sales_order.order_number} pertenece a otro fondo")

            available_units = sales_order.available_units
            if available_units is None:
                # fallback si no existe campo: units - units_executed
                executed = getattr(sales_order, 'units_executed', 0) or 0
                available_units = max((sales_order.units or 0) - executed, 0)

            if units_req > available_units:
                raise serializers.ValidationError(
                    f"La orden de venta {sales_order.order_number} solo tiene {available_units} unidades disponibles"
                )

            price = Decimal(str(sales_order.price_per_unit))
            subtotal = price * units_req

            validated.append({
                'sales_order_id': str(sales_order.id),
                'purchase_order_id': str(purchase_order.id),
                'units': units_req,
                'price_per_unit': str(price),
                'total_amount': str(subtotal),
                'buyer_savings': '0',
                'seller_gain': '0',
                'quality_score': None
            })
            total_units_req += units_req

        # Opcional: validar contra unidades de la PO (si aplica)
        po_units_target = getattr(purchase_order, 'units', None)
        if isinstance(po_units_target, int) and po_units_target > 0:
            # Permitimos parcial; si necesitas exacto, cambia a !=
            if total_units_req > po_units_target:
                raise serializers.ValidationError(
                    f"Unidades seleccionadas ({total_units_req}) superan las unidades de la orden ({po_units_target})"
                )

        return validated

    def process_selection(self) -> Dict[str, Any]:
        """Procesa la selección manual con services_core"""
        request = self.context.get('request')
        user = request.user if request else None

        purchase_order = self._purchase_order
        selected_matches = self.validated_data['selected_matches']

        # Construir matches validados para el core
        validated_matches = self._build_validated_matches(purchase_order, selected_matches)

        # Tomar una SO primaria (requerido por el modelo actual)
        primary_so = SalesOrder.objects.get(id=validated_matches[0]['sales_order_id'])

        # Persistir selección
        selection = self.selection_service.create_selection(
            purchase_order=purchase_order,
            sales_order=primary_so,
            validated_matches=validated_matches,
            user=user,
            expires_in_minutes=15
        )

        return {
            'success': True,
            'message': 'Selección manual creada correctamente',
            'selection_id': str(selection.id),
            'purchase_order_id': str(purchase_order.id),
            'order_number': purchase_order.order_number,
            'selection_summary': {
                'total_units': selection.total_units,
                'total_amount': float(selection.total_amount),
                'expected_savings': float(selection.expected_savings),
                'expires_at': selection.expires_at.isoformat(),
                'items_count': selection.items.count(),
                'status': selection.status
            },
            'next_step': {
                'action': 'Proceder al pago',
                'endpoint': '/trading/pay-selection/',
                'purchase_order_id': str(purchase_order.id),
                'amount_to_pay': float(selection.total_amount),
                'payment_deadline': selection.expires_at.isoformat()
            }
        }