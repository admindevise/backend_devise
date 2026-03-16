from rest_framework import serializers
from django.utils import timezone
from django.db import transaction

from apps.user.models import User
from apps.fund.models.core import Fund
from apps.trading.models.core_models import (
    PurchaseOrder,
    SalesOrder,
    Transaction,
    OrderBook
)

from apps.utils.serializers.base_serializer import BaseSerializer
from apps.trading.services.order_service import OrderCreationService, OrderManagementService

# ================================================
# SERIALIZER BASE DE ÓRDENES DE COMPRA Y VENTA
# ================================================
class BaseOrderSerializer(BaseSerializer, serializers.ModelSerializer):
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    assisted_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
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
        'partially_executed_at', 'fully_executed_at', 'cancelled_at', 'matched_at' ,'created_at', 'created_by', 'is_staff_assisted', 'assistance_notes', 'authorization_channel', 'authorization_evidence', 'assisted_at',
    ]
    
    common_read_only = ['order_number', 'total_amount', 'available_units', 'fully_executed_at', 'partially_executed_at', 'cancelled_at', 'matched_at', 'created_at', 'fund']
    
    order_prefix = 'OR'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NUEVO: Inicializar servicios de trading
        self.order_creation_service = OrderCreationService()
        self.order_management_service = OrderManagementService()
    
    def validate_units(self, value):
        """Validate that units is a positive integer."""
        if value <= 0:
            raise serializers.ValidationError({
                'units': "La cantidad de unidades debe ser un número entero positivo."
            })
        return value
    
    def validate_expiration_date(self, value):
        """Validate that expiration_date is in the future."""
        if value <= timezone.now().date():
            format_time = value.strftime('%Y-%m-%d %H:%M:%S')
            raise serializers.ValidationError({
                'expiration_date': f"La fecha de expiración debe ser una fecha futura. Valor proporcionado: {format_time}"
            })
        return value
    
    def validate_margin(self, value):
        """Validate that margin is a positive number."""
        if value < 0:
            raise serializers.ValidationError({
                'margin': "El margen debe ser un numero positivo."
            })
        return value
    
    def validate_status(self, value):
        """Validate that status is a valid option."""
        valid_statuses = ['PENDING', 'APPROVED', 'COMPLETED', 'CANCELLED']
        if value not in valid_statuses:
            raise serializers.ValidationError({
                'status': f"El estado debe ser uno de los siguientes: {', '.join(valid_statuses)}."
            })
        return value
    
    def validate_assisted_at(self, value):
        """Validate that assisted_at is a valid datetime if provided."""
        if value and value > timezone.now():
            format_time = value.strftime('%Y-%m-%d %H:%M:%S')
            raise serializers.ValidationError({
                'assisted_at': f"La fecha de asistencia no puede ser en el futuro. Valor proporcionado: {format_time}"
            })
        return value
    
    def validate(self, attrs):
        """
        Validate that price_per_unit is not less than fund's price_per_unit
        and calculate total_amount based on units and price_per_unit.
        """
        # Tomar fund desde contexto (ULR) si no viene en body
        fund_id = self.context.get('fund_id')
        request = self.context.get('request')
        
        if not fund_id:
            raise serializers.ValidationError({'fund': "El campo 'fund' es obligatorio en la URL."})
    
        try:
            attrs['fund'] = Fund.objects.get(id=fund_id)
        except Fund.DoesNotExist:
            raise serializers.ValidationError({'fund': f"El fideicomiso con ID {fund_id} no existe."})
        
        # Validar price_per_unit contra el precio del fondo
        if 'price_per_unit' in attrs:
            if attrs['price_per_unit'] < attrs['fund'].price_per_unit:
                raise serializers.ValidationError(
                    {'price_per_unit': f"El precio por unidad no puede ser menor que el precio del fondo ({attrs['fund'].price_per_unit})."}
                )

        if 'units' in attrs and 'price_per_unit' in attrs:
            attrs['total_amount'] = attrs['units'] * attrs['price_per_unit']

        if 'units' in attrs:
            attrs['available_units'] = attrs['units']
            
            
        is_staff = request.user.is_staff or request.user.is_superuser
        # Si NO es creación asistida, ignorar cualquier dato enviado por el cliente
        if is_staff:
            attrs['is_staff_assisted'] = True
        if not is_staff:
            attrs['assistance_notes'] = ''
            attrs['authorization_channel'] = ''
            attrs['authorization_evidence'] = ''
            attrs['assisted_at'] = None
            return attrs

        # Si SÍ es creación asistida, entonces sí se validan como requeridos
        if not attrs.get('authorization_channel'):
            raise serializers.ValidationError({"authorization_channel": "Campo requerido para creación asistida por staff/admin."})
        if not attrs.get('authorization_evidence'):
            raise serializers.ValidationError({"authorization_evidence": "Campo requerido para creación asistida por staff/admin."})
        if not attrs.get('assistance_notes'):
            raise serializers.ValidationError({"assistance_notes": "Campo requerido para creación asistida por staff/admin."})
        if not attrs.get('assisted_at'):
            raise serializers.ValidationError({"assisted_at": "Campo requerido para creación asistida por staff/admin."})

        return attrs
    
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


# ===============================================
# SERIALIZERS ESPECÍFICOS DE ÓRDENES
# ===============================================
class PurchaseOrderSerializer(BaseOrderSerializer):
    matched_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    processing_payment_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    paid_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    supplier_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            'does_not_exist': 'El usuario con ID "{pk_value}" no existe en el sistema.',
            'incorrect_type': 'El ID del usuario debe ser un número entero.',
        }
    )
    order_prefix = 'PO'
    
    class Meta:
        model = PurchaseOrder
        fields = BaseOrderSerializer.common_fields + ['processing_payment_at','paid_at','supplier_user']
        read_only_fields = BaseOrderSerializer.common_read_only
    
    def validate_supplier_user(self, value):
        """Validación personalizada del supplier_user"""
        # value ya es un objeto User
        if value is None:
            return value  # Permitido ser null
        
        if not value.is_active:
            raise serializers.ValidationError({
                'supplier_user': f"El usuario '{value.username}' no está activo."
            })
        
        return value
    
    def validate(self, data):
        """SIMPLIFICADO: Solo validaciones de negocio, NO permisos"""
        data = super().validate(data)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # SIMPLE: Solo asignar supplier_user si no se especificó
            if 'supplier_user' not in data or data['supplier_user'] is None:
                data['supplier_user'] = request.user    
        
        return data
    
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
                user=user,  # Admin que crea
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
        
    def to_representation(self, instance):
        if isinstance(instance, dict):
            return instance
        return super().to_representation(instance)
        
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
    # Campo opcional para especificar tokens específicos
    token_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="Lista opcional de IDs de tokens específicos a vender"
    )
    order_prefix = 'SO'
    
    class Meta:
        model = SalesOrder
        fields = BaseOrderSerializer.common_fields + ['seller_user', 'reserved_tokens_info' , 'token_ids']
        read_only_fields = BaseOrderSerializer.common_read_only
    
    def validate(self, data):
        """Solo validaciones de negocio, NO permisos"""
        data = super().validate(data)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Solo asignar seller_user si no se especificó
            if 'seller_user' not in data or data['seller_user'] is None:
                data['seller_user'] = request.user
    
        return data
    
    def create(self, validated_data):
        """Crear orden de venta usando el servicio de seguridad"""
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            raise serializers.ValidationError("No se pudo determinar el usuario")
        
        validated_data = self._generate_order_number(validated_data)
        
        try:
            # El servicio necesita saber quién crea (admin) y para quién (seller_user)
            result = self.order_creation_service.create_sales_order(
                user=user,  # Usuario que crea (admin/seller_user)
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


# ================================================
# SERIALIZERS DE CANCELACIÓN Y TRANSACCIONES
# ================================================
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
        
    def validate(self, attrs):
        """Validación básica antes de delegar en el servicio"""
        request = self.context.get('request')
        fund_id = self.context.get('fund_id')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Usuario no autenticado")
        
        if not fund_id:
            raise serializers.ValidationError({
                'fund': "El campo 'fund_id' es obligatorio en la URL para cancelar una orden."
            })
        
        if not Fund.objects.filter(id=fund_id).exists():
            raise serializers.ValidationError({
                'fund': f"El fideicomiso con ID {fund_id} no existe."
            })
        
        return attrs
    
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
    
    