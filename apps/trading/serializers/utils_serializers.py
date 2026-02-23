from rest_framework import serializers
from apps.utils.serializers.base_serializer import BaseSerializer

class UnifiedOrderSerializer(BaseSerializer):
    order_number = serializers.CharField()
    order_type = serializers.CharField()
    origin = serializers.CharField()
    user = serializers.IntegerField()
    created_by = serializers.IntegerField()
    fund = serializers.IntegerField()
    units = serializers.IntegerField()
    amount_total = serializers.SerializerMethodField()
    price_per_unit = serializers.DecimalField(max_digits=20, decimal_places=2)
    status = serializers.CharField()
    
    def get_amount_total(self, obj):
        if isinstance(obj, dict):
            price_per_unit = obj.get('price_per_unit')
            units = obj.get('units')
        else:
            price_per_unit = getattr(obj, 'price_per_unit', None)
            units = getattr(obj, 'units', None)

        if price_per_unit is None or units is None:
            return None
        return str(price_per_unit * units)
    
    @staticmethod
    def from_purchase(order):
        return {
            'order_number': order.order_number,
            'order_type': 'purchase',
            'origin': order.origin,
            'user': order.supplier_user_id,
            'created_by': order.created_by_id,
            'fund': order.fund_id,
            'units': order.units,
            'price_per_unit': order.price_per_unit,
            'status': order.status,
            'created_at': order.created_at
        }

    @staticmethod
    def from_sales(order):
        return {
            'order_number': order.order_number,
            'order_type': 'sales',
            'origin': order.origin,
            'user': order.seller_user_id,
            'created_by': order.created_by_id,
            'fund': order.fund_id,
            'units': order.units,
            'price_per_unit': order.price_per_unit,
            'status': order.status,
            'created_at': order.created_at
        }