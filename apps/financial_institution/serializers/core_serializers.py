from rest_framework import serializers
from apps.financial_institution.models.core import FinancialInstitution, FinancialInstitutionApplication
from apps.financial_institution.services.fi_application_service import FinancialInstitutionApplicationService
from apps.financial_institution.services.actions_application_service import FIActionsService
from apps.user.serializers.basic_info_user_serializer import UserShortInfoSerializer

class FISerializer(serializers.ModelSerializer):
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
    
class FIApplicationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reviewed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    requested_investor_profile = serializers.ChoiceField(
        choices=FinancialInstitutionApplication.InvestorProfile.choices,
        required=True,
        help_text="Perfil del inversor"
    )
    user = UserShortInfoSerializer(read_only=True)
    
    class Meta:
        model = FinancialInstitutionApplication
        fields = '__all__'
        read_only_fields = ['id', 'user', 'status', 'created_at']
        extra_kwargs = {
            'financial_institution': {'required': True},
            'requested_investment_amount': {'required': True},
            'application_notes': {'required': False},
            'kyc_documents': {'required': False, 'allow_null': True, 'default': {}},
        }

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
                request=request,
                **validated_data
            )
            
            # Agregar metadatos del request
            application.ip_address = ip
            application.user_agent = user_agent
            application.save()
            
            return application
            
        except ValueError as e:
            raise serializers.ValidationError({"detail": [str(e)]})
        except Exception as e:
            raise serializers.ValidationError({"detail": [f"Error inesperado al crear la solicitud. {str(e)}"]})


# ========================================================
# Serializers específicos para acciones en la aplicación
# ========================================================      
class FIPreApprovalSerializer(serializers.Serializer):
    """Serializer específico para pre-aprobaciones"""
    
    review_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Notas de revisión para la pre-aprobación"
    )
    max_investment_amount = serializers.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        required=True,
        help_text="Monto de inversión solicitado actualizado"
    )
    
    def validate_requested_investment_amount(self, value):
        """Validar que el monto sea positivo si se proporciona"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "El monto de inversión debe ser mayor que cero"
            )
        return value
    
    def create(self, validated_data):
        """Crear pre-aprobación usando el servicio"""
        application = self.context['application']
        request = self.context['request']
        
        try:
            application, approval = FIActionsService.pre_approve_application(
                application_id=application,
                pre_approved_by=request.user,
                request=request,
                **validated_data
            )
            return application
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        return {
            'id': instance.id,
            'application_id': instance.id,
            'status': instance.status,
            'reviewed_by': instance.reviewed_by.email if instance.reviewed_by else None,
            'reviewed_at': instance.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if instance.reviewed_at else None,
            'review_notes': instance.review_notes,
            'financial_institution_name': instance.financial_institution.name,
            'user_email': instance.user.email,
            'approval_id': instance.approval.id if hasattr(instance, 'approval') and instance.approval else None,
            'message': 'Solicitud pre-aprobada exitosamente. Puede proceder a configurar los detalles finales y enviar el contrato.'
        }


class FIContractSendSerializer(serializers.Serializer):
    """Serializer específico para envío de contratos"""
    
    contract_url = serializers.URLField(
        required=True,
        help_text="URL del documento de contrato a enviar"
    )
    send_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Notas adicionales sobre el envío del contrato"
    )
    
    def validate_contract_url(self, value):
        """Validar que la URL del contrato sea válida"""
        if not value:
            raise serializers.ValidationError("La URL del contrato es requerida")
        
        # Validación adicional de formato si es necesario
        if not (value.startswith('http://') or value.startswith('https://')):
            raise serializers.ValidationError("La URL debe comenzar con http:// o https://")
        
        return value
    
    def create(self, validated_data):
        """Enviar contrato usando el servicio"""
        application = self.context['application']
        request = self.context['request']
        
        try:
            application, approval = FIActionsService.send_contract(
                application_id=application,
                sent_by=request.user,
                request=request,
                **validated_data
            )
            return application
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        approval = getattr(instance, 'approval', None)
        return {
            'id': instance.id,
            'application_id': instance.id,
            'status': instance.status,
            'approval_id': approval.id if approval else None,
            'contract_sent_at': approval.contract_sent_at.strftime("%Y-%m-%d %H:%M:%S") if approval and approval.contract_sent_at else None,
            'contract_generated_at': approval.contract_generated_at.strftime("%Y-%m-%d %H:%M:%S") if approval and approval.contract_generated_at else None,
            'financial_institution_name': instance.financial_institution.name,
            'user_email': instance.user.email,
            'message': 'Contrato enviado exitosamente. El usuario debe proceder a firmarlo.'
        }
        
        
class FIContractSignSerializer(serializers.Serializer):
    """Serializer específico para firma de contratos"""
    
    signature_method = serializers.ChoiceField(
        choices=[
            ('digital', 'Firma Digital'),
            ('manual', 'Firma Manual Escaneada'),
            ('other', 'Otro Método')
        ],
        required=True,
        help_text="Método utilizado para firmar el contrato"
    )
    user_signature_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Notas adicionales sobre la firma del usuario"
    )
    
    def validate_signature_method(self, value):
        """Validar que el método de firma sea válido"""
        valid_methods = ['digital', 'manual', 'other']
        if value not in valid_methods:
            raise serializers.ValidationError(f"Método de firma inválido. Opciones válidas: {', '.join(valid_methods)}")
        return value
    
    def validate(self, attrs):
        """Validar que solo el propietario de la solicitud pueda firmar"""
        request = self.context.get('request')
        application_id = self.context.get('application')
        application = FinancialInstitutionApplication.objects.filter(id=application_id).first()
        
        if request and request.user:
            user = request.user
            
            if application.user != user:
                raise serializers.ValidationError({"detail": "No tienes permiso para firmar este contrato."})
        
        return attrs
    
    def create(self, validated_data):
        """Marcar contrato como firmado usando el servicio"""
        application = self.context['application']
        request = self.context['request']
        
        try:
            application, approval = FIActionsService.user_sign_contract(
                application_id=application,
                signed_by=request.user,
                request=request,
                **validated_data
            )
            return application
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        approval = getattr(instance, 'approval', None)
        
        return {
            'id': instance.id,
            'application_id': instance.id,
            'status': instance.status,
            'approval_id': approval.id if approval else None,
            'financial_institution_name': instance.financial_institution.name,
            'user_email': instance.user.email,
            'message': 'Contrato marcado como firmado exitosamente. La solicitud está en revisión interna.'
        }
        
        
class FIApprovalSerializer(serializers.Serializer):
    """Serializer específico para aprobaciones"""
    
    approval_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Notas adicionales sobre la aprobación"
    )
    conditions = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Condiciones asociadas a la aprobación"
    )
    expiry_date = serializers.DateField(
        required=False,
        help_text="Fecha de expiración de la aprobación"
    )
    
    def validate_approval_date(self, value):
        """Validar que la fecha de aprobación no sea futura"""
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError("La fecha de aprobación no puede ser futura")
        return value
    
    def create(self, validated_data):
        application = self.context['application']
        request = self.context['request']
        
        try:
            application, approval = FIActionsService.approve_application(
                application_id=application,
                approved_by=request.user,
                request=request,
                **validated_data
            )
            return application
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        return {
            'id': instance.id,
            'status': instance.status,
            'approved_by': instance.reviewed_by.email if instance.reviewed_by else None,
            'reviewed_at': instance.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if instance.reviewed_at else None,
            'financial_institution_name': instance.financial_institution.name,
            'user_email': instance.user.email,
            'approval_id': instance.approval.id if hasattr(instance, 'approval') and instance.approval else None,
            'message': 'Solicitud aprobada exitosamente.'
        }
        

class FIRejectionSerializer(serializers.Serializer):
    """Serializer específico para rechazos"""
    
    rejection_reason = serializers.CharField(
        required=True,
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
    
    def validate_can_reapply_after(self, value):
        """Validar que la fecha de reaplicación no sea en el pasado"""
        from django.utils import timezone
        if value and value < timezone.now().date():
            raise serializers.ValidationError("La fecha de reaplicación no puede ser en el pasado")
        return value
    
    def create(self, validated_data):
        application = self.context['application']
        request = self.context['request']
        
        try:
            rejected_application = FIActionsService.reject_application(
                application_id=application,
                reviewed_by=request.user,
                request=request,
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