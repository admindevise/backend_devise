from rest_framework import serializers
from django.utils import timezone
from django.db import transaction

from apps.trading.services.order_service import OrderCreationService, OrderManagementService
from apps.user.models import User
from apps.trading.models.core_models import (
    PurchaseOrder,
    SalesOrder,
    Transaction,
    OrderBook
)

class BaseOrderSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    processing_payment_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    partially_executed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    fully_executed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    cancelled_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    
    # Campos comunes para ambos serializadores
    common_fields = [
        'id', 'order_number', 'units', 'available_units', 'margin',
        'status', 'fund', 'fund_name',
        'min_acceptable_price', 'max_acceptable_price', 'price_per_unit', 'total_amount', 'expiration_date', 'days_until_expiration', 'metadata',
        'partially_executed_at', 'fully_executed_at', 'cancelled_at', 'matched_at' ,'created_at', 'created_by'
    ]
    
    common_read_only = ['order_number', 'total_amount', 'available_units', 'fully_executed_at', 'partially_executed_at', 'cancelled_at', 'matched_at', 'created_at']
    
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
        
        if 'units' in data:
            data['available_units'] = data['units']
            
        
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
    matched_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    processing_payment_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    paid_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    supplier_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    order_prefix = 'PO'
    
    class Meta:
        model = PurchaseOrder
        fields = BaseOrderSerializer.common_fields + ['processing_payment_at','paid_at','supplier_user']
        read_only_fields = BaseOrderSerializer.common_read_only
    
    def validate(self, data):
        """Validaciones específicas para órdenes de compra"""
        data = super().validate(data)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # ✅ NUEVO: Solo asignar automáticamente si NO se especificó supplier_user
            if 'supplier_user' not in data or data['supplier_user'] is None:
                data['supplier_user'] = request.user
            else:
                # ✅ VERIFICAR PERMISOS: Solo admin puede especificar supplier_user diferente
                if data['supplier_user'] != request.user and not request.user.is_staff:
                    raise serializers.ValidationError(
                        "Solo usuarios admin pueden crear órdenes para otros usuarios"
                    )
        
        return data
    
    # ✅ NUEVO: Integración con servicio de creación segura
    @transaction.atomic
    def create(self, validated_data):
        """Crear orden de compra usando el servicio de seguridad"""
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("No se pudo determinar el usuario")
        
        # ✅ NUEVO: Determinar usuario objetivo y usuario que crea
        supplier_user = validated_data.get('supplier_user', user)  # Usuario que compra
        created_by_user = user  # Usuario que crea (puede ser admin)
        
        # ✅ LOGGING para debugging
        if user.is_staff and supplier_user != user:
            print(f"🔧 Admin {user.email} creating purchase order for {supplier_user.email}")
        
        validated_data = self._generate_order_number(validated_data)
        
        try:
            # Usar el servicio de creación que incluye todas las validaciones
            result = self.order_creation_service.create_purchase_order(
                user=created_by_user,  # Admin que crea
                order_data=validated_data,  # Ya contiene supplier_user correcto
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
    order_prefix = 'SO'
    
    class Meta:
        model = SalesOrder
        fields = BaseOrderSerializer.common_fields + ['seller_user', 'token_ids']
        read_only_fields = BaseOrderSerializer.common_read_only
    
    def validate(self, data):
        """Validaciones adicionales y asignacion automatica de seller_user"""
        
        data = super().validate(data)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # ✅ NUEVO: Solo asignar automáticamente si NO se especificó seller_user
            if 'seller_user' not in data or data['seller_user'] is None:
                data['seller_user'] = request.user
            else:
                # ✅ VERIFICAR PERMISOS: Solo admin puede especificar seller_user diferente
                if data['seller_user'] != request.user and not request.user.is_staff:
                    raise serializers.ValidationError(
                        "Solo usuarios admin pueden crear órdenes para otros usuarios"
                    )
    
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
        
        # ✅ NUEVO: Determinar usuario objetivo y usuario que crea
        seller_user = validated_data.get('seller_user', user)  # Usuario que vende
        created_by_user = user  # Usuario que crea (puede ser admin)
        
        # ✅ LOGGING para debugging
        if user.is_staff and seller_user != user:
            print(f"🔧 Admin {user.email} creating sales order for {seller_user.email}")
        
        validated_data = self._generate_order_number(validated_data)
        
        try:
            # ✅ VALIDACIÓN DE OWNERSHIP: Usar seller_user (no el admin)
            if token_ids:
                from apps.trading.security.token_validators import TradingTokenValidator
                validator = TradingTokenValidator()
                
                # ✅ IMPORTANTE: Validar ownership del seller_user, no del admin
                ownership_result = validator.validate_ownership(
                    seller_user, token_ids, validated_data['fund'].id  # ← seller_user
                )
                
                if not ownership_result['valid']:
                    raise serializers.ValidationError({
                        'token_ownership': f'El usuario {seller_user.email} no es propietario de los tokens especificados',
                        'invalid_tokens': ownership_result['invalid_tokens']
                    })
                
                # Actualizar units basado en tokens especificados
                validated_data['units'] = len(token_ids)
                validated_data['total_amount'] = len(token_ids) * validated_data['price_per_unit']
            
            # ✅ USAR SERVICIO CON USUARIOS CORRECTOS
            # El servicio necesita saber quién crea (admin) y para quién (seller_user)
            result = self.order_creation_service.create_sales_order(
                user=created_by_user,  # Admin que crea
                order_data=validated_data,  # Ya contiene seller_user correcto
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
            'metadata',
            'created_at',
        ]
        read_only_fields = ['transaction_date', 'created_at', 'updated_at']

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
    
    