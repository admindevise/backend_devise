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
    🔍 Validador de Pagos - Usa modelos como fuente de verdad (NO metadata legacy)
    
    Responsabilidades:
    - Validar estados de órdenes usando modelos
    - Verificar selecciones activas desde MatchSelection
    - Validar contratos aprobados desde OrderContract
    - Validar precondiciones de pago usando selection_models
    """
    
    def validate_payment_execution(self, purchase_order: PurchaseOrder) -> None:
        """
        Valida que la orden esté lista para ejecución de pago usando modelos como fuente de verdad.
        """
        # 1. Verificar estado de la orden
        self.validate_order_status(purchase_order)
        
        # 2. Verificar que tenga selecciones activas usando modelos
        self.validate_selected_matches_from_models(purchase_order)
        
        # NOTA: Los contratos se validan en PaymentCoreService antes de proceder
    
    def validate_order_status(self, purchase_order: PurchaseOrder) -> None:
        """Valida que el estado de la orden permita ejecución de pago"""
        
        valid_statuses = ['PENDING', 'MATCHES_SELECTED', 'PARTIALLY_EXECUTED']
        
        if purchase_order.status not in valid_statuses:
            raise PaymentValidationError(
                f'La orden debe estar en estado {", ".join(valid_statuses)}. '
                f'Estado actual: {purchase_order.status}'
            )
    
    def validate_selected_matches_from_models(self, purchase_order: PurchaseOrder) -> None:
        """
        ✅ NUEVO: Valida que la orden tenga selecciones usando modelos como fuente de verdad
        """
        try:
            # Buscar selección activa que incluya esta purchase order
            selection = MatchSelection.objects.filter(
                items__purchase_order=purchase_order,
                status='ACTIVE'
            ).first()
            
            if not selection:
                raise PaymentValidationError(
                    'No hay una selección de matches activa para esta orden'
                )
            
            # Verificar que tenga items válidos para esta purchase order
            po_items = selection.items.filter(purchase_order=purchase_order)
            if not po_items.exists():
                raise PaymentValidationError(
                    'La selección no tiene items válidos para esta orden'
                )
            
            # Verificar que no esté expirada
            if selection.is_expired:
                raise PaymentValidationError(
                    'La selección de matches ha expirado'
                )
                
        except MatchSelection.DoesNotExist:
            raise PaymentValidationError(
                'No se encontró selección de matches para esta orden'
            )
    
    def validate_selected_matches(self, purchase_order: PurchaseOrder) -> None:
        """
        ⚠️ LEGACY: Mantenido para compatibilidad, pero redirige al nuevo método
        """
        return self.validate_selected_matches_from_models(purchase_order)
    
    def validate_contracts_approved_from_selection(self, selection: MatchSelection) -> None:
        """
        ✅ NUEVO: Valida contratos aprobados usando la selección activa como fuente de verdad
        """
        from apps.trading.models.core_models import OrderContract
        
        # Obtener todos los items de la selección
        selection_items = selection.items.select_related('purchase_order', 'sales_order').all()
        
        if not selection_items.exists():
            raise PaymentValidationError("No hay items en la selección para verificar contratos")
        
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
                    'purchase_order': item.purchase_order.order_number,
                    'sales_order': item.sales_order.order_number,
                    'contract_status': contract.status
                })
        
        # Construir mensaje de error si hay problemas
        error_messages = []
        
        if missing_contracts:
            missing_list = [f"PO {c['purchase_order']} ↔ SO {c['sales_order']}" for c in missing_contracts]
            error_messages.append(f"Contratos faltantes: {', '.join(missing_list)}")
        
        if pending_contracts:
            pending_list = [f"PO {c['purchase_order']} ↔ SO {c['sales_order']} ({c['contract_status']})" for c in pending_contracts]
            error_messages.append(f"Contratos pendientes de aprobación: {', '.join(pending_list)}")
        
        if error_messages:
            raise PaymentValidationError(
                f"Todos los contratos deben estar aprobados por el administrador antes del pago. "
                f"{' | '.join(error_messages)}"
            )
    
    def validate_contracts_approved(self, purchase_order: PurchaseOrder) -> None:
        """
        ⚠️ LEGACY: Valida contratos usando metadata (mantenido para compatibilidad)
        """
        from apps.trading.models.core_models import OrderContract
        
        # Intentar obtener matches desde metadata legacy
        if not purchase_order.metadata or not purchase_order.metadata.get('selected_matches'):
            # Si no hay metadata, buscar selección activa
            try:
                selection = MatchSelection.objects.filter(
                    items__purchase_order=purchase_order,
                    status='ACTIVE'
                ).first()
                
                if selection:
                    return self.validate_contracts_approved_from_selection(selection)
                else:
                    raise PaymentValidationError('No hay matches seleccionados')
            except Exception:
                raise PaymentValidationError('No hay matches seleccionados')
        
        # Procesar metadata legacy
        selected_matches = purchase_order.metadata.get('selected_matches', [])
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
    
    def validate_payment_preconditions_from_selection(
        self,
        purchase_order: PurchaseOrder,
        selection: MatchSelection,
        payment_data: Dict[str, Any]
    ) -> None:
        """
        ✅ PRINCIPAL: Validación usando MatchSelection como fuente de verdad
        """
        # 1. Validar que la selección tenga items
        items_count = selection.items.count()
        if items_count == 0:
            raise PaymentValidationError("La selección no tiene items válidos para pago")
        
        # 2. Validar que la selección no esté expirada
        if selection.is_expired:
            raise PaymentValidationError("La selección de matches ha expirado")
        
        # 3. Validar estado de la selección
        if selection.status != 'ACTIVE':
            raise PaymentValidationError(f"La selección debe estar ACTIVE. Estado actual: {selection.status}")
        
        # 4. Validar monto (con tolerancia para decimales)
        expected_amount = float(selection.total_amount)
        provided_amount = float(payment_data.get('amount', 0))
        
        if abs(expected_amount - provided_amount) > 0.01:
            raise PaymentValidationError(
                f"El monto del pago ({provided_amount}) no coincide con el total de la selección ({expected_amount})"
            )
        
        # 5. Validar estados de órdenes relacionadas
        invalid_orders = []
        for item in selection.items.select_related('purchase_order', 'sales_order'):
            # Purchase Orders: MATCHES_SELECTED es válido para pago
            if item.purchase_order.status not in ['PENDING', 'MATCHES_SELECTED', 'PARTIALLY_EXECUTED']:
                invalid_orders.append(f"PO {item.purchase_order.order_number}: {item.purchase_order.status}")
            
            # Sales Orders: MATCHES_SELECTED es válido para pago
            if item.sales_order.status not in ['PENDING', 'MATCHES_SELECTED', 'PARTIALLY_EXECUTED']:
                invalid_orders.append(f"SO {item.sales_order.order_number}: {item.sales_order.status}")
        
        if invalid_orders:
            raise PaymentValidationError(f"Órdenes en estado inválido: {', '.join(invalid_orders)}")
        
        # 6. Validar disponibilidad de unidades en tiempo real
        unavailable_items = []
        for item in selection.items.select_related('sales_order'):
            so = item.sales_order
            available = so.available_units if so.available_units is not None else (so.units - (so.units_executed or 0))
            
            if item.units > available:
                unavailable_items.append(
                    f"SO {so.order_number}: necesita {item.units}, disponible {available}"
                )
        
        if unavailable_items:
            raise PaymentValidationError(f"Unidades no disponibles: {', '.join(unavailable_items)}")
    
    def validate_payment_preconditions(self, purchase_order: PurchaseOrder, payment_data: Dict[str, Any]) -> None:
        """
        ⚠️ LEGACY: Validación usando metadata (mantenido para compatibilidad)
        """
        # Intentar usar selección activa primero
        try:
            selection = MatchSelection.objects.filter(
                items__purchase_order=purchase_order,
                status='ACTIVE'
            ).first()
            
            if selection:
                return self.validate_payment_preconditions_from_selection(
                    purchase_order, selection, payment_data
                )
        except Exception:
            pass
        
        # Fallback a validación legacy con metadata
        self._validate_payment_preconditions_legacy(purchase_order, payment_data)
    
    def _validate_payment_preconditions_legacy(self, purchase_order: PurchaseOrder, payment_data: Dict[str, Any]) -> None:
        """Validación legacy usando metadata"""
        
        # 1. Verificar que haya metadata de selección
        if not purchase_order.metadata or not purchase_order.metadata.get('selection_summary'):
            raise PaymentValidationError('No hay información de selección en la orden')
        
        selection_summary = purchase_order.metadata['selection_summary']
        
        # 2. Verificar expiración desde metadata
        expires_at_str = selection_summary.get('expires_at')
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                if timezone.now() > expires_at:
                    raise PaymentValidationError('La selección de matches ha expirado')
            except (ValueError, TypeError):
                pass  # Si no se puede parsear, no validar expiración
        
        # 3. Validar monto
        expected_amount = float(selection_summary.get('total_amount', 0))
        provided_amount = float(payment_data.get('amount', 0))
        
        if abs(expected_amount - provided_amount) > 0.01:
            raise PaymentValidationError(
                f'El monto del pago ({provided_amount}) no coincide con el total seleccionado ({expected_amount})'
            )
        
        # 4. Verificar que haya matches seleccionados
        selected_matches = purchase_order.metadata.get('selected_matches', [])
        if not selected_matches:
            raise PaymentValidationError('No hay matches seleccionados')
        
        # 5. Verificar disponibilidad de unidades (básico)
        if selection_summary.get('total_units', 0) <= 0:
            raise PaymentValidationError('No hay unidades válidas en la selección')
    
    def handle_expired_selection_safely(self, purchase_order: PurchaseOrder) -> Dict[str, Any]:
        """
        ✅ NUEVO: Maneja selecciones expiradas usando modelos
        """
        try:
            # Buscar selección expirada
            selection = MatchSelection.objects.filter(
                items__purchase_order=purchase_order,
                status='ACTIVE'
            ).first()
            
            if selection and selection.is_expired:
                # Marcar como expirada
                selection.status = 'EXPIRED'
                selection.save(update_fields=['status'])
                
                # Limpiar estado de la purchase order
                purchase_order.status = 'PENDING'
                purchase_order.matched_at = None
                purchase_order.metadata = purchase_order.metadata or {}
                purchase_order.metadata.update({
                    'selection_expired_at': timezone.now().isoformat(),
                    'expired_selection_id': str(selection.id)
                })
                purchase_order.save(update_fields=['status', 'matched_at', 'metadata'])
                
                return {
                    'message': 'Selección expirada limpiada correctamente',
                    'order_status': purchase_order.status,
                    'selection_id': str(selection.id)
                }
            
            return {
                'message': 'No se encontró selección expirada',
                'order_status': purchase_order.status
            }
            
        except Exception as e:
            return {
                'message': f'Error al limpiar selección expirada: {str(e)}',
                'order_status': purchase_order.status
            }