from rest_framework import serializers

from apps.fund.models.membership import FundInvestment, InvestmentApplication
from apps.fund.models.core import Fund

from apps.fund.services.investment_service import InvestmentService, InvestmentError

class InvestmentSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    payment_date = serializers.DateField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    maturity_date = serializers.DateField(format="%Y-%m-%d", read_only=True)
    
    class Meta:
        model = FundInvestment
        fields = [
            'id', 'created_at', 'updated_at', 'payment_date', 'maturity_date',
            'final_invested_amount', 'units_owned', 'purchase_price_per_unit',
            'current_unit_value', 'investment_status',
            'payment_status', 'payment_method', 'payment_reference',
            
            # ✅ Agregar las propiedades directamente
            'user', 'fund', 'fund_name', 'financial_institution_name'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'status', 'payment_date', 'maturity_date')

class InvestmentApplicationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reviewed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    contract_sent_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    contract_signed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)  
    contract_signature_deadline = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)     
    rejected_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    can_reapply_after = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    withdrawn_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = InvestmentApplication
        fields = '__all__'
        read_only_fields = ('id', 'status', 'created_at', 'updated_at', 'reviewed_at', 'contract_sent_at', 'contract_signed_at', 'contract_signature_deadline', 'rejected_at', 'can_reapply_after', 'withdrawn_at')

class InvestmentDashboardSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    class Meta:
        model = FundInvestment
        fields = ['id', 'fund', 'fund_name', 'financial_institution_name', 'created_at', 'final_invested_amount', 'units_owned']
        read_only_fields = fields


class SubmitInvestmentSerializer(serializers.Serializer):
    requested_amount = serializers.DecimalField(max_digits=14, decimal_places=2,required=True)
    fund = serializers.IntegerField(required=True)
    accepts_terms_and_conditions = serializers.BooleanField(required=True)
    accepts_risk_disclosure = serializers.BooleanField(required=True)
    
    def validate_fund(self, value):
        try:
            fund = Fund.objects.get(id=value)
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe")
        return fund
    
    def create(self, validated_data):
        request = self.context.get('request')
        
        # Capturar metadatos del request
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            application = InvestmentService.submit_investment(
                fund=validated_data['fund'],
                user=request.user,
                requested_amount=validated_data['requested_amount'],
                accepts_terms_and_conditions=validated_data['accepts_terms_and_conditions'],
                accepts_risk_disclosure=validated_data['accepts_risk_disclosure'],
                request=request
            )
            
            application.ip_address = ip
            application.user_agent = user_agent
            application.save()
            
            return application
        except InvestmentError as e:
            raise serializers.ValidationError(str(e))
        
    def to_representation(self, instance):
        application = getattr(instance, 'application', instance)
        
        return {
            'id': application.id,
            'fund_id': application.fund.id,
            'fund_name': application.fund.name,
            'user_id': application.user.id,
            'user_email': application.user.email,
            'requested_amount': str(application.requested_amount),
            'application_status': application.application_status,
            'created_at': application.created_at.strftime('%Y-%m-%d %H:%M:%S') if application.created_at else None,
        }
        
class IAReviewSerializer(serializers.Serializer):
    """Serializer para marcar solicitud en revisión"""
    
    review_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Notas de revisión por parte del administrador"
    )
    
    def validate_application(self, value):
        application_id = self.context['application_id']
        
        try:
            application = InvestmentApplication.objects.get(id=application_id)
        except InvestmentApplication.DoesNotExist:
            raise serializers.ValidationError(f"La solicitud de inversión con el ID:{application_id} no existe")
        return application
    
    def create(self, validated_data):
        """Marcar solicitud en revisión usando el servicio"""
        application_id = self.context['application_id']
        request = self.context['request']
        
        try:
            application = InvestmentApplication.objects.get(id=application_id)
            
            reviewed_application = InvestmentService.mark_under_review(
                application=application,
                reviewed_by=request.user,
                review_notes=validated_data.get('review_notes', ''),
                request=request
            )
            return reviewed_application
        except InvestmentError as e:
            raise serializers.ValidationError(str(e))
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        return {
            'id': instance.id,
            'application_status': instance.application_status,
            'reviewed_by': instance.reviewed_by.email,
            'reviewed_at': instance.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if instance.reviewed_at else None,
            'review_notes': instance.review_notes,
            'fund_name': instance.fund.name,
            'user_email': instance.user.email,
            'requested_amount': str(instance.requested_amount),
            'message': 'Solicitud marcada en revisión exitosamente.'
        }

class IASendContractSerializer(serializers.Serializer):
    """Serializer para envío de contrato de inversión"""
    
    contract_url = serializers.URLField(
        required=True,
        help_text="URL del documento de contrato de inversión a enviar"
    )
    
    def validate_contract_url(self, value):
        """Validar que la URL del contrato sea válida"""
        if not value:
            raise serializers.ValidationError("La URL del contrato es requerida")
        
        # Validación adicional de formato
        if not (value.startswith('http://') or value.startswith('https://')):
            raise serializers.ValidationError("La URL debe comenzar con http:// o https://")
        
        return value
    
    def validate_application(self, value):
        application_id = self.context['application_id']
        
        try:
            application = InvestmentApplication.objects.get(id=application_id)
        except InvestmentApplication.DoesNotExist:
            raise serializers.ValidationError(f"La solicitud de inversión con el ID:{application_id} no existe")
        return application
    
    def create(self, validated_data):
        """Enviar contrato usando el servicio"""
        application_id = self.context['application_id']
        request = self.context['request']
        
        try:
            application = InvestmentApplication.objects.get(id=application_id)
            
            approved_application = InvestmentService.send_contract(
                application=application,
                contract_url=validated_data['contract_url'],
                contract_sent_by=request.user,
                request=request
            )
            return approved_application
        except InvestmentError as e:
            raise serializers.ValidationError(str(e))
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        return {
            'id': instance.id,
            'application_status': instance.application_status,
            'contract_url': instance.contract_url,
            'contract_sent_by': instance.contract_sent_by.email,
            'contract_sent_at': instance.contract_sent_at.strftime("%Y-%m-%d %H:%M:%S") if instance.contract_sent_at else None,
            'contract_signature_deadline': instance.contract_signature_deadline.strftime("%Y-%m-%d %H:%M:%S") if instance.contract_signature_deadline else None,
            'fund_name': instance.fund.name,
            'user_email': instance.user.email,
            'requested_amount': str(instance.requested_amount),
            'message': 'Contrato enviado exitosamente. El usuario debe proceder a firmarlo.'
        }

class IAContractSignSerializer(serializers.Serializer):
    """Serializer para firma de contrato de inversión por parte del usuario"""
    
    def validate(self, attrs):
        """Validación a nivel de serializer para verificar que la aplicación existe"""
        application_id = self.context.get('application_id')
        
        if not application_id:
            raise serializers.ValidationError("ID de aplicación no proporcionado en el contexto")
        
        try:
            application = InvestmentApplication.objects.get(id=application_id)
        except InvestmentApplication.DoesNotExist:
            raise serializers.ValidationError({
                "detail": f"La solicitud de inversión con el ID:{application_id} no existe"})
        
        # Agregar la aplicación a los datos validados para uso posterior
        attrs['_application'] = application
        return attrs
    
    def create(self, validated_data):
        """Firmar contrato usando el servicio"""
        # Usar la aplicación que ya validamos
        application = validated_data['_application']
        request = self.context['request']
        
        try:            
            signed_application, fund_investment = InvestmentService.sign_contract(
                application=application,
                user=request.user,
                request=request
            )
            return signed_application
        except InvestmentError as e:
            raise serializers.ValidationError(str(e))
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        return {
            'id': instance.id,
            'application_status': instance.application_status,
            'contract_signed_at': instance.contract_signed_at.strftime("%Y-%m-%d %H:%M:%S") if instance.contract_signed_at else None,
            'fund_name': instance.fund.name,
            'user_email': instance.user.email,
            'requested_amount': str(instance.requested_amount),
            'message': 'Contrato firmado exitosamente. Su solicitud de inversión ha sido aprobada.'
        }



