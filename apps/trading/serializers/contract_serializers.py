from rest_framework import serializers
from django.utils import timezone

from apps.trading.models import OrderContract

class OrderContractSerializer(serializers.ModelSerializer):
    """Serializer básico para contratos"""
    
    purchase_order_number = serializers.CharField(source='purchase_order.order_number', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.order_number', read_only=True)
    buyer_email = serializers.CharField(source='purchase_order.supplier_user.email', read_only=True)
    seller_email = serializers.CharField(source='sales_order.seller_user.email', read_only=True)
    
    class Meta:
        model = OrderContract
        fields = [
            'id', 'purchase_order', 'sales_order', 'status', 
            'approved_by', 'approved_at', 'created_at',
            'purchase_order_number', 'sales_order_number', 
            'buyer_email', 'seller_email'
        ]
        read_only_fields = ['approved_by', 'approved_at']

class ContractApprovalSerializer(serializers.Serializer):
    """Serializer para aprobación/rechazo de contratos"""
    
    status = serializers.ChoiceField(
        choices=['APPROVED', 'REJECTED'],
        help_text="APPROVED para aprobar, REJECTED para rechazar"
    )