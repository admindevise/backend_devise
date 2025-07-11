# apps/trading/serializers/match_selection_serializers.py
from rest_framework import serializers
from typing import Dict, Any, List
from django.utils import timezone

from apps.trading.models import PurchaseOrder
from apps.trading.services.match_selection_service import (
    MatchSelectionService, 
    MatchSelectionError,
    InsufficientUnitsWarning
)

class AutoMatchSelectionSerializer(serializers.Serializer):
    """Serializer para selección automática de matches"""
    
    purchase_order_id = serializers.UUIDField(required=True)
    force_partial = serializers.BooleanField(
        required=False, 
        default=False,
        help_text="Si True, acepta comprar menos unidades de las solicitadas"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_service = MatchSelectionService()
    
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
        
        # Verificar permisos básicos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para seleccionar matches de esta orden")
        
        # Verificar estado
        if purchase_order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
            raise serializers.ValidationError(
                f"La orden debe estar PENDING o PARTIALLY_EXECUTED. Estado actual: {purchase_order.status}"
            )
        
        # Guardar la orden en el contexto para uso posterior
        self._purchase_order = purchase_order
        return value
    
    def process_auto_selection(self) -> Dict[str, Any]:
        """Procesa la selección automática de matches"""
        
        request = self.context.get('request')
        user = request.user if request else None
        purchase_order = self._purchase_order
        force_partial = self.validated_data.get('force_partial', False)
        
        try:
            # Procesar usando el servicio unificado
            result = self.selection_service.process_auto_match_selection(
                purchase_order=purchase_order,
                user=user,
                force_partial=force_partial,
                request=request
            )
            
            return result
            
        except InsufficientUnitsWarning as w:
            # Para advertencias, devolver la información sin error
            return w.warning_data
        except MatchSelectionError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error inesperado: {str(e)}")

class MatchSelectionSerializer(serializers.Serializer):
    """Serializer para selección manual de matches específicos"""
    
    purchase_order_id = serializers.UUIDField(required=True)
    selected_matches = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        min_length=1,
        help_text="Lista de matches seleccionados con formato: [{'sales_order_id': 'uuid', 'units': 5}]"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_service = MatchSelectionService()
    
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
        
        # Verificar permisos básicos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para seleccionar matches de esta orden")
        
        # Guardar la orden en el contexto para uso posterior
        self._purchase_order = purchase_order
        return value
    
    def validate_selected_matches(self, value):
        """Validar formato de matches seleccionados"""
        
        if not isinstance(value, list):
            raise serializers.ValidationError("selected_matches debe ser una lista")
        
        for i, match in enumerate(value):
            if not isinstance(match, dict):
                raise serializers.ValidationError(f"Match {i} debe ser un objeto")
            
            # Verificar que tenga al menos uno de los identificadores
            if not match.get('sales_order_id') and match.get('match_index') is None:
                raise serializers.ValidationError(
                    f"Match {i} debe tener 'sales_order_id' o 'match_index'"
                )
            
            # Validar unidades si se especifican
            units = match.get('units')
            if units is not None:
                if not isinstance(units, int) or units <= 0:
                    raise serializers.ValidationError(
                        f"Match {i}: 'units' debe ser un entero positivo"
                    )
            
            # Validar match_index si se especifica
            match_index = match.get('match_index')
            if match_index is not None:
                if not isinstance(match_index, int) or match_index < 0:
                    raise serializers.ValidationError(
                        f"Match {i}: 'match_index' debe ser un entero no negativo"
                    )
        
        return value
    
    def process_selection(self) -> Dict[str, Any]:
        """Procesa la selección manual de matches"""
        
        request = self.context.get('request')
        user = request.user if request else None
        purchase_order = self._purchase_order
        selected_matches = self.validated_data['selected_matches']
        
        try:
            # Procesar usando el servicio unificado
            result = self.selection_service.process_match_selection(
                purchase_order=purchase_order,
                selected_matches=selected_matches,
                user=user,
                request=request
            )
            
            return result
            
        except MatchSelectionError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error inesperado: {str(e)}")

class MatchSelectionValidationSerializer(serializers.Serializer):
    """Serializer solo para validar que una orden puede seleccionar matches"""
    
    purchase_order_id = serializers.UUIDField(required=True)
    
    def validate_purchase_order_id(self, value):
        """Validar que la orden existe y está en estado válido"""
        
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("Usuario no identificado")
        
        try:
            purchase_order = PurchaseOrder.objects.get(id=value)
        except PurchaseOrder.DoesNotExist:
            raise serializers.ValidationError("Orden de compra no encontrada")
        
        # Verificar permisos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise serializers.ValidationError("No tienes permisos para esta orden")
        
        # Verificar estado
        if purchase_order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
            raise serializers.ValidationError(
                f"La orden debe estar PENDING o PARTIALLY_EXECUTED. Estado actual: {purchase_order.status}"
            )
        
        self._purchase_order = purchase_order
        return value
    
    def get_available_matches(self) -> Dict[str, Any]:
        """Obtiene los matches disponibles para la orden"""
        
        try:
            from apps.trading.order_matching import OrderMatch
            
            purchase_order = self._purchase_order
            matcher = OrderMatch()
            available_matches = matcher.find_matches_for_order(purchase_order)
            
            # Formatear matches para respuesta
            formatted_matches = []
            for i, match in enumerate(available_matches):
                sales_order = match['sales_order']
                formatted_matches.append({
                    'match_index': i,
                    'sales_order_id': str(sales_order.id),
                    'sales_order_number': sales_order.order_number,
                    'seller_email': sales_order.seller_user.email,
                    'available_units': sales_order.available_units or sales_order.units,
                    'price_per_unit': float(sales_order.price_per_unit),
                    'max_tradeable_units': match.get('matched_units', 0),
                    'estimated_cost': float(match.get('total_amount', 0))
                })
            
            return {
                'success': True,
                'purchase_order_id': str(purchase_order.id),
                'purchase_order_status': purchase_order.status,
                'available_matches': formatted_matches,
                'matches_count': len(formatted_matches),
                'budget_remaining': float(purchase_order.total_amount),
                'units_to_buy': purchase_order.units
            }
            
        except Exception as e:
            raise serializers.ValidationError(f"Error obteniendo matches: {str(e)}")