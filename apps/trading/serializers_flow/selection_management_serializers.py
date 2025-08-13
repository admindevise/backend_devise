from rest_framework import serializers
from typing import Dict, Any, List
from django.utils import timezone

from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from apps.trading.models.selection_models import MatchSelection, MatchSelectionItem
from apps.trading.services_core.selection_service import MatchSelectionService
from apps.trading.services_core.match_selection_core import SelectionServiceError, InsufficientUnitsWarning

class UnifiedMatchSelectionSerializer(serializers.Serializer):
    """
    Serializer unificado para manejar selecciones de matches tanto para compradores como vendedores
    """
    
    # Campos comunes
    order_id = serializers.UUIDField(required=True, help_text="ID de la orden (compra o venta)")
    order_type = serializers.ChoiceField(
        choices=['purchase', 'sales'], 
        required=True,
        help_text="Tipo de orden: 'purchase' para compra, 'sales' para venta"
    )
    selection_method = serializers.ChoiceField(
        choices=['manual', 'auto'],
        required=True,
        help_text="Método de selección: 'manual' para específico, 'auto' para automático"
    )
    
    # Campos para selección manual
    selected_matches = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Lista de matches seleccionados manualmente. Requerido para selection_method='manual'"
    )
    
    # Campos para selección automática
    force_partial = serializers.BooleanField(
        required=False, 
        default=False,
        help_text="Si True, acepta selecciones parciales cuando no hay suficientes unidades/compradores"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_service = MatchSelectionService()
        self._cached_order = None
    
    def validate(self, attrs):
        """Validación completa de la solicitud"""
        
        order_type = attrs.get('order_type')
        selection_method = attrs.get('selection_method')
        selected_matches = attrs.get('selected_matches')
        
        # Validar orden específica
        order = self._validate_and_cache_order(attrs['order_id'], order_type)
        
        # Validación específica según método de selección
        if selection_method == 'manual':
            if not selected_matches:
                raise serializers.ValidationError(
                    "selected_matches es requerido para selection_method='manual'"
                )
            self._validate_manual_matches(selected_matches, order_type)
        
        elif selection_method == 'auto':
            if selected_matches:
                raise serializers.ValidationError(
                    "selected_matches no debe especificarse para selection_method='auto'"
                )
        
        return attrs
    
    def _validate_and_cache_order(self, order_id, order_type):
        """Valida y cachea la orden según su tipo"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        try:
            if order_type == 'purchase':
                order = PurchaseOrder.objects.select_related('fund', 'supplier_user').get(id=order_id)
                user_field = 'supplier_user'
            else:  # sales
                order = SalesOrder.objects.select_related('fund', 'seller_user').get(id=order_id)
                user_field = 'seller_user'
                
        except (PurchaseOrder.DoesNotExist, SalesOrder.DoesNotExist):
            raise serializers.ValidationError(f"Orden de {order_type} no encontrada")
        
        # Verificar permisos
        order_user = getattr(order, user_field)
        if not user.is_staff and order_user != user:
            raise serializers.ValidationError(f"No tienes permisos para esta orden de {order_type}")
        
        # Verificar estado
        if order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
            raise serializers.ValidationError(
                f"La orden debe estar PENDING o PARTIALLY_EXECUTED. Estado actual: {order.status}"
            )
        
        self._cached_order = order
        return order
    
    def _validate_manual_matches(self, selected_matches, order_type):
        """Valida formato de matches para selección manual"""
        
        if not isinstance(selected_matches, list) or len(selected_matches) == 0:
            raise serializers.ValidationError("selected_matches debe ser una lista no vacía")
        
        # Determinar qué campo ID esperamos según el tipo de orden
        if order_type == 'purchase':
            expected_id_field = 'sales_order_id'
        else:  # sales
            expected_id_field = 'purchase_order_id'
        
        for i, match in enumerate(selected_matches):
            if not isinstance(match, dict):
                raise serializers.ValidationError(f"Match {i} debe ser un objeto")
            
            # Verificar que tenga al menos uno de los identificadores
            has_id = match.get(expected_id_field) is not None
            has_index = match.get('match_index') is not None
            
            if not has_id and not has_index:
                raise serializers.ValidationError(
                    f"Match {i} debe tener '{expected_id_field}' o 'match_index'"
                )
            
            # Validar unidades si se especifican
            units = match.get('units')
            if units is not None:
                if not isinstance(units, int) or units <= 0:
                    raise serializers.ValidationError(
                        f"Match {i}: 'units' debe ser un entero positivo"
                    )
    
    def process_selection(self) -> Dict[str, Any]:
        """Procesa la selección según el tipo y método especificado"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        order = self._cached_order
        order_type = self.validated_data['order_type']
        selection_method = self.validated_data['selection_method']
        
        try:
            if selection_method == 'manual':
                # Selección manual
                selected_matches = self.validated_data['selected_matches']
                result = self.selection_service.process_manual_selection(
                    order=order,
                    selected_matches=selected_matches,
                    user=user,
                    request=request
                )
            else:
                # Selección automática
                force_partial = self.validated_data.get('force_partial', False)
                result = self.selection_service.process_auto_selection(
                    order=order,
                    user=user,
                    force_partial=force_partial,
                    request=request
                )
            
            return result
            
        except InsufficientUnitsWarning as w:
            # Para advertencias, devolver la información sin error
            return w.warning_data
        except SelectionServiceError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error inesperado: {str(e)}")


class SelectionStatusSerializer(serializers.ModelSerializer):
    """
    Serializer para consultar el estado de una selección existente
    """
    
    order_id = serializers.SerializerMethodField()
    order_type = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    is_expired = serializers.SerializerMethodField()
    time_remaining_seconds = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    # Información detallada de items
    items_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = MatchSelection
        fields = [
            'id', 'status', 'total_amount', 'total_units', 'expected_savings',
            'selected_at', 'expires_at', 'metadata',
            'order_id', 'order_type', 'order_number', 'created_by_email',
            'is_expired', 'time_remaining_seconds', 'items_count', 'items_detail'
        ]
    
    def get_order_id(self, obj):
        main_order = obj.purchase_order or obj.sales_order
        return str(main_order.id) if main_order else None
    
    def get_order_type(self, obj):
        return 'purchase' if obj.purchase_order else 'sales'
    
    def get_order_number(self, obj):
        main_order = obj.purchase_order or obj.sales_order
        return main_order.order_number if main_order else None
    
    def get_is_expired(self, obj):
        return obj.is_expired
    
    def get_time_remaining_seconds(self, obj):
        if obj.is_expired:
            return 0
        return obj.time_remaining.total_seconds()
    
    def get_items_count(self, obj):
        return obj.items.count()
    
    def get_items_detail(self, obj):
        items = obj.items.select_related('sales_order', 'purchase_order').all()
        
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'sales_order_id': str(item.sales_order.id),
                'sales_order_number': item.sales_order.order_number,
                'purchase_order_id': str(item.purchase_order.id),
                'purchase_order_number': item.purchase_order.order_number,
                'seller_email': item.sales_order.seller_user.email,
                'buyer_email': item.purchase_order.supplier_user.email,
                'units': item.units,
                'price_per_unit': float(item.price_per_unit),
                'subtotal': float(item.units * item.price_per_unit),
                'buyer_savings': float(item.buyer_savings),
                'seller_gain': float(item.seller_gain),
                'metadata': item.metadata
            })
        
        return items_data


class SelectionValidationSerializer(serializers.Serializer):
    """
    Serializer para validar que una orden puede crear selecciones
    y obtener información de matches disponibles
    """
    
    order_id = serializers.UUIDField(required=True)
    order_type = serializers.ChoiceField(
        choices=['purchase', 'sales'], 
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_service = MatchSelectionService()
        self._cached_order = None
    
    def validate(self, attrs):
        """Validar que la orden existe y se puede hacer selección"""
        
        order_id = attrs['order_id']
        order_type = attrs['order_type']
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        try:
            if order_type == 'purchase':
                order = PurchaseOrder.objects.get(id=order_id)
                user_field = 'supplier_user'
            else:
                order = SalesOrder.objects.get(id=order_id)
                user_field = 'seller_user'
                
        except (PurchaseOrder.DoesNotExist, SalesOrder.DoesNotExist):
            raise serializers.ValidationError(f"Orden de {order_type} no encontrada")
        
        # Verificar permisos
        order_user = getattr(order, user_field)
        if not user.is_staff and order_user != user:
            raise serializers.ValidationError(f"No tienes permisos para esta orden")
        
        # Verificar estado
        if order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
            raise serializers.ValidationError(
                f"La orden debe estar PENDING o PARTIALLY_EXECUTED. Estado actual: {order.status}"
            )
        
        self._cached_order = order
        return attrs
    
    def get_validation_info(self) -> Dict[str, Any]:
        """Obtiene información de validación y matches disponibles"""
        
        order = self._cached_order
        order_type = self.validated_data['order_type']
        
        # Verificar si hay selección activa
        active_selection = self.selection_service.get_active_selection(order)
        
        if active_selection:
            return {
                'can_create_selection': False,
                'has_active_selection': True,
                'active_selection_id': str(active_selection.id),
                'active_selection_expires_at': active_selection.expires_at.isoformat(),
                'message': 'Ya existe una selección activa para esta orden',
                'action_required': 'cancel_existing_selection_or_proceed_to_payment'
            }
        
        # Obtener matches disponibles
        try:
            if order_type == 'purchase':
                available_matches = self.selection_service.purchase_service._get_available_matches_for_purchase(order)
            else:
                available_matches = self.selection_service.sales_service._get_available_matches_for_sales(order)
            
            matches_summary = []
            for i, match in enumerate(available_matches):
                if order_type == 'purchase':
                    target_order = match['sales_order']
                    target_user = target_order.seller_user
                else:
                    target_order = match['purchase_order']
                    target_user = target_order.supplier_user
                
                matches_summary.append({
                    'match_index': i,
                    'target_order_id': str(target_order.id),
                    'target_order_number': target_order.order_number,
                    'target_user_email': target_user.email,
                    'available_units': target_order.available_units,
                    'price_per_unit': float(target_order.price_per_unit),
                    'fund_name': target_order.fund.name
                })
            
            return {
                'can_create_selection': True,
                'has_active_selection': False,
                'order_id': str(order.id),
                'order_number': order.order_number,
                'order_type': order_type,
                'available_matches_count': len(available_matches),
                'available_matches': matches_summary,
                'order_details': {
                    'units_needed': order.available_units,
                    'budget_available': float(getattr(order, 'total_amount', 0)),
                    'price_per_unit': float(order.price_per_unit),
                    'fund_name': order.fund.name
                }
            }
            
        except Exception as e:
            return {
                'can_create_selection': False,
                'has_active_selection': False,
                'error': str(e),
                'message': 'No se pudieron obtener matches disponibles'
            }


class SelectionCancellationSerializer(serializers.Serializer):
    """
    Serializer para cancelar una selección existente
    """
    
    selection_id = serializers.UUIDField(required=True)
    cancellation_reason = serializers.CharField(
        max_length=500, 
        required=False, 
        default="Cancelled by user"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_service = MatchSelectionService()
    
    def validate_selection_id(self, value):
        """Validar que la selección existe y el usuario puede cancelarla"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        try:
            selection = MatchSelection.objects.select_related(
                'purchase_order__supplier_user',
                'sales_order__seller_user'
            ).get(id=value)
        except MatchSelection.DoesNotExist:
            raise serializers.ValidationError("Selección no encontrada")
        
        # Verificar permisos
        main_order = selection.purchase_order or selection.sales_order
        if isinstance(main_order, PurchaseOrder):
            order_user = main_order.supplier_user
        else:
            order_user = main_order.seller_user
        
        if not user.is_staff and order_user != user:
            raise serializers.ValidationError("No tienes permisos para cancelar esta selección")
        
        # Verificar que se puede cancelar
        if selection.status != 'ACTIVE':
            raise serializers.ValidationError(f"No se puede cancelar una selección con estado {selection.status}")
        
        self._cached_selection = selection
        return value
    
    def cancel_selection(self) -> Dict[str, Any]:
        """Cancela la selección y restaura el estado de la orden"""
        
        selection = self._cached_selection
        main_order = selection.purchase_order or selection.sales_order
        cancellation_reason = self.validated_data.get('cancellation_reason')
        
        # Marcar como cancelada
        selection.status = 'CANCELLED'
        selection.metadata = selection.metadata or {}
        selection.metadata.update({
            'cancelled_at': timezone.now().isoformat(),
            'cancellation_reason': cancellation_reason
        })
        selection.save(update_fields=['status', 'metadata'])
        
        # Restaurar estado de la orden
        main_order.status = 'PENDING'
        main_order.matched_at = None
        main_order.metadata = main_order.metadata or {}
        main_order.metadata.update({
            'last_selection_cancelled_at': timezone.now().isoformat(),
            'cancelled_selection_id': str(selection.id)
        })
        main_order.save(update_fields=['status', 'matched_at', 'metadata'])
        
        return {
            'success': True,
            'message': 'Selección cancelada exitosamente',
            'selection_id': str(selection.id),
            'order_id': str(main_order.id),
            'order_number': main_order.order_number,
            'new_order_status': main_order.status,
            'cancelled_at': timezone.now().isoformat(),
            'cancellation_reason': cancellation_reason
        }