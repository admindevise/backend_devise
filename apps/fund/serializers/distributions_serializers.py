from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from apps.fund.models.core import Fund
from apps.fund.models.distributions import DistributionPeriod, InvestmentDistributionRecord
from apps.fund.services.distributions.distributions_service import DistributionService, DistributionServiceError


class CreateDistributionPeriodSerializer(serializers.Serializer):
    """
    Serializer para crear períodos de distribución.
    Sigue el patrón de los serializers de investment.
    """
    
    # Campos requeridos
    total_amount = serializers.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        required=True,
        help_text="Monto total a distribuir"
    )
    
    distribution_type = serializers.ChoiceField(
        choices=DistributionPeriod.DistributionType.choices,
        required=True,
        help_text="Tipo de distribución (monthly, quarterly, etc.)"
    )
    
    period_year = serializers.IntegerField(
        required=True,
        min_value=2020,
        max_value=2050,
        help_text="Año del período de distribución"
    )
    
    fund = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    # Campos opcionales
    period_month = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        allow_null=True,
        help_text="Mes del período (requerido para distribuciones mensuales)"
    )
    
    period_quarter = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=4,
        allow_null=True,
        help_text="Trimestre del período (requerido para distribuciones trimestrales)"
    )
    
    payment_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Fecha de pago programada (por defecto hoy)"
    )
    
    record_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Fecha de registro para snapshot de tokens (por defecto hoy)"
    )
    
    distribution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Notas adicionales sobre la distribución"
    )
    
    # Validaciones de campo individual
    def validate_total_amount(self, value):
        """Validar que el monto sea positivo"""
        if value <= 0:
            raise serializers.ValidationError("El monto total debe ser mayor a cero")
        return value
    
    def validate_fund(self, value):
        """Validar que el fondo existe y está activo"""
        try:
            fund = Fund.objects.get(id=value)
            if not fund.status:
                raise serializers.ValidationError("El fondo no está activo")
            return fund
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe")
    
    def validate_payment_date(self, value):
        """Validar que la fecha de pago no sea en el pasado"""
        if value and value < timezone.now().date():
            raise serializers.ValidationError("La fecha de pago no puede ser en el pasado")
        return value
    
    def validate_record_date(self, value):
        """Validar que la fecha de registro no sea futura"""
        if value and value > timezone.now().date():
            raise serializers.ValidationError("La fecha de registro no puede ser futura")
        return value
    
    # Validaciones a nivel de objeto
    def validate(self, attrs):
        """Validaciones que requieren múltiples campos"""
        distribution_type = attrs.get('distribution_type')
        period_month = attrs.get('period_month')
        period_quarter = attrs.get('period_quarter')
        
        # Validar mes para distribuciones mensuales
        if distribution_type == DistributionPeriod.DistributionType.MONTHLY:
            if not period_month:
                raise serializers.ValidationError({
                    'period_month': 'Las distribuciones mensuales requieren especificar el mes'
                })
        elif period_month:
            # Si se especifica mes pero no es distribución mensual, limpiar el campo
            attrs['period_month'] = None
        
        # Validar trimestre para distribuciones trimestrales
        if distribution_type == DistributionPeriod.DistributionType.QUARTERLY:
            if not period_quarter:
                raise serializers.ValidationError({
                    'period_quarter': 'Las distribuciones trimestrales requieren especificar el trimestre'
                })
        elif period_quarter:
            # Si se especifica trimestre pero no es distribución trimestral, limpiar el campo
            attrs['period_quarter'] = None
        
        # Validar que las fechas sean coherentes
        payment_date = attrs.get('payment_date')
        record_date = attrs.get('record_date')
        
        if payment_date and record_date and payment_date < record_date:
            raise serializers.ValidationError({
                'payment_date': 'La fecha de pago no puede ser anterior a la fecha de registro'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Crear período de distribución usando el servicio"""
        request = self.context.get('request')
        
        try:
            # Extraer el fondo de los datos validados
            fund = validated_data.pop('fund')
            
            # Crear servicio de distribuciones
            distribution_service = DistributionService(fund)
            
            # Crear período de distribución
            distribution_period = distribution_service.create_distribution_period(
                total_amount=validated_data['total_amount'],
                distribution_type=validated_data['distribution_type'],
                period_year=validated_data['period_year'],
                period_month=validated_data.get('period_month'),
                period_quarter=validated_data.get('period_quarter'),
                payment_date=validated_data.get('payment_date'),
                record_date=validated_data.get('record_date'),
                distribution_notes=validated_data.get('distribution_notes', ''),
                created_by=request.user if request else None,
                request=request
            )
            
            return distribution_period
            
        except DistributionServiceError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error interno: {str(e)}")
    
    def to_representation(self, instance):
        """Representación de respuesta tras la creación"""
        return {
            'id': instance.id,
            'fund_id': instance.fund.id,
            'fund_name': instance.fund.name,
            'distribution_type': instance.distribution_type,
            'distribution_type_display': instance.get_distribution_type_display(),
            'period_year': instance.period_year,
            'period_month': instance.period_month,
            'period_quarter': instance.period_quarter,
            'period_display': instance.period_display,
            'total_distribution_amount': str(instance.total_distribution_amount),
            'total_tokens_outstanding': instance.total_tokens_outstanding,
            'distribution_per_token': str(instance.distribution_per_token),
            'record_date': instance.record_date.strftime("%Y-%m-%d"),
            'payment_date': instance.payment_date.strftime("%Y-%m-%d"),
            'status': instance.status,
            'status_display': instance.get_status_display(),
            'created_by': instance.created_by.email if instance.created_by else None,
            'created_at': instance.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'distribution_notes': instance.distribution_notes,
            'message': f'Período de distribución creado exitosamente para {instance.period_display}'
        }


class DistributionPeriodPreviewSerializer(serializers.Serializer):
    """
    Serializer para vista previa de distribución sin crearla
    """
    
    total_amount = serializers.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        required=True
    )
    
    fund = serializers.IntegerField(required=True)
    
    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a cero")
        return value
    
    def validate_fund(self, value):
        try:
            return Fund.objects.get(id=value)
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe")
    
    def create(self, validated_data):
        """Calcular vista previa usando el servicio"""
        fund = validated_data['fund']
        total_amount = validated_data['total_amount']
        
        try:
            distribution_service = DistributionService(fund)
            preview = distribution_service.calculate_distribution_preview(total_amount)
            
            if 'error' in preview:
                raise serializers.ValidationError(preview['error'])
            
            return preview
            
        except Exception as e:
            raise serializers.ValidationError(f"Error calculando vista previa: {str(e)}")


class DistributionPeriodListSerializer(serializers.ModelSerializer):
    """
    Serializer para listado de períodos de distribución
    """
    
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    record_date = serializers.DateField(format="%Y-%m-%d", read_only=True)
    payment_date = serializers.DateField(format="%Y-%m-%d", read_only=True)
    approved_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    processed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    # Campos calculados
    period_display = serializers.ReadOnlyField()
    distribution_type_display = serializers.CharField(source='get_distribution_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Información del creador
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    approved_by_email = serializers.CharField(source='approved_by.email', read_only=True)
    
    class Meta:
        model = DistributionPeriod
        fields = [
            'id', 'distribution_type', 'distribution_type_display',
            'period_year', 'period_month', 'period_quarter', 'period_display',
            'total_distribution_amount', 'total_tokens_outstanding', 'distribution_per_token',
            'record_date', 'payment_date', 'status', 'status_display',
            'created_at', 'approved_at', 'processed_at',
            'created_by_email', 'approved_by_email',
            'distribution_notes'
        ]
        read_only_fields = fields


class DistributionPeriodDetailSerializer(DistributionPeriodListSerializer):
    """
    Serializer detallado para un período de distribución específico
    """
    
    # Información adicional del fondo
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    fund_id = serializers.IntegerField(source='fund.id', read_only=True)
    
    # Metadatos de cálculo
    calculation_metadata = serializers.JSONField(read_only=True)
    
    # Estadísticas de registros de distribución
    total_investment_records = serializers.SerializerMethodField()
    total_users_affected = serializers.SerializerMethodField()
    
    class Meta(DistributionPeriodListSerializer.Meta):
        fields = DistributionPeriodListSerializer.Meta.fields + [
            'fund_id', 'fund_name', 'calculation_metadata',
            'total_investment_records', 'total_users_affected'
        ]
    
    def get_total_investment_records(self, obj):
        """Obtener total de registros de distribución creados"""
        return obj.investment_records.count()
    
    def get_total_users_affected(self, obj):
        """Obtener total de usuarios únicos afectados"""
        return obj.investment_records.values('investment__application__user').distinct().count()


# ====================================
# DISTRIBUTION RECORD BY INVESTMENT
# ====================================
class CreateDistributionRecordsSerializer(serializers.Serializer):
    """
    Serializer para crear registros de distribución COP para todos los inversores.
    """
    
    distribution_period_id = serializers.IntegerField(
        required=True,
        help_text="ID del período de distribución"
    )
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Notas adicionales sobre la creación de registros"
    )
    
    def validate_distribution_period_id(self, value):
        """Validar que el período de distribución existe y está en estado válido"""
        try:
            distribution_period = DistributionPeriod.objects.get(id=value)
            
            # Validar que esté en estado válido para crear registros
            if distribution_period.status not in [
                DistributionPeriod.DistributionStatus.DRAFT,
                DistributionPeriod.DistributionStatus.APPROVED
            ]:
                raise serializers.ValidationError(
                    f"El período debe estar en estado DRAFT o APPROVED, actual: {distribution_period.get_status_display()}"
                )
            
            # Verificar que no existan registros ya creados
            if distribution_period.investment_records.exists():
                raise serializers.ValidationError(
                    "Ya existen registros de distribución para este período"
                )
            
            return distribution_period
            
        except DistributionPeriod.DoesNotExist:
            raise serializers.ValidationError(f"Período de distribución con ID {value} no existe")
    
    def create(self, validated_data):
        """Crear registros de distribución usando el servicio"""
        request = self.context.get('request')
        distribution_period = validated_data['distribution_period_id']
        
        try:
            # Crear servicio de distribuciones
            distribution_service = DistributionService(distribution_period.fund)
            
            # Crear registros de distribución
            result = distribution_service.create_distribution_records(
                distribution_period=distribution_period,
                created_by=request.user if request else None,
                request=request
            )
            
            return result
            
        except DistributionServiceError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error interno: {str(e)}")
    
    def to_representation(self, instance):
        """Representación de respuesta tras la creación"""
        return {
            'success': instance['success'],
            'distribution_period_id': instance['distribution_period_id'],
            'total_records_created': instance['total_records_created'],
            'records_summary': instance['records_summary'],
            'fund_info': instance['fund_info'],
            'summary': instance['summary'],
            'message': f"Se crearon {instance['total_records_created']} registros de distribución exitosamente"
        }        
        
class InvestmentDistributionRecordSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)             
    class Meta:
        model = InvestmentDistributionRecord
        fields = '__all__'
        
        