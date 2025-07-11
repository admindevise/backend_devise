# apps/trading/serializers/payment_serializers.py
from rest_framework import serializers
from decimal import Decimal
from typing import Dict, Any

from apps.trading.models import PurchaseOrder
from apps.trading.services.payment_execution_service import PaymentExecutionService, PaymentExecutionError

class PaymentExecutionSerializer(serializers.Serializer):
    """
    Serializer para manejar la ejecución de pagos y matches
    """
    
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
    
    def validate_purchase_order_id(self, value):
        """Validar que la orden existe y el usuario tiene permisos"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        try:
            purchase_order = PurchaseOrder.objects.get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")
        
        # Verificar permisos
        if not user.is_staff and purchase_order.created_by != user:
            raise serializers.ValidationError("No tienes permisos para pagar esta orden")
        
        # Guardar la orden en el contexto para uso posterior
        self._purchase_order = purchase_order
        return value
    
    def validate(self, attrs):
        """Validaciones adicionales del conjunto de datos"""
        
        # La orden ya fue validada en validate_purchase_order_id
        purchase_order = self._purchase_order
        
        # Validar estado de la orden
        if purchase_order.status != 'MATCHES_SELECTED':
            raise serializers.ValidationError({
                'purchase_order_id': f'La orden debe estar en estado MATCHES_SELECTED. Estado actual: {purchase_order.status}'
            })
        
        # Validar que tenga matches seleccionados
        if not purchase_order.metadata.get('selected_matches'):
            raise serializers.ValidationError({
                'purchase_order_id': 'No se encontraron matches seleccionados en la orden'
            })
        
        return attrs
    
    def execute_payment(self) -> Dict[str, Any]:
        """
        Ejecuta el pago completo usando el servicio
        
        Returns:
            Dict con los resultados de la ejecución
            
        Raises:
            serializers.ValidationError: Si hay errores en la ejecución
        """
        
        request = self.context.get('request')
        user = request.user if request else None
        purchase_order = self._purchase_order
        
        # Preparar datos de pago
        payment_data = {
            'method': self.validated_data.get('payment_method', 'automatic'),
            'reference': self.validated_data.get('reference'),
            'metadata': self.validated_data.get('metadata', {})
        }
        
        try:
            # Ejecutar usando el servicio
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
    """
    Serializer solo para validar que una orden puede ser pagada
    """
    
    purchase_order_id = serializers.UUIDField(required=True)
    
    def validate_purchase_order_id(self, value):
        """Validar estado de la orden para pago"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        try:
            purchase_order = PurchaseOrder.objects.get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")
        
        # Verificar permisos
        if not user.is_staff and purchase_order.created_by != user:
            raise serializers.ValidationError("No tienes permisos para esta orden")
        
        # Verificar estado
        if purchase_order.status != 'MATCHES_SELECTED':
            raise serializers.ValidationError(
                f'La orden debe estar en estado MATCHES_SELECTED. Estado actual: {purchase_order.status}'
            )
        
        # Verificar matches
        if not purchase_order.metadata.get('selected_matches'):
            raise serializers.ValidationError('No hay matches seleccionados')
        
        # Verificar expiración
        from datetime import datetime
        from django.utils import timezone
        
        expires_at_str = purchase_order.metadata.get('selection_summary', {}).get('expires_at')
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                if timezone.now() > expires_at:
                    raise serializers.ValidationError('La selección de matches ha expirado')
            except ValueError:
                pass  # Ignorar errores de formato de fecha
        
        return value
    
    def get_payment_info(self) -> Dict[str, Any]:
        """Obtiene información del pago a realizar"""
        
        purchase_order_id = self.validated_data['purchase_order_id']
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        
        selection_summary = purchase_order.metadata.get('selection_summary', {})
        
        return {
            'order_number': purchase_order.order_number,
            'total_amount': selection_summary.get('total_amount', 0),
            'matches_count': len(purchase_order.metadata.get('selected_matches', [])),
            'expires_at': selection_summary.get('expires_at'),
            'savings': selection_summary.get('savings', 0),
            'ready_for_payment': True
        }