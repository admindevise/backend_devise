from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
import uuid

from apps.trading.models import (
    PurchaseOrder,
    SalesOrder,
    Transaction,
    OrderBook
)
from apps.fund.models import Fund
from apps.user.models import User
from apps.user.serializers.basic_info_user_serializer import UserBasicInfoSerializer

class BaseOrderSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    paid_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    completed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    cancelled_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    
    # Campos comunes para ambos serializadores
    common_fields = [
        'id', 'order_number', 'units', 'expiration_date', 'margin',
        'status', 'fund', 'fund_name', 'created_by', 'approved_at',
        'paid_at', 'completed_at', 'cancelled_at', 'created_at',
        'min_acceptable_price', 'max_acceptable_price', 'days_until_expiration', 'price_per_unit', 'total_amount',
    ]
    
    common_read_only = ['order_number', 'total_amount', 'approved_at', 'paid_at', 'completed_at', 'cancelled_at']
    
    order_prefix = 'OR'
    
    def validate_units(self, value):
        """
        Validate that units is a positive integer.
        """
        if value <= 0:
            raise serializers.ValidationError("Las unidades deben ser un número entero positivo.")
        return value
    
    def validate_expiration_date(self, value):
        """
        Validate that expiration_date is in the future.
        """
        if value <= timezone.now().date():
            raise serializers.ValidationError("La fecha de expiración debe ser en el futuro.")
        return value
    
    def validate_margin(self, value):
        """
        Validate that margin is a positive number.
        """
        if value < 0:
            raise serializers.ValidationError("El margen debe ser un número positivo.")
        if value > 100:
            raise serializers.ValidationError("El margen no puede ser mayor al 100%.")
        return value
    
    def validate_status(self, value):
        """
        Validate that status is a valid option.
        """
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


class SalesOrderSerializer(BaseOrderSerializer):
    seller_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    order_prefix = 'SO'
    class Meta:
        model = SalesOrder
        fields = BaseOrderSerializer.common_fields + ['seller_user']
        read_only_fields = BaseOrderSerializer.common_read_only


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions between purchase and sales orders"""
    #buyer_details = UserBasicInfoSerializer(source='buyer', read_only=True)
    #seller_details = UserBasicInfoSerializer(source='seller', read_only=True)
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'purchase_order',
            'sales_order',
            'buyer',
            #'buyer_details',
            'seller',
            #'seller_details',
            'fund',
            'fund_name',
            'units',
            'price_per_unit',
            'total_amount',
            'created_at'
        ]
        read_only_fields = ['transaction_date', 'created_at', 'updated_at']

    @transaction.atomic
    def create(self, validated_data):
        transaction = super().create(validated_data)
        
        # Actualizar estado de órdenes relacionadas
        purchase_order = transaction.purchase_order
        sales_order = transaction.sales_order
        
        # Actualizar estados según la lógica de negocio
        purchase_order.update_status('COMPLETED')
        sales_order.update_status('COMPLETED')
        
        return transaction

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