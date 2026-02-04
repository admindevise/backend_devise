from rest_framework import serializers
from typing import Dict, Any
from django.utils import timezone

from apps.trading.models.core_models import PurchaseOrder
from apps.trading.models.selection_models import MatchSelection
from apps.trading.services_core.payment_core_service import PaymentCoreService, PaymentCoreError


class PaymentExecutionSerializer(serializers.Serializer):
    """
    Serializer para ejecutar pagos usando el nuevo flujo basado en modelos.
    
    Flujo:
    1. Obtiene MatchSelection activa (fuente de verdad)
    2. Verifica que contratos estén aprobados por admin
    3. Ejecuta pago bancario usando selection.total_amount
    4. Ejecuta transferencias de tokens reales
    5. Finaliza y audita la operación
    """
    
    # Campos obligatorios
    purchase_order_id = serializers.UUIDField(
        required=True,
        help_text="ID de la orden de compra que tiene selección activa"
    )
    
    # Campos opcionales para el pago
    payment_method = serializers.ChoiceField(
        choices=[
            ('automatic', 'Automático'),
            ('CREDIT_CARD', 'Tarjeta de Crédito'),
            ('BANK_TRANSFER', 'Transferencia Bancaria'),
            ('PSE', 'PSE')
        ],
        default='automatic',
        required=False,
        help_text="Método de pago (ficticio para demo)"
    )
    
    reference = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Referencia externa del pago (opcional)"
    )
    
    metadata = serializers.DictField(
        required=False,
        help_text="Metadata adicional para el pago"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment_service = PaymentCoreService()
        self._cached_purchase_order = None
        self._cached_selection = None
    
    def validate_purchase_order_id(self, value):
        """Valida que la orden exista, tenga selección activa y contratos aprobados"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        # Obtener la orden con relaciones necesarias
        try:
            purchase_order = PurchaseOrder.objects.select_related(
                'fund',
                'supplier_user'
            ).get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")
        
        # Verificar permisos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para pagar esta orden")
        
        # Verificar estado de la orden
        if purchase_order.status not in ['MATCHES_SELECTED', 'PENDING', 'PARTIALLY_EXECUTED']:
            raise serializers.ValidationError(
                f"La orden debe estar en estado MATCHES_SELECTED, PENDING o PARTIALLY_EXECUTED. Estado actual: {purchase_order.status}"
            )
        
        # Buscar selección activa que tenga esta PO como main order
        try:
            selection = purchase_order.match_selection  # Relación directa OneToOne
            if selection.status != 'ACTIVE':
                raise MatchSelection.DoesNotExist()
            if selection.is_expired:
                raise serializers.ValidationError(
                    "La selección de matches ha expirado. "
                    "Debes crear una nueva selección antes de proceder al pago."
                )
        except MatchSelection.DoesNotExist:
            # ALTERNATIVA: Buscar selecciones donde esta PO esté como item
            selection = MatchSelection.objects.filter(
                items__purchase_order=purchase_order,
                status='ACTIVE'
            ).select_related('sales_order').prefetch_related(
                'items__sales_order',
                'items__purchase_order'
            ).first()
            
            if not selection:
                raise serializers.ValidationError(
                    "No hay una selección de matches activa para esta orden de compra. "
                    "Debes crear una selección antes de proceder al pago."
                )
            
            if selection.is_expired:
                raise serializers.ValidationError(
                    "La selección de matches ha expirado. "
                    "Debes crear una nueva selección antes de proceder al pago."
                )
        
        # Verificar que tenga items
        if not selection.items.exists():
            raise serializers.ValidationError(
                "La selección no tiene items válidos para procesar el pago"
            )
        
        # Cachear para uso posterior
        self._cached_purchase_order = purchase_order
        self._cached_selection = selection
        
        return value
    
    def validate(self, attrs):
        """Validaciones cruzadas y preparación final"""
        
        # Validar que tengamos los objetos cacheados
        if not self._cached_purchase_order or not self._cached_selection:
            raise serializers.ValidationError("Error en validación de orden o selección")
        
        # Verificar disponibilidad del servicio de pago
        try:
            validation_info = self.payment_service.get_payment_validation_info(
                self._cached_purchase_order
            )
            
            if not validation_info.get('can_pay', False):
                reason = validation_info.get('reason', 'unknown')
                message = validation_info.get('message', 'No se puede proceder al pago')
                
                if reason == 'pending':
                    raise serializers.ValidationError(
                        f"Contratos pendientes de aprobación: {message}"
                    )
                else:
                    raise serializers.ValidationError(message)
                    
        except PaymentCoreError as e:
            raise serializers.ValidationError(f"Error de validación de pago: {str(e)}")
        
        return attrs
    
    def execute_payment(self) -> Dict[str, Any]:
        """Ejecuta el pago completo usando el nuevo flujo"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        purchase_order = self._cached_purchase_order
        selection = self._cached_selection
        
        # Preparar datos de pago desde la selección (fuente de verdad)
        payment_data = {
            'method': self.validated_data.get('payment_method', 'automatic'),
            'reference': self.validated_data.get('reference'),
            'metadata': self.validated_data.get('metadata', {}),
            'amount': float(selection.total_amount),
            'selection_id': str(selection.id)
        }
        
        try:
            # Ejecutar pago usando el servicio core
            result = self.payment_service.execute_with_selection(
                purchase_order=purchase_order,
                payment_data=payment_data,
                user=user,
                request=request
            )
            
            # Enriquecer respuesta con información de la selección
            result.update({
                'selection_summary': {
                    'selection_id': str(selection.id),
                    'total_amount': float(selection.total_amount),
                    'total_units': selection.total_units,
                    'expected_savings': float(selection.expected_savings),
                    'items_count': selection.items.count(),
                    'status': selection.status
                },
                'order_summary': {
                    'order_id': str(purchase_order.id),
                    'order_number': purchase_order.order_number,
                    'order_status': purchase_order.status,
                    'buyer_email': purchase_order.supplier_user.email,
                    'fund_name': purchase_order.fund.name
                }
            })
            
            return result
            
        except PaymentCoreError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error inesperado en pago: {str(e)}")


class PaymentValidationSerializer(serializers.Serializer):
    """
    Serializer para validar si una orden puede proceder al pago.
    Proporciona información detallada sobre el estado de contratos y selecciones.
    """
    
    purchase_order_id = serializers.UUIDField(
        required=True,
        help_text="ID de la orden de compra a validar"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment_service = PaymentCoreService()
    
    def validate_purchase_order_id(self, value):
        """Valida que la orden exista y sea accesible"""
        
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
        
        # Verificar permisos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para consultar esta orden")
        
        return value
    
    def get_validation_info(self) -> Dict[str, Any]:
        """Obtiene información completa de validación de pago"""
        
        purchase_order_id = self.validated_data['purchase_order_id']
        
        try:
            purchase_order = PurchaseOrder.objects.select_related(
                'fund', 'supplier_user'
            ).get(id=purchase_order_id)
            
            # Usar el servicio para obtener información de validación
            validation_info = self.payment_service.get_payment_validation_info(purchase_order)
            
            return validation_info
            
        except PurchaseOrder.DoesNotExist:
            return {
                'can_pay': False,
                'reason': 'order_not_found',
                'message': 'Orden de compra no encontrada'
            }
        except Exception as e:
            return {
                'can_pay': False,
                'reason': 'validation_error',
                'message': f'Error en validación: {str(e)}'
            }


class PaymentStatusSerializer(serializers.Serializer):
    """
    Serializer para consultar el estado de pagos de una orden.
    Proporciona historial de pagos y estado actual.
    """
    
    purchase_order_id = serializers.UUIDField(
        required=True,
        help_text="ID de la orden de compra"
    )
    
    def validate_purchase_order_id(self, value):
        """Valida acceso a la orden"""
        
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
        
        # Verificar permisos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para consultar esta orden")
        
        return value
    
    def get_payment_status(self) -> Dict[str, Any]:
        """Obtiene estado completo de pagos para la orden"""
        
        from apps.trading.models.selection_models import PaymentRecord
        
        purchase_order_id = self.validated_data['purchase_order_id']
        
        try:
            purchase_order = PurchaseOrder.objects.select_related(
                'fund', 'supplier_user'
            ).get(id=purchase_order_id)
            
            # Obtener registros de pago
            payment_records = PaymentRecord.objects.filter(
                purchase_order=purchase_order
            ).order_by('-initiated_at')  # ✅ CORREGIDO: initiated_at existe, created_at no
            
            # ✅ CORREGIDO: Buscar selección activa
            active_selection = None
            try:
                active_selection = purchase_order.match_selection
                if active_selection.status != 'ACTIVE' or active_selection.is_expired:
                    active_selection = None
            except MatchSelection.DoesNotExist:
                # Buscar como item en otras selecciones
                active_selection = MatchSelection.objects.filter(
                    items__purchase_order=purchase_order,
                    status='ACTIVE'
                ).first()
                if active_selection and active_selection.is_expired:
                    active_selection = None
            
            # Construir respuesta
            payment_history = []
            for record in payment_records:
                payment_history.append({
                    'id': record.id,
                    'amount': float(record.amount),
                    'payment_method': record.payment_method,
                    'reference': record.reference,
                    'status': record.status,
                    'initiated_at': record.initiated_at.isoformat(),  # ✅ CORREGIDO
                    'processed_at': record.processed_at.isoformat() if record.processed_at else None,
                    'completed_at': record.completed_at.isoformat() if record.completed_at else None,
                    'failed_at': record.failed_at.isoformat() if record.failed_at else None,
                    'bank_transaction_id': record.bank_transaction_id,
                    'bank_reference': record.bank_reference
                })
            
            return {
                'order_summary': {
                    'order_id': str(purchase_order.id),
                    'order_number': purchase_order.order_number,
                    'order_status': purchase_order.status,
                    'buyer_email': purchase_order.supplier_user.email,
                    'fund_name': purchase_order.fund.name,
                    'paid_at': purchase_order.paid_at.isoformat() if hasattr(purchase_order, 'paid_at') and purchase_order.paid_at else None,
                    'processing_payment_at': purchase_order.processing_payment_at.isoformat() if hasattr(purchase_order, 'processing_payment_at') and purchase_order.processing_payment_at else None
                },
                'active_selection': {
                    'has_active_selection': active_selection is not None,
                    'selection_id': str(active_selection.id) if active_selection else None,
                    'total_amount': float(active_selection.total_amount) if active_selection else None,
                    'expires_at': active_selection.expires_at.isoformat() if active_selection else None,
                    'is_expired': active_selection.is_expired if active_selection else None
                },
                'payment_history': payment_history,
                'payment_summary': {
                    'total_payments': len(payment_history),
                    'successful_payments': len([p for p in payment_history if p['status'] == 'COMPLETED']),
                    'failed_payments': len([p for p in payment_history if p['status'] == 'FAILED']),
                    'pending_payments': len([p for p in payment_history if p['status'] in ['INITIATED', 'PROCESSING']])
                }
            }
            
        except Exception as e:
            return {
                'error': f'Error obteniendo estado de pagos: {str(e)}'
            }