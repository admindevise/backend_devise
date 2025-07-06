from rest_framework import serializers
from django.utils import timezone
from django.db import transaction

from apps.trading.service.order_service import OrderCreationService, OrderManagementService
from apps.user.models import User
from apps.trading.models import (
    PurchaseOrder,
    SalesOrder,
    Transaction,
    OrderBook
)

class BaseOrderSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    paid_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    completed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    cancelled_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    
    # Campos comunes para ambos serializadores
    common_fields = [
        'id', 'order_number', 'units', 'available_units', 'expiration_date', 'margin',
        'status', 'fund', 'fund_name', 'created_by',
        'paid_at', 'completed_at', 'cancelled_at', 'created_at',
        'min_acceptable_price', 'max_acceptable_price', 'days_until_expiration', 'price_per_unit', 'total_amount',
    ]
    
    common_read_only = ['order_number', 'total_amount', 'approved_at', 'paid_at', 'completed_at', 'cancelled_at']
    
    order_prefix = 'OR'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ NUEVO: Inicializar servicios de trading
        self.order_creation_service = OrderCreationService()
        self.order_management_service = OrderManagementService()
    
    def validate_units(self, value):
        """Validate that units is a positive integer."""
        if value <= 0:
            raise serializers.ValidationError("Units must be a positive integer.")
        return value
    
    def validate_expiration_date(self, value):
        """Validate that expiration_date is in the future."""
        if value <= timezone.now().date():
            raise serializers.ValidationError("Expiration date must be in the future.")
        return value
    
    def validate_margin(self, value):
        """Validate that margin is a positive number."""
        if value < 0:
            raise serializers.ValidationError("Margin must be a positive number.")
        return value
    
    def validate_status(self, value):
        """Validate that status is a valid option."""
        valid_statuses = ['PENDING', 'APPROVED', 'COMPLETED', 'CANCELLED']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Estado inválido. Opciones válidas: {valid_statuses}")
        return value
    
    def validate(self, data):
        """
        Validate that price_per_unit is not less than fund's price_per_unit
        and calculate total_amount based on units and price_per_unit.
        """
        if 'price_per_unit' in data and 'fund' in data:
            if data['price_per_unit'] < data['fund'].price_per_unit:
                raise serializers.ValidationError(
                    f"Price per unit must be greater than or equal to fund's price per unit ({data['fund'].price_per_unit})"
                )
        
        if 'units' in data and 'price_per_unit' in data:
            data['total_amount'] = data['units'] * data['price_per_unit']
        
        return data
    
    def create(self, validated_data):
        if 'created_by' not in validated_data:
            if 'request' in self.context:
                validated_data['created_by'] = self.context['request'].user
            else:
                raise serializers.ValidationError("No se pudo determinar el usuario para 'created_by'")
        
        # Obtener el siguiente número de orden de forma segura (atómica)
        with transaction.atomic():
            # Determinar la clase del modelo según el serializador
            if self.order_prefix == 'PO':
                model_class = PurchaseOrder
            else:  # SO
                model_class = SalesOrder
                
            # Buscar el último número usado para este tipo de orden
            last_order = model_class.objects.filter(
                order_number__startswith=f"{self.order_prefix}-"
            ).order_by('order_number').last()
            
            if last_order and last_order.order_number:
                # Extraer el número del último order_number
                try:
                    last_number = int(last_order.order_number.split('-')[1])
                    next_number = last_number + 1
                except (IndexError, ValueError):
                    next_number = 1
            else:
                next_number = 1
            
            # Generar el order_number con 8 dígitos
            validated_data['order_number'] = f"{self.order_prefix}-{next_number:08d}"
            
            # Verificar que el número generado no exista ya (por si acaso)
            while model_class.objects.filter(order_number=validated_data['order_number']).exists():
                next_number += 1
                validated_data['order_number'] = f"{self.order_prefix}-{next_number:08d}"
        
        return super().create(validated_data)

class PurchaseOrderSerializer(BaseOrderSerializer):
    supplier_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    order_prefix = 'PO'
    
    class Meta:
        model = PurchaseOrder
        fields = BaseOrderSerializer.common_fields + ['supplier_user']
        read_only_fields = BaseOrderSerializer.common_read_only
    
    def validate(self, data):
        """Validaciones específicas para órdenes de compra"""
        data = super().validate(data)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            data['supplier_user'] = request.user
        
        return data
    
    # ✅ NUEVO: Integración con servicio de creación segura
    @transaction.atomic
    def create(self, validated_data):
        """Crear orden de compra usando el servicio de seguridad"""
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("No se pudo determinar el usuario")
        
        validated_data = self._generate_order_number(validated_data)
        
        try:
            # Usar el servicio de creación que incluye todas las validaciones
            result = self.order_creation_service.create_purchase_order(
                user=user,
                order_data=validated_data,
                request=request
            )
            
            if not result['success']:
                raise serializers.ValidationError("Error al crear la orden de compra")
            
            return result['purchase_order']
            
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error inesperado: {str(e)}")
        
    def _generate_order_number(self, validated_data):
        """Genera el numero de orden unico"""
        last_order = PurchaseOrder.objects.filter(
            order_number__startswith=f"{self.order_prefix}-"
        ).order_by('order_number').last()
        
        if last_order and last_order.order_number:
            try:
                last_number = int(last_order.order_number.split('-')[1])
                next_number = last_number + 1
            except (IndexError, ValueError):
                next_number = 1
        else:
            next_number = 1
        
        # Generar el order_number con 8 dígitos
        validated_data['order_number'] = f"{self.order_prefix}-{next_number:08d}"
        
        # Verificar que el número generado no exista ya (por si acaso)
        while PurchaseOrder.objects.filter(order_number=validated_data['order_number']).exists():
            next_number += 1
            validated_data['order_number'] = f"{self.order_prefix}-{next_number:08d}"
        
        return validated_data

class SalesOrderSerializer(BaseOrderSerializer):
    seller_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    # ✅ NUEVO: Campo opcional para especificar tokens específicos
    token_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="Lista opcional de IDs de tokens específicos a vender"
    )
    # ✅ NUEVO: Información de tokens reservados en respuesta
    reserved_tokens_info = serializers.SerializerMethodField(read_only=True)
    
    order_prefix = 'SO'
    
    class Meta:
        model = SalesOrder
        fields = BaseOrderSerializer.common_fields + ['seller_user', 'token_ids', 'reserved_tokens_info']
        read_only_fields = BaseOrderSerializer.common_read_only + ['reserved_tokens_info']
    
    def get_reserved_tokens_info(self, obj):
        """Obtiene información de tokens reservados"""
        if hasattr(obj, 'metadata') and obj.metadata:
            reserved_tokens = obj.metadata.get('reserved_tokens', [])
            expires_at_raw = obj.metadata.get('reservation_expires_at')
            
            # ✅ ALTERNATIVA: Usar el mismo formato que created_at
            expires_at_formatted = None
            if expires_at_raw:
                try:
                    from django.utils.dateparse import parse_datetime
                    from django.utils import timezone
                    
                    # Parse the datetime string
                    if isinstance(expires_at_raw, str):
                        expires_dt = parse_datetime(expires_at_raw)
                        if expires_dt:
                            # Formatear exactamente igual que created_at
                            expires_at_formatted = expires_dt.strftime("%Y-%m-%d %H:%M:%S")
                    
                except Exception:
                    expires_at_formatted = expires_at_raw
            
            return {
                'count': len(reserved_tokens),
                'token_ids': reserved_tokens,
                'expires_at': expires_at_formatted
            }
        return None
    
    def validate(self, data):
        """Validaciones adicionales y asignacion automatica de seller_user"""
        
        data = super().validate(data)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            data['seller_user'] = request.user
    
        return data
    
    # ✅ NUEVO: Integración con servicio de creación segura
    @transaction.atomic  
    def create(self, validated_data):
        """Crear orden de venta usando el servicio de seguridad"""
        request = self.context.get('request')
        user = request.user if request else None
        token_ids = validated_data.pop('token_ids', None)  # Extraer token_ids si existe
        
        if not user:
            raise serializers.ValidationError("No se pudo determinar el usuario")
        
        validated_data = self._generate_order_number(validated_data)
        
        try:
            # Si se especificaron token_ids, validar ownership primero
            if token_ids:
                from apps.trading.security.token_validators import TradingTokenValidator
                validator = TradingTokenValidator()
                
                ownership_result = validator.validate_ownership(
                    user, token_ids, validated_data['fund'].id
                )
                
                if not ownership_result['valid']:
                    raise serializers.ValidationError({
                        'token_ownership': 'Validación de propiedad fallida',
                        'invalid_tokens': ownership_result['invalid_tokens']
                    })
                
                # Actualizar units basado en tokens especificados
                validated_data['units'] = len(token_ids)
                validated_data['total_amount'] = len(token_ids) * validated_data['price_per_unit']
            
            # Usar el servicio de creación que incluye todas las validaciones
            result = self.order_creation_service.create_sales_order(
                user=user,
                order_data=validated_data,
                request=request
            )
            
            if not result['success']:
                raise serializers.ValidationError("Error al crear la orden de venta")
            
            return result['sales_order']
            
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error inesperado: {str(e)}")
        
    def _generate_order_number(self, validated_data):
        """Genera el numero de orden unico"""
        last_order = SalesOrder.objects.filter(
            order_number__startswith=f"{self.order_prefix}-"
        ).order_by('order_number').last()
        
        if last_order and last_order.order_number:
            try:
                last_number = int(last_order.order_number.split('-')[1])
                next_number = last_number + 1
            except (IndexError, ValueError):
                next_number = 1
        else:
            next_number = 1
        
        # Generar el order_number con 8 dígitos
        validated_data['order_number'] = f"{self.order_prefix}-{next_number:08d}"
        
        # Verificar que el número generado no exista ya (por si acaso)
        while SalesOrder.objects.filter(order_number=validated_data['order_number']).exists():
            next_number += 1
            validated_data['order_number'] = f"{self.order_prefix}-{next_number:08d}"
        
        return validated_data

class OrderCancellationSerializer(serializers.Serializer):
    """Serializer para manejar cancelación de órdenes"""
    cancellation_reason = serializers.CharField(
        required=True,
        max_length=500,
        help_text="Razón opcional para la cancelación"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_management_service = OrderManagementService()
    
    def cancel_order(self, order, user, request=None):
        """Cancela una orden usando el servicio apropiado"""
        try:
            if isinstance(order, SalesOrder):
                result = self.order_management_service.cancel_sales_order(
                    order, user, request
                )
            elif isinstance(order, PurchaseOrder):
                result = self.order_management_service.cancel_purchase_order(
                    order, user, request
                )
            else:
                raise ValueError("Tipo de orden no válido")
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(f"Error al cancelar orden: {str(e)}")

# ✅ ACTUALIZADO: TransactionSerializer con validaciones mejoradas
class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions between purchase and sales orders"""
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'purchase_order',
            'sales_order',
            'buyer',
            'seller',
            'fund',
            'fund_name',
            'units',
            'price_per_unit',
            'total_amount',
            'created_at'
        ]
        read_only_fields = ['transaction_date', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ NUEVO: Servicio para ejecución de transacciones
        from apps.trading.service.order_service import TransactionExecutionService
        self.transaction_service = TransactionExecutionService()

    def validate(self, data):
        """Validaciones adicionales para transacciones"""
        purchase_order = data.get('purchase_order')
        sales_order = data.get('sales_order')
        units = data.get('units', 0)
        
        if purchase_order and sales_order:
            # Validar que las órdenes pertenezcan al mismo fondo
            if purchase_order.fund != sales_order.fund:
                raise serializers.ValidationError("Las órdenes deben pertenecer al mismo fondo")
            
            # Validar unidades disponibles
            max_units = min(purchase_order.units, sales_order.units)
            if units > max_units:
                raise serializers.ValidationError(
                    f"Units cannot exceed available units in orders. Max: {max_units}"
                )
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        """Crear transacción usando el servicio de ejecución"""
        request = self.context.get('request')
        purchase_order = validated_data['purchase_order']
        sales_order = validated_data['sales_order']
        units_to_trade = validated_data['units']
        
        try:
            # Usar el servicio de ejecución que maneja blockchain y DB
            result = self.transaction_service.execute_trade(
                purchase_order=purchase_order,
                sales_order=sales_order,
                units_to_trade=units_to_trade,
                request=request
            )
            
            if not result['success']:
                raise serializers.ValidationError("Error ejecutando la transacción")
            
            return result['transaction']
            
        except Exception as e:
            raise serializers.ValidationError(f"Error en transacción: {str(e)}")

class OrderBookSerializer(serializers.ModelSerializer):
    """Serializer for order book which shows open buy/sell orders for a fund"""
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    
    class Meta:
        model = OrderBook
        fields = [
            'id',
            'fund',
            'fund_name',
            'last_price',
            'daily_high',
            'daily_low',
            'daily_volume',
            'created_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Usar las propiedades del modelo directamente
        representation['buy_orders'] = PurchaseOrderSerializer(
            instance.buy_orders, many=True, context=self.context
        ).data
        
        representation['sell_orders'] = SalesOrderSerializer(
            instance.sell_orders, many=True, context=self.context
        ).data
        
        return representation