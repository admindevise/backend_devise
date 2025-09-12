from rest_framework import serializers

from apps.fund.models.core import Fund
from apps.fund.models.membership import InvestorContract
from apps.fund.services.investor_contract_service import InvestorContractService, InvestorContractError

class InvestorContractSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    expired_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    contract_signed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = InvestorContract
        fields = '__all__'
        read_only_fields = ['user', 'created_at']

class InvestorContractCreateSerializer(serializers.Serializer):
    contract_url = serializers.URLField(required=True)
    fund = serializers.IntegerField(required=True)
    
    def validate_fund(self, value):
        try:
            fund=Fund.objects.get(id=value)
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe.")
        return fund
    
    def create(self, validated_data):
        request = self.context.get('request')
        
        try:
            contract = InvestorContractService.create_contract(
                fund=validated_data['fund'],
                user=request.user,
                contract_url=validated_data['contract_url'],
                request=request,
            )
            return contract
        
        except InvestorContractError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        return InvestorContractSerializer(instance).data


class InvestorContractSignSerializer(serializers.Serializer):
    def validate(self, attrs):
        contract = self.context.get('contract')
        if not contract:
            raise serializers.ValidationError({
                "detail": "El contrato es obligatorio para firmar."
            })
        
        try:
            InvestorContract.objects.select_related('fund').get(id=contract)
        except InvestorContract.DoesNotExist:
            raise serializers.ValidationError({
                "detail": f"El contrato con ID {contract} no existe."
            })
        return attrs
    
    def save(self):
        contract = self.context['contract']
        request = self.context['request']
        
        try:
            signed_contract = InvestorContractService.sign_contract(
                contract=contract,
                request=request,
            )
            return signed_contract
        
        except InvestorContractError as e:
            raise serializers.ValidationError(str(e))
    
    def to_representation(self, instance):
        contract_id = self.context.get('contract')
        if contract_id:
            try:
                # Obtener el contrato actualizado desde la base de datos
                contract = InvestorContract.objects.select_related('fund', 'user').get(id=contract_id)
                
                # Construcción manual de la respuesta
                return {
                    'id': contract.id,
                    'user': contract.user.id if contract.user else None,
                    'user_email': contract.user.email if contract.user else None,
                    'fund': contract.fund.id if contract.fund else None,
                    'fund_name': contract.fund.name if contract.fund else None,
                    'contract_url': contract.contract_url,
                    'status': contract.status,
                    'created_at': contract.created_at.strftime("%Y-%m-%d %H:%M:%S") if contract.created_at else None,
                    'expired_at': contract.expired_at.strftime("%Y-%m-%d %H:%M:%S") if contract.expired_at else None,
                    'contract_signed_at': contract.contract_signed_at.strftime("%Y-%m-%d %H:%M:%S") if contract.contract_signed_at else None,
                    'suspension_reason': contract.suspension_reason,
                    'suspended_at': contract.suspended_at.strftime("%Y-%m-%d %H:%M:%S") if contract.suspended_at else None,
                    'message': 'Contrato firmado exitosamente.'
                }
            except InvestorContract.DoesNotExist:
                return {"detail": "El contrato no se encontró después de la firma."}
