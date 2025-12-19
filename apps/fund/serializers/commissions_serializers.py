"""
Serializers para Cesiones/Transfers - Versión Beta
"""

from rest_framework import serializers
from apps.fund.models.commissions import Transfers


class TransferSerializer(serializers.ModelSerializer):
    """Serializer básico para cesiones"""
    
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Transfers
        fields = [
            'id', 'fund', 'fund_name', 'effective_date',
            'class_transfer', 'settlor', 'assignee', 'assigned_amount',
            'doc_transfer', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TransferCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear cesión"""
    
    class Meta:
        model = Transfers
        fields = [
            'fund', 'effective_date', 'class_transfer',
            'settlor', 'assignee', 'assigned_amount', 'doc_transfer',
            # Datos del cedente
            'actor_settlor', 'nit_settlor', 'type_doc_settlor', 'id_doc_settlor',
            # Datos del cesionario
            'actor_assignee', 'nit_assignee', 'type_doc_assignee', 'id_doc_assignee',
        ]
    
    def validate_assigned_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a cero")
        return value


class TransferListSerializer(serializers.ModelSerializer):
    """Serializer para listado de cesiones"""
    
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    
    class Meta:
        model = Transfers
        fields = [
            'id', 'fund', 'fund_name', 'effective_date',
            'settlor', 'assignee', 'assigned_amount'
        ]