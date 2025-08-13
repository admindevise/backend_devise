from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from apps.trading.models.core_models import PurchaseOrder
from apps.trading.models.selection_models import MatchSelection

class PaymentValidationError(Exception):
    """Excepción para errores de validación de pagos"""
    pass

class PaymentValidator:
    """
    🔍 Validador de Pagos - Maneja todas las validaciones relacionadas con pagos
    
    Responsabilidades:
    - Validar estados de órdenes
    - Verificar expiración de selecciones
    - Validar montos de pago
    - Validar metadatos de selección
    """
    
    def validate_payment_execution(self, purchase_order: PurchaseOrder) -> None:
        """Valida que la orden esté lista para ejecución de pago"""
        
        # 3. Verificar estado DESPUÉS de validar expiración
        self.validate_order_status(purchase_order)
        
        # 4. Verificar que tenga selecciones
        self.validate_selected_matches(purchase_order)
        
        # 5. Verificar contratos aprobados
        self.validate_contracts_approved(purchase_order)
        
    def validate_contracts_approved(self, purchase_order: PurchaseOrder) -> None:
        """Valida que todos los contratos estén aprobados antes del pago"""
        
        from apps.trading.models.core_models import OrderContract
        
        # Obtener matches seleccionados
        selected_matches = purchase_order.metadata.get('selected_matches', [])
        
        if not selected_matches:
            raise PaymentValidationError('No hay matches seleccionados')
        
        # Verificar que cada match tenga un contrato aprobado
        unapproved_contracts = []
        
        for match in selected_matches:
            sales_order_id = match.get('sales_order_id')
            
            if not sales_order_id:
                continue
                
            contract = OrderContract.objects.filter(
                purchase_order=purchase_order,
                sales_order_id=sales_order_id,
                status='APPROVED'
            ).first()
            
            if not contract:
                unapproved_contracts.append({
                    'sales_order_id': sales_order_id,
                    'sales_order_number': match.get('sales_order_number', sales_order_id)
                })
        
        if unapproved_contracts:
            contract_list = ", ".join([c['sales_order_number'] for c in unapproved_contracts])
            raise PaymentValidationError(
                f'Los siguientes contratos deben ser aprobados por el administrador antes del pago: {contract_list}'
            )    
    
    def validate_order_status(self, purchase_order: PurchaseOrder) -> None:
        """Valida que el estado de la orden sea correcto"""
        
        if not purchase_order.status in ['MATCHES_SELECTED', 'PARTIALLY_EXECUTED']:
            raise PaymentValidationError(
                f'La orden debe estar en estado MATCHES_SELECTED. Estado actual: {purchase_order.status}'
            )
    
    def validate_selected_matches(self, purchase_order: PurchaseOrder) -> None:
        """Valida que la orden tenga matches seleccionados"""
        
        if not purchase_order.metadata or not purchase_order.metadata.get('selected_matches'):
            raise PaymentValidationError(
                'No se encontraron matches seleccionados en la orden'
            )


    def validate_payment_preconditions_from_selection(
        self,
        purchase_order: PurchaseOrder,
        selection: MatchSelection,
        payment_data: Dict[str, Any]
    ) -> None:
        """
        Validación usando MatchSelection como fuente de verdad.
        Reemplaza validaciones basadas en metadata.
        """
        # 1. Validar que la selección tenga items
        items_count = selection.items.count()
        if items_count == 0:
            raise PaymentValidationError("La selección no tiene items válidos para pago")
        
        # 2. Validar monto
        expected_amount = float(selection.total_amount)
        provided_amount = payment_data.get('amount', 0)
        
        if abs(expected_amount - provided_amount) > 0.01:  # Tolerancia por decimales
            raise PaymentValidationError(
                f"El monto del pago ({provided_amount}) no coincide con el total de la selección ({expected_amount})"
            )
        
        # 3. Validar que la selección no esté expirada
        if selection.is_expired:
            raise PaymentValidationError("La selección de matches ha expirado")
        
        # 4. Validar estado de la selección
        if selection.status != 'ACTIVE':
            raise PaymentValidationError(f"La selección debe estar ACTIVE. Estado actual: {selection.status}")
        
        # 5. Validar que todas las órdenes relacionadas estén en estado válido
        invalid_orders = []
        for item in selection.items.select_related('purchase_order', 'sales_order'):
            if item.purchase_order.status not in ['PENDING', 'MATCHES_SELECTED', 'PARTIALLY_EXECUTED']:
                invalid_orders.append(f"PO {item.purchase_order.order_number}: {item.purchase_order.status}")
            
            if item.sales_order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
                invalid_orders.append(f"SO {item.sales_order.order_number}: {item.sales_order.status}")
        
        if invalid_orders:
            raise PaymentValidationError(f"Órdenes en estado inválido: {', '.join(invalid_orders)}")