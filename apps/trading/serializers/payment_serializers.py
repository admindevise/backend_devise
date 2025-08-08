# apps/trading/serializers/payment_serializers.py

from rest_framework import serializers
from typing import Dict, Any
from django.utils import timezone

from apps.trading.models.core_models import PurchaseOrder
from apps.trading.models.selection_models import MatchSelection
from apps.trading.services.payment_execution_service import PaymentExecutionService
from apps.trading.services_core.selection_service import MatchSelectionService

class PaymentExecutionSerializer(serializers.Serializer):
    """Serializer optimizado para ejecución de pagos con arquitectura nueva"""
    
    purchase_order_id = serializers.UUIDField(required=True)
    payment_method = serializers.CharField(
        max_length=50, 
        required=False, 
        default='automatic'
    )
    reference = serializers.CharField(
        max_length=100, 
        required=False
    )
    metadata = serializers.JSONField(
        required=False, 
        default=dict
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment_service = PaymentExecutionService()
        self.selection_service = MatchSelectionService()
        self._cached_purchase_order = None
        self._cached_selection = None
    
    def validate_purchase_order_id(self, value):
        """Validación optimizada con arquitectura nueva"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        # 1. Obtener orden con relaciones optimizadas
        try:
            purchase_order = PurchaseOrder.objects.select_related(
                'fund',
                'supplier_user'
            ).get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")
        
        # 2. Verificar permisos básicos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para pagar esta orden")
        
        # 3. Obtener y verificar selección activa
        active_selection = self.selection_service.get_active_selection(purchase_order)
        
        if not active_selection:
            raise serializers.ValidationError(
                "No hay una selección de matches activa para esta orden. "
                "Selecciona matches antes de proceder al pago."
            )
        
        if active_selection.is_expired:
            # La selección será limpiada automáticamente por get_active_selection
            raise serializers.ValidationError(
                "La selección de matches ha expirado. "
                "Selecciona nuevos matches antes de proceder al pago."
            )
        
        # 4. Cachear para uso posterior
        self._cached_purchase_order = purchase_order
        self._cached_selection = active_selection
        
        return value
    
    def execute_payment(self) -> Dict[str, Any]:
        """Ejecución de pago con arquitectura nueva"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        purchase_order = self._cached_purchase_order
        selection = self._cached_selection
        
        payment_data = {
            'method': self.validated_data.get('payment_method', 'automatic'),
            'reference': self.validated_data.get('reference'),
            'metadata': self.validated_data.get('metadata', {}),
            'amount': selection.total_amount,  # ✅ Desde modelo estructurado
            'selection_id': selection.id
        }
        
        try:
            result = self.payment_service.execute_payment_with_selection(
                purchase_order=purchase_order,
                selection=selection,
                payment_data=payment_data,
                user=user,
                request=request
            )
            return result
            
        except Exception as e:
            raise serializers.ValidationError(str(e))


class PaymentValidationSerializer(serializers.Serializer):
    """Serializer para validación pre-pago con arquitectura nueva"""
    
    purchase_order_id = serializers.UUIDField(required=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_service = MatchSelectionService()
        self._cached_purchase_order = None
        self._cached_selection = None
    
    def validate_purchase_order_id(self, value):
        """Validación optimizada"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        try:
            purchase_order = PurchaseOrder.objects.select_related(
                'fund', 'supplier_user'
            ).get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")
        
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para esta orden")
        
        # Obtener selección activa
        active_selection = self.selection_service.get_active_selection(purchase_order)
        
        self._cached_purchase_order = purchase_order
        self._cached_selection = active_selection
        
        return value
    
    def get_payment_info(self) -> Dict[str, Any]:
        """Información completa del pago usando modelos estructurados"""
        
        purchase_order = self._cached_purchase_order
        selection = self._cached_selection
        
        if not selection:
            return {
                'order_number': purchase_order.order_number,
                'order_id': str(purchase_order.id),
                'status': purchase_order.status,
                'ready_for_payment': False,
                'has_active_selection': False,
                'warning': 'No hay selección de matches activa.',
                'action_required': 'select_matches'
            }
        
        is_expired = selection.is_expired
        
        return {
            'order_number': purchase_order.order_number,
            'order_id': str(purchase_order.id),
            'status': purchase_order.status,
            
            # ✅ Datos desde modelo estructurado
            'selection_id': selection.id,
            'total_amount': float(selection.total_amount),
            'total_units': selection.total_units,
            'expected_savings': float(selection.expected_savings),
            'matches_count': selection.items.count(),
            
            # ✅ Información de tiempo precisa
            'selected_at': selection.selected_at.isoformat(),
            'expires_at': selection.expires_at.isoformat(),
            'time_remaining_seconds': selection.time_remaining.total_seconds(),
            'is_expired': is_expired,
            
            # ✅ Estado de pago
            'ready_for_payment': not is_expired and selection.status == 'ACTIVE',
            'has_active_selection': True,
            'selection_status': selection.status,
            
            # Información adicional
            'fund_name': purchase_order.fund.name,
            'units_requested': purchase_order.units,
            
            # ✅ Mensajes específicos
            'warning': 'La selección ha expirado.' if is_expired else None,
            'action_required': 'select_new_matches' if is_expired else None
        }


""" from rest_framework import serializers
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime
from django.utils import timezone

from apps.trading.models.core_models import PurchaseOrder
from apps.trading.services.payment_execution_service import PaymentExecutionService, PaymentExecutionError

class PaymentExecutionSerializer(serializers.Serializer):

    
    purchase_order_id = serializers.UUIDField(required=True)
    payment_method = serializers.CharField(
        max_length=50, 
        required=False, 
        default='automatic',
        help_text="Método de pago (opcional, se genera automático)"
    )
    reference = serializers.CharField(
        max_length=100, 
        required=False,
        help_text="Referencia de pago (opcional, se genera automático)"
    )
    metadata = serializers.JSONField(
        required=False, 
        default=dict,
        help_text="Metadatos adicionales del pago"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment_service = PaymentExecutionService()
        self._cached_purchase_order = None
    
    def _clean_expired_selection_immediately(self, purchase_order):

        
        if not purchase_order.metadata:
            return False
            
        expires_at_str = purchase_order.metadata.get('selection_summary', {}).get('expires_at')
        
        if not expires_at_str:
            return False
            
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if timezone.now() > expires_at:
                # ✅ LIMPIAR INMEDIATAMENTE
                purchase_order.status = 'PENDING'
                purchase_order.matched_at = None
                purchase_order.metadata = {
                    'selection_expired_at': timezone.now().isoformat(),
                    'expired_reason': 'Selection expired during payment attempt'
                }
                purchase_order.save(update_fields=['status', 'matched_at', 'metadata'])
                print(f"✅ Order {purchase_order.order_number} expired and cleaned")
                return True
        except ValueError:
            # Si hay error en fecha, también limpiar
            purchase_order.status = 'PENDING'
            purchase_order.matched_at = None
            purchase_order.metadata = {
                'selection_expired_at': timezone.now().isoformat(),
                'expired_reason': 'Invalid date format'
            }
            purchase_order.save(update_fields=['status', 'matched_at', 'metadata'])
            return True
        
        return False
    
    def validate_purchase_order_id(self, value):
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        # ✅ OPTIMIZACIÓN: Una consulta con select_related
        try:
            purchase_order = PurchaseOrder.objects.select_related(
                'fund',
                'supplier_user'
            ).get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")
        
        # ✅ VERIFICAR Y LIMPIAR EXPIRACIÓN ANTES DE CUALQUIER OTRA VALIDACIÓN
        was_expired = self._clean_expired_selection_immediately(purchase_order)
        
        if was_expired:
            raise serializers.ValidationError(
                "La selección de matches ha expirado y se ha limpiado automáticamente. "
                "Puedes seleccionar nuevos matches ahora."
            )
        
        # ✅ SOLO permisos básicos después de verificar expiración
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para pagar esta orden")
        
        # Cachear la orden
        self._cached_purchase_order = purchase_order
        return value
    
    def execute_payment(self) -> Dict[str, Any]:
        
        request = self.context.get('request')
        user = request.user if request else None
        purchase_order = self._cached_purchase_order
        
        # ✅ RECARGAR después de posible limpieza
        purchase_order.refresh_from_db()
        
        payment_data = {
            'method': self.validated_data.get('payment_method', 'automatic'),
            'reference': self.validated_data.get('reference'),
            'metadata': self.validated_data.get('metadata', {})
        }
        
        try:
            # ✅ El service ya no maneja expiración
            result = self.payment_service.execute_payment_and_matches(
                purchase_order=purchase_order,
                payment_data=payment_data,
                user=user,
                request=request
            )
            return result
            
        except PaymentExecutionError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error inesperado: {str(e)}")


class PaymentValidationSerializer(serializers.Serializer):

    
    purchase_order_id = serializers.UUIDField(required=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_purchase_order = None
    
    def _clean_expired_selection_immediately(self, purchase_order):
        
        
        if not purchase_order.metadata:
            return False
            
        expires_at_str = purchase_order.metadata.get('selection_summary', {}).get('expires_at')
        
        if not expires_at_str:
            return False
            
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if timezone.now() > expires_at:
                purchase_order.status = 'PENDING'
                purchase_order.matched_at = None
                purchase_order.metadata = {
                    'selection_expired_at': timezone.now().isoformat(),
                    'expired_reason': 'Selection expired during validation'
                }
                purchase_order.save(update_fields=['status', 'matched_at', 'metadata'])
                return True
        except ValueError:
            purchase_order.status = 'PENDING'
            purchase_order.matched_at = None
            purchase_order.metadata = {
                'selection_expired_at': timezone.now().isoformat(),
                'expired_reason': 'Invalid date format'
            }
            purchase_order.save(update_fields=['status', 'matched_at', 'metadata'])
            return True
        
        return False
    
    def validate_purchase_order_id(self, value):
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        try:
            purchase_order = PurchaseOrder.objects.select_related(
                'fund',
                'supplier_user'
            ).get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")
        
        # ✅ VERIFICAR Y LIMPIAR EXPIRACIÓN
        was_expired = self._clean_expired_selection_immediately(purchase_order)
        
        # Solo permisos básicos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para esta orden")
        
        self._cached_purchase_order = purchase_order
        return value
    
    def get_payment_info(self) -> Dict[str, Any]:
        
        
        purchase_order = self._cached_purchase_order
        
        # ✅ RECARGAR después de posible limpieza
        purchase_order.refresh_from_db()
        
        # ✅ VERIFICAR EXPIRACIÓN NUEVAMENTE
        was_expired = self._clean_expired_selection_immediately(purchase_order)
        
        if was_expired:
            purchase_order.refresh_from_db()
        
        # ✅ INFORMACIÓN BASADA EN ESTADO ACTUAL
        metadata = purchase_order.metadata or {}
        selection_summary = metadata.get('selection_summary', {})
        selected_matches = metadata.get('selected_matches', [])
        
        # Verificar si está expirado AHORA
        is_currently_expired = False
        expires_at_str = selection_summary.get('expires_at')
        
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                is_currently_expired = timezone.now() > expires_at
            except ValueError:
                is_currently_expired = True
        
        payment_info = {
            'order_number': purchase_order.order_number,
            'order_id': str(purchase_order.id),
            'status': purchase_order.status,
            'total_amount': selection_summary.get('total_amount', 0),
            'matches_count': len(selected_matches),
            'expires_at': expires_at_str,
            'is_expired': is_currently_expired or was_expired,
            'savings': selection_summary.get('savings', 0),
            'ready_for_payment': (
                not is_currently_expired and 
                not was_expired and 
                purchase_order.status == 'MATCHES_SELECTED' and 
                bool(selected_matches)
            ),
            'fund_name': purchase_order.fund.name,
            'units_requested': purchase_order.units,
            'available_units': purchase_order.available_units or purchase_order.units,
        }
        
        # ✅ MENSAJES ESPECÍFICOS
        if is_currently_expired or was_expired:
            payment_info['warning'] = 'La selección ha expirado y se ha limpiado automáticamente.'
            payment_info['action_required'] = 'select_new_matches'
        elif not selected_matches:
            payment_info['warning'] = 'No hay matches seleccionados.'
            payment_info['action_required'] = 'select_matches'
        elif purchase_order.status != 'MATCHES_SELECTED':
            payment_info['warning'] = f'Estado actual: {purchase_order.status}.'
            payment_info['action_required'] = 'wait_or_select_matches'
        
        return payment_info """