from rest_framework import serializers
from apps.fund.models.tokens import FundToken
from apps.fund.models.membership import InvestorContract

from apps.user.serializers.basic_info_user_serializer import UserShortInfoSerializer

class TrustMembersSerializer(serializers.ModelSerializer):
    contract_signed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    user = UserShortInfoSerializer()
    
    class Meta:
        model = InvestorContract
        fields = ['user', 'contract_signed_at', 'created_at', 'fund']

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
    city_name = serializers.CharField(required=True, allow_blank=False)
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    asset_type = serializers.CharField(required=True, allow_blank=False)
    square_footage = serializers.IntegerField(required=True)
    year_built = serializers.IntegerField(required=True)
    occupancy_rate = serializers.IntegerField(required=True)
    net_operating_income = serializers.IntegerField(required=True)
    
    def validate_latitude(self, value):
        """Validar que la latitud esté en el rango de Colombia"""
        if not (-4.5 <= value <= 13.5):
            raise serializers.ValidationError("La latitud debe estar en el rango válido para Colombia (-4.5 a 13.5)")
        return value
    
    def validate_longitude(self, value):
        """Validar que la longitud esté en el rango de Colombia"""
        if not (-82.0 <= value <= -66.0):
            raise serializers.ValidationError("La longitud debe estar en el rango válido para Colombia (-82.0 a -66.0)")
        return value
    
    def validate_occupancy_rate(self, value):
        """Validar que la tasa de ocupación esté entre 0 y 100"""
        if not (0 <= value <= 100):
            raise serializers.ValidationError("La tasa de ocupación debe estar entre 0 y 100")
        return value
    
    def validate_year_built(self, value):
        """Validar que el año de construcción sea razonable"""
        if not (1800 <= value <= 2025):
            raise serializers.ValidationError("El año de construcción debe estar entre 1800 y 2025")
        return value
    
    def validate_square_footage(self, value):
        """Validar que el área sea positiva"""
        if value <= 0:
            raise serializers.ValidationError("El área debe ser mayor a 0")
        return value
    
    def validate_net_operating_income(self, value):
        """Validar que el NOI sea positivo"""
        if value < 0:
            raise serializers.ValidationError("El ingreso operativo neto debe ser mayor o igual a 0")
        return value

class CustomerSupportSerializer(serializers.Serializer):
    user_type = serializers.ChoiceField(
        choices=['investor', 'admin', 'fund_manager'],
        default='investor'
    )
    query_type = serializers.ChoiceField(
        choices=['general', 'portfolio', 'transactions', 'technical', 'account'],
        required=True
    )
    context = serializers.CharField(required=True, allow_blank=False)
    
    # Datos opcionales del usuario para enriquecer el contexto
    user_data = serializers.JSONField(required=False, default=dict)
    
    def validate_context(self, value):
        """Validar que el contexto tenga suficiente información"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("El contexto debe tener al menos 10 caracteres")
        return value
    

class InvestmentTrendSerializer(serializers.Serializer):
    """
    Serializer para mostrar tendencias de inversiones con diferentes períodos de tiempo.
    Permite analizar el comportamiento de las inversiones en distintos rangos temporales.
    """
    TIME_PERIOD_CHOICES = [
        ('1M', '1 Mes'),
        ('3M', '3 Meses'),
        ('6M', '6 Meses'),
        ('1Y', '1 Año'),
    ]
    
    fund_id = serializers.IntegerField(required=False, allow_null=True)
    time_period = serializers.ChoiceField(
        choices=TIME_PERIOD_CHOICES,
        default='1M',
        help_text="Período de tiempo para analizar la tendencia"
    )
    
    # Datos de salida (read_only)
    total_investments = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    average_investment = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    growth_percentage = serializers.FloatField(read_only=True)
    period_data = serializers.ListField(
        child=serializers.DictField(),
        read_only=True,
        help_text="Datos detallados por período (diarios, semanales o mensuales)"
    )
    
    def validate_fund_id(self, value):
        """Validar que fund_id sea un entero positivo si se proporciona"""
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise serializers.ValidationError("El ID de fondo debe ser un entero positivo.")
        return value
    
    def to_representation(self, instance):
        """
        Personalizar la representación de los datos de tendencia
        """
        representation = super().to_representation(instance)
        
        # Agregar información adicional sobre el período
        time_period = representation.get('time_period')
        period_info = {
            '1M': {'days': 30, 'label': 'Último mes'},
            '3M': {'days': 90, 'label': 'Últimos 3 meses'},
            '6M': {'days': 180, 'label': 'Últimos 6 meses'},
            '1Y': {'days': 365, 'label': 'Último año'},
        }
        
        representation['period_info'] = period_info.get(time_period, {})
        
        return representation