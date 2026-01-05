"""
Serializers para Comisiones y Cesiones/Transfers
"""

from rest_framework import serializers
from apps.fund.models.commissions import Commissions


# ============================================================================
# COMMISSIONS SERIALIZERS
# ============================================================================

class CommissionResponseSerializer(serializers.ModelSerializer):
    """Serializer de respuesta para comisiones"""
    
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Commissions
        fields = [
            'id', 'fund', 'fund_name', 'contract_num',
            'name', 'description', 'amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CommissionCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear comisión"""
    
    class Meta:
        model = Commissions
        fields = [
            'fund', 'contract_num', 'name', 'description', 'amount'
        ]
    
    def validate_contract_num(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El número de contrato es requerido")
        if len(value) > 10:
            raise serializers.ValidationError("El número de contrato no puede exceder 10 caracteres")
        return value.strip()
    
    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El nombre es requerido")
        if len(value) > 50:
            raise serializers.ValidationError("El nombre no puede exceder 50 caracteres")
        return value.strip()
    
    def validate_description(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("La descripción es requerida")
        if len(value) > 256:
            raise serializers.ValidationError("La descripción no puede exceder 256 caracteres")
        return value.strip()


class CommissionListSerializer(serializers.ModelSerializer):
    """Serializer para listado de comisiones"""
    
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    
    class Meta:
        model = Commissions
        fields = [
            'id', 'fund', 'fund_name', 'contract_num',
            'name', 'amount'
        ]