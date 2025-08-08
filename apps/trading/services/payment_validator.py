from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from apps.trading.models.core_models import PurchaseOrder

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
        
        if purchase_order.status != 'MATCHES_SELECTED':
            raise PaymentValidationError(
                f'La orden debe estar en estado MATCHES_SELECTED. Estado actual: {purchase_order.status}'
            )
    
    def validate_selected_matches(self, purchase_order: PurchaseOrder) -> None:
        """Valida que la orden tenga matches seleccionados"""
        
        if not purchase_order.metadata or not purchase_order.metadata.get('selected_matches'):
            raise PaymentValidationError(
                'No se encontraron matches seleccionados en la orden'
            )
    
    #def validate_payment_preconditions(self, purchase_order: PurchaseOrder, payment_data: dict) -> None:
        """Valida condiciones previas para el procesamiento de pago"""
        
        # Validar estado de la orden
        """ if purchase_order.status != 'MATCHES_SELECTED':
            raise ValueError(f"Cannot process payment for order with status: {purchase_order.status}")
        
        # Validar monto del pago
        expected_amount, units_to_purchase = self.extract_payment_amount(purchase_order)
        paid_amount = Decimal(str(payment_data.get('amount', 0)))
        
        if abs(paid_amount - expected_amount) > Decimal('0.01'):
            raise ValueError(f"Payment amount mismatch. Expected: {expected_amount}, Received: {paid_amount}")
    
    def extract_payment_amount(self, purchase_order: PurchaseOrder) -> tuple[Decimal, int]: """
        """Extrae el monto esperado del pago desde metadatos o orden"""
        
"""         if hasattr(purchase_order, 'metadata') and purchase_order.metadata:
            selection_summary = purchase_order.metadata.get('selection_summary', {})
            if 'total_amount' in selection_summary:
                expected_amount = Decimal(str(selection_summary['total_amount']))
                selected_matches = purchase_order.metadata.get('selected_matches', [])
                units_to_purchase = sum(match.get('units', 0) for match in selected_matches)
                return expected_amount, units_to_purchase
        
        # Fallback a valores de la orden
        return purchase_order.total_amount, purchase_order.units """
    
