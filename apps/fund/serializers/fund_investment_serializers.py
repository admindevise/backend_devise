from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.validators import RegexValidator
from decimal import Decimal
from django.utils import timezone

from apps.fund.models import Fund, FundInvestment, FundApplication
from apps.fund.services.application_service import FundApplicationService

class FundApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer para manejar las aplicaciones a fondos
    """
    
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reviewed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    fund_id = serializers.IntegerField(write_only=True, required=True)
    applicant = serializers.PrimaryKeyRelatedField(read_only=True)
    reviewed_by = serializers.PrimaryKeyRelatedField(read_only=True)
    
    requested_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, 
        validators=[RegexValidator(
            regex=r'^\d+(\.\d{1,2})?$',
            message="Request amount must be a valid decimal number."
        )]
    )
    
    class Meta:
        model = FundApplication
        fields = [
            'id', 'fund_id', 'applicant', 'reviewed_by', 'requested_amount',
            'status', 'created_at', 'updated_at', 'reviewed_at', 
            'applicant_notes', 'reviewed_at', 'rejection_reason'
                  ]
        read_only_fields = ['applicant', 'reviewed_by', 'created_at']

    # ========================================
    # VALIDACIONES BÁSICAS (Solo formato/tipo)
    # ========================================
    
    def validate_fund_id(self, value):
        """
        Validación básica de formato. 
        Las validaciones de negocio están en el servicio.
        """
        if not isinstance(value, int) or value <= 0:
            raise ValidationError("Fund ID must be a positive integer.")
        return value
    
    def validate_requested_amount(self, value):
        """
        Validación básica de formato.
        Las validaciones de negocio (montos mínimos/máximos) están en el servicio.
        """
        if not isinstance(value, Decimal):
            raise serializers.ValidationError("Request amount must be a valid decimal.")
        if value <= 0:
            raise ValidationError("Request amount must be greater than zero.")
        return value
    
    def validate_applicant_notes(self, value):
        """Validación básica de longitud"""
        if value and len(value) > 1000:  # Ejemplo de límite
            raise ValidationError("Applicant notes cannot exceed 1000 characters.")
        return value
    
    # ========================================
    # DELEGACIÓN AL SERVICIO
    # ========================================
    
    def create(self, validated_data):
        """
        Delegar creación al servicio de dominio.
        El serializer solo extrae y valida datos de entrada.
        """
        # Extraer datos validados
        fund_id = validated_data['fund_id']
        requested_amount = validated_data['requested_amount']
        notes = validated_data.get('applicant_notes', '')
        user = self.context['request'].user
        request = self.context.get('request', None)
        
        # Delegar al servicio (que maneja toda la lógica de negocio)
        application = FundApplicationService.create_application(
            fund_id=fund_id,
            user=user,
            requested_amount=requested_amount,
            notes=notes,
            request=request
        )
        
        return application
    
# ===================================================
# SERIALIZERS AUXILIARES PARA OPERACIONES ESPECÍFICAS
# ===================================================
    
class FundApplicationReviewSerializer(serializers.Serializer):
    """
    Serializer específico para revisión de aplicaciones por parte del staff.
    No hereda de ModelSerializer porque no crea/actualiza directamente.
    """
    
    review_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    class Meta:
        fields = ['review_notes']


class FundApplicationRejectionSerializer(FundApplicationReviewSerializer):
    """
    Serializer específico para rechazar aplicaciones.
    Extiende el de revisión agregando rejection_reason obligatorio.
    """
    
    rejection_reason = serializers.CharField(max_length=500, required=True)
    
    class Meta:
        fields = ['application_id', 'rejection_reason', 'review_notes']
    
    def validate_rejection_reason(self, value):
        """Validar que se proporcione una razón"""
        if not value or not value.strip():
            raise ValidationError("Rejection reason is required.")
        return value.strip()
    
    
class FundApplicationStatusSerializer(serializers.ModelSerializer):
    """
    Serializer de solo lectura para consultar el estado de aplicaciones.
    Incluye información útil para el frontend.
    """
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    applicant_email = serializers.CharField(source='applicant.email', read_only=True)
    reviewer_email = serializers.CharField(source='reviewed_by.email', read_only=True)
    
    # Campos calculados
    can_be_approved = serializers.SerializerMethodField()
    can_be_rejected = serializers.SerializerMethodField()
    has_investment = serializers.SerializerMethodField()
    days_since_application = serializers.SerializerMethodField()
    
    class Meta:
        model = FundApplication
        fields = [
            'id', 'fund_name', 'applicant_email', 'reviewer_email',
            'requested_amount', 'status', 'created_at', 'reviewed_at',
            'applicant_notes', 'review_notes', 'rejection_reason',
            'can_be_approved', 'can_be_rejected', 'has_investment',
            'days_since_application'
        ]
        read_only_fields = ('__all__',)  # Solo lectura
    
    def get_can_be_approved(self, obj):
        """¿Se puede aprobar esta aplicación?"""
        return obj.status in [
            FundApplication.ApplicationStatus.PENDING,
            FundApplication.ApplicationStatus.UNDER_REVIEW
        ]
    
    def get_can_be_rejected(self, obj):
        """¿Se puede rechazar esta aplicación?"""
        return obj.status not in [
            FundApplication.ApplicationStatus.APPROVED,
            FundApplication.ApplicationStatus.REJECTED
        ]
    
    def get_has_investment(self, obj):
        """¿Tiene inversión asociada?"""
        return hasattr(obj, 'investment')
    
    def get_days_since_application(self, obj):
        """Días desde la aplicación"""
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        return delta.days


class FundInvestmentSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    investor = serializers.PrimaryKeyRelatedField(read_only=True)
    
    invested_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, 
        validators=[RegexValidator(
            regex=r'^\d+(\.\d{1,2})?$',
            message="Invested amount must be a valid decimal number."
        )]
    )
    
    class Meta:
        model = FundInvestment
        fields = [
            'id', 'fund', 'application', 'investor', 
            'status', 'invested_amount',
            'created_at', 'updated_at',
            'cancellation_reason'
            ]
        read_only_fields = ['investor', 'created_at']
    
    def validate_fund_id(self, value):
        try:
            fund = Fund.objects.get(id=value)
        except Fund.DoesNotExist:
            raise ValidationError(f"Fund with ID {value} does not exist.")
        if fund.status != 'active':
            raise ValidationError("Cannot invest in a fund that is not active.")
        return value
    
    def validate_invested_amount(self, value):
        if value <= 0:
            raise ValidationError("Invested amount must be greater than zero.")
        return value
    
    def create(self, validated_data):
        validated_data['investor'] = self.context['request'].user        
        return super().create(validated_data)