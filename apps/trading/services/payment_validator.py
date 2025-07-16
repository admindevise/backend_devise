from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
import logging

from apps.trading.models import PurchaseOrder

logger = logging.getLogger('trading.payment_validator')

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
        
        # 1. Verificar expiración ANTES de verificar estado
        self.validate_selection_expiry(purchase_order)
        
        # 2. Recargar después de validar expiración
        purchase_order.refresh_from_db()
        
        # 3. Verificar estado DESPUÉS de validar expiración
        self.validate_order_status(purchase_order)
        
        # 4. Verificar que tenga selecciones
        self.validate_selected_matches(purchase_order)
    
    def validate_selection_expiry(self, purchase_order: PurchaseOrder) -> None:
        """Valida que la selección no haya expirado"""
        
        if not purchase_order.metadata:
            return
            
        expires_at_str = purchase_order.metadata.get('selection_summary', {}).get('expires_at')
        
        if not expires_at_str:
            return
            
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if timezone.now() > expires_at:
                self._handle_expired_selection(purchase_order)
                raise PaymentValidationError(
                    'La selección de matches ha expirado. Debes seleccionar nuevamente.'
                )
        except ValueError:
            logger.warning(f"Invalid expiry date format: {expires_at_str}")
    
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
    
    def validate_payment_preconditions(self, purchase_order: PurchaseOrder, payment_data: dict) -> None:
        """Valida condiciones previas para el procesamiento de pago"""
        
        # Validar estado de la orden
        if purchase_order.status != 'MATCHES_SELECTED':
            raise ValueError(f"Cannot process payment for order with status: {purchase_order.status}")
        
        # Validar monto del pago
        expected_amount, units_to_purchase = self.extract_payment_amount(purchase_order)
        paid_amount = Decimal(str(payment_data.get('amount', 0)))
        
        if abs(paid_amount - expected_amount) > Decimal('0.01'):
            raise ValueError(f"Payment amount mismatch. Expected: {expected_amount}, Received: {paid_amount}")
    
    def extract_payment_amount(self, purchase_order: PurchaseOrder) -> tuple[Decimal, int]:
        """Extrae el monto esperado del pago desde metadatos o orden"""
        
        if hasattr(purchase_order, 'metadata') and purchase_order.metadata:
            selection_summary = purchase_order.metadata.get('selection_summary', {})
            if 'total_amount' in selection_summary:
                expected_amount = Decimal(str(selection_summary['total_amount']))
                selected_matches = purchase_order.metadata.get('selected_matches', [])
                units_to_purchase = sum(match.get('units', 0) for match in selected_matches)
                return expected_amount, units_to_purchase
        
        # Fallback a valores de la orden
        return purchase_order.total_amount, purchase_order.units
    
    def _handle_expired_selection(self, purchase_order: PurchaseOrder) -> None:
        """Maneja la limpieza cuando una selección expira"""
        
        # ✅ LOGGING DETALLADO PARA DEBUGGING
        logger.warning(f"🔄 HANDLING EXPIRED SELECTION for order {purchase_order.order_number}")
        logger.warning(f"  └─ Current status: {purchase_order.status}")
        logger.warning(f"  └─ Current matched_at: {purchase_order.matched_at}")
        
        # ✅ GUARDAR ESTADO ANTERIOR PARA VERIFICACIÓN
        old_status = purchase_order.status
        old_matched_at = purchase_order.matched_at
        
        # Limpiar estado y metadatos
        purchase_order.status = 'PENDING'
        purchase_order.matched_at = None
        
        # Limpiar metadatos de selección expirada
        if purchase_order.metadata:
            # ✅ GUARDAR INFORMACIÓN DE EXPIRACIÓN PARA AUDITORÍA
            expired_matches = purchase_order.metadata.get('selected_matches', [])
            expired_summary = purchase_order.metadata.get('selection_summary', {})
            
            purchase_order.metadata.pop('selected_matches', None)
            purchase_order.metadata.pop('selection_summary', None)
            purchase_order.metadata['selection_expired_at'] = timezone.now().isoformat()
            purchase_order.metadata['last_expired_selection'] = {
                'expired_at': timezone.now().isoformat(),
                'previous_status': old_status,
                'expired_matches_count': len(expired_matches),
                'expired_summary': expired_summary
            }
        
        # ✅ FORZAR SAVE COMPLETO EN LUGAR DE update_fields
        try:
            purchase_order.save()
            logger.warning(f"✅ Order {purchase_order.order_number} status updated from {old_status} to {purchase_order.status}")
        except Exception as e:
            logger.error(f"❌ ERROR saving expired selection: {str(e)}")
            raise
        
        # ✅ VERIFICAR QUE SE GUARDÓ CORRECTAMENTE
        purchase_order.refresh_from_db()
        if purchase_order.status != 'PENDING':
            logger.error(f"❌ CRITICAL: Order status not updated! Still: {purchase_order.status}")
            # Intentar guardar de nuevo
            purchase_order.status = 'PENDING'
            purchase_order.matched_at = None
            purchase_order.save(update_fields=['status', 'matched_at'])
            purchase_order.refresh_from_db()
            logger.warning(f"🔁 Retry save result: {purchase_order.status}")
        else:
            logger.warning(f"✅ Verified: Order {purchase_order.order_number} successfully reset to PENDING")