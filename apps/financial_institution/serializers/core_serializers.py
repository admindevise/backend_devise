from rest_framework import serializers
from apps.financial_institution.models import FinancialInstitution, FinancialInstitutionApproval, FinancialInstitutionApplication
from apps.financial_institution.service.fi_application_service import FinancialInstitutionApplicationService

class FinancialInstitutionSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = FinancialInstitution
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'api_key', 'webhook_url', 'last_activity'
            ]
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)
    
class FinancialInstitutionApplicationSerializer(serializers.ModelSerializer):
    requested_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reviewed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    requested_investor_profile = serializers.ChoiceField(
        choices=FinancialInstitutionApplication.InvestorProfile.choices,
        required=True,
        help_text="Perfil del inversor"
    )
    
    class Meta:
        model = FinancialInstitutionApplication
        fields = [
            'id', 'financial_institution', 'requested_investor_profile', 
            'requested_investment_amount', 'application_notes', 'kyc_documents',
            'status', 'requested_at','rejection_category', 'rejection_reason', 'can_reapply_after', 'user', 'reviewed_by', 'reviewed_at'
        ]
        read_only_fields = ['id', 'requested_at', 'user', 'status']

    def validate_financial_institution(self, value):
        """Valida que la institución financiera esté activa"""
        if value.status != FinancialInstitution.Status.ACTIVE:
            raise serializers.ValidationError("La institución financiera no está activa.")
        return value
    
    def validate(self, data):
        """Validaciones a nivel de objeto"""
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            
            # Validar que el usuario esté activo
            if not user.is_active:
                raise serializers.ValidationError(
                    "No se puede crear la solicitud. El usuario no está activo."
                )
        
        return data
    
    def create(self, validated_data):
        """Crear solicitud usando el servicio"""
        request = self.context.get('request')
        
        if not request or not request.user:
            raise serializers.ValidationError("Usuario no autenticado")
        
        user = request.user
        
        # Capturar metadatos del request
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            # Usar el servicio para crear la aplicación
            application = FinancialInstitutionApplicationService.submit_application(
                user=user,
                financial_institution=validated_data['financial_institution'],
                requested_investor_profile=validated_data['requested_investor_profile'],
                requested_investment_amount=validated_data.get('requested_investment_amount'),
                application_notes=validated_data.get('application_notes', ''),
                kyc_documents=validated_data.get('kyc_documents', {})
            )
            
            # Agregar metadatos del request
            application.ip_address = ip
            application.user_agent = user_agent
            application.save()
            
            return application
            
        except ValueError as e:
            raise serializers.ValidationError(str(e))

class FinancialInstitutionApprovalSerializer(serializers.ModelSerializer):
    """Serializer específico para aprobaciones"""
    
    investor_profile = serializers.ChoiceField(
        choices=FinancialInstitutionApplication.InvestorProfile.choices,
        required=True,
        help_text="Perfil del inversor aprobado"
    )
    max_investment_amount = serializers.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        required=False,
        help_text="Monto máximo de inversión permitido"
    )
    allowed_fund_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Tipos de fondos permitidos"
    )
    approval_notes = serializers.CharField(
        required=False,
        help_text="Notas adicionales sobre la aprobación"
    )
    conditions = serializers.CharField(
        required=False,
        help_text="Condiciones especiales de la aprobación"
    )
    expiry_date = serializers.DateField(
        required=False,
        help_text="Fecha de expiración de la aprobación"
    )
    
    class Meta:
        model = FinancialInstitutionApproval
        fields = [
            'investor_profile', 'max_investment_amount', 'allowed_fund_types',
            'approval_notes', 'conditions', 'expiry_date'
        ]
    
    def create(self, validated_data):
        application = self.context['application']
        request = self.context['request']
        
        try:
            application, approval = FinancialInstitutionApplicationService.approve_application(
                application_id=application.id,
                approved_by=request.user,
                **validated_data
            )
            return approval
        except ValueError as e:
            raise serializers.ValidationError(str(e))

class FinancialInstitutionRejectionSerializer(serializers.Serializer):
    """Serializer específico para rechazos"""
    
    rejection_reason = serializers.CharField(
        required=True,  # Siempre requerido para rechazos
        help_text="Razón del rechazo"
    )
    review_notes = serializers.CharField(
        required=False,
        help_text="Notas adicionales de la revisión"
    )
    rejection_category = serializers.ChoiceField(
        choices=FinancialInstitutionApplication.RejectionCategory.choices,
        required=True,
        help_text="Categoría del rechazo"
    )
    can_reapply_after = serializers.DateField(
        required=False,
        help_text="Fecha después de la cual el usuario puede volver a aplicar"
    )
    
    
    def create(self, validated_data):
        application = self.context['application']
        request = self.context['request']
        
        try:
            rejected_application = FinancialInstitutionApplicationService.reject_application(
                application_id=application.id,
                reviewed_by=request.user,
                **validated_data
            )
            return rejected_application
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        return {
            'id': instance.id,
            'status': instance.status,
            'rejection_reason': instance.rejection_reason,
            'rejection_category': instance.rejection_category,
            'can_reapply_after': instance.can_reapply_after.strftime("%Y-%m-%d") if instance.can_reapply_after else None,
            'reviewed_at': instance.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if instance.reviewed_at else None,
            'reviewed_by': instance.reviewed_by.email if instance.reviewed_by else None
        }