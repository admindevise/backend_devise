from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.validators import RegexValidator
from decimal import Decimal
from django.utils import timezone

from apps.fund.models import TokenTransaction
from apps.fund.services.application_service import FundApplicationService

class TokenTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer para manejar las transacciones de tokens
    """

    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    from_user = serializers.PrimaryKeyRelatedField(read_only=True)
    to_user = serializers.PrimaryKeyRelatedField(read_only=True)

    amount = serializers.IntegerField()

    class Meta:
        model = TokenTransaction
        fields = [
            'id', 'fund', 'from_user', 'to_user', 'transaction_type',
            'price_per_unit', 'amount', 'status', 'description',
            'kaleido_transaction_id', 'metadata', 'created_at', 
        ]
        read_only_fields = ['from_user', 'to_user', 'created_at']

    # ========================================
    # VALIDACIONES BÁSICAS (Solo formato/tipo)
    # ========================================

    def validate_amount(self, value):
        """
        Validación básica de formato.
        Las validaciones de negocio (montos mínimos/máximos) están en el servicio.
        """
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value