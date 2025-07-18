from rest_framework import serializers
from apps.fund.models import FundToken

class TokenCounterUserSerializer(serializers.Serializer):
    """
    Serializer para contar los tokens de un usuario en un fondo específico.
    El user_id se obtiene automáticamente del usuario autenticado.
    """
    fund_id = serializers.IntegerField(required=True)
    user_id = serializers.IntegerField()
    token_count = serializers.IntegerField(read_only=True)

    def validate_fund_id(self, value):
        """Validar que fund_id sea un entero positivo"""
        if not isinstance(value, int) or value <= 0:
            raise serializers.ValidationError("El ID de fondo debe ser un entero positivo.")
        return value

    def get_token_count(self, obj):
        """
        Cuenta los tokens de un usuario en un fondo específico
        
        Args:
            obj (dict): Diccionario con user_id y fund_id
            
        Returns:
            int: Número de tokens que posee el usuario
        """
        user_id = obj.get('user_id')
        fund_id = obj.get('fund_id')
        
        if not user_id or not fund_id:
            return 0
        
        tokens_available = FundToken.objects.filter(
            owner_user=user_id, 
            fund=fund_id, 
            status=True, 
            reserved_for_sale=False
        ).count()
        
        tokens_total = FundToken.objects.filter(
            owner_user=user_id, 
            fund=fund_id, 
            status=True
        ).count()
        
        tokens_reserved = tokens_total - tokens_available
        
        # Contar tokens activos del usuario en el fondo específico
        return {
            'tokens_available': tokens_available,
            'tokens_reserved': tokens_reserved,
            'tokens_total': tokens_total
        }

class AISerializer(serializers.Serializer):
    prompt = serializers.CharField(required=True, allow_blank=False)
    