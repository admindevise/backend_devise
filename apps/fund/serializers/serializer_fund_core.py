from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework.exceptions import ValidationError
from django.core.validators import RegexValidator

from apps.fund.models import Fund, FundInvestment, TransferReceipt, FundToken
from apps.kaleido.models import InstanceOfTokenContract721, PromoteContract
from apps.kaleido.serializers.serializer_token_instance import InstanceOfTokenContract721Serializer
from apps.kaleido.serializers.serializer_wallet import WalletFundSerializer

from apps.kaleido.utils import create_wallet_for_fund, create_instance_token_contract_721

from django.db import transaction

class FundSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    hd_wallet = WalletFundSerializer(read_only=True)
    token_contract_721 = InstanceOfTokenContract721Serializer(read_only=True)
    promote_contract_id = serializers.IntegerField(write_only=True)
    
    # Validacion para nickname solo numeros y letas
    nickname_tokens = RegexValidator(r'^[a-zA-Z0-9_]+$', 'El nickname solo puede contener letras, números y guiones bajos')
    
    amount_total = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    total_investors = serializers.SerializerMethodField()
    
    class Meta:
        model = Fund
        fields = [
            # Campos comunes
            'id', 'user', 'hd_wallet', 'name', 'description',
            'amount_units', 'amount_tokens', 'nickname_tokens',
            'token_contract_721', 'secret', 'price_per_unit', 'status', 
            'promote_contract_id', 'image', 'created_at',
            
            # Información Regulatoria
            'superintendency_registry', 'tax_id', 'fund_type', 'management_company',
            
            # Parámetros Financieros
            'annual_return', 'initial_unit_value', 'total_assets',
            'management_fee', 'success_fee', 'risk_rating',
            
            # Políticas de Inversión
            'risk_profile', 'investment_horizon', 'asset_composition',
            'dividend_distribution',
            
            # Operaciones
            'minimum_investment', 'permanence_period', 'early_withdrawal_penalty',
            'trading_hours', 'operations_closing_date',
            
            # Otros Campos Relevantes
            'main_manager', 'operations_start_date',
            
            # Funciones
            'amount_total', 'current_price', 'total_investors'
        ]
        read_only_fields = ['hd_wallet', 'token_contract_721', 'created_at', 'user']
        
    def get_amount_total(self, obj):
        return obj.amount_total
    
    def get_current_price(self, obj):
        return obj.current_price
    
    def get_total_investors(self, obj):
        return obj.total_investors

    def create(self, validated_data):
        user = self.context['request'].user
        secret = validated_data.get('secret')
        
        promote_contract_id = validated_data.pop('promote_contract_id', None)
        
        if not secret:
            raise ValidationError({"secret": "Secret is required."})
        if not promote_contract_id:
            raise ValidationError({"promote_contract_id": "Promote contract id is required."})
        
        # Validar que el promote_contract_id exista
        try:
            promote_contract = PromoteContract.objects.get(id=promote_contract_id)
        except PromoteContract.DoesNotExist:
            raise ValidationError({"promote_contract_id": "Promote contract id is not found."})
        
        # Eliminar "user" de validated_data para evitar que se pase dos veces
        validated_data.pop('user', None)
        
        with transaction.atomic():
            # Crear el Fund
            fund = Fund.objects.create(user=user, **validated_data)
            
            # Crear la wallet
            wallet, error = create_wallet_for_fund(user, secret)
            if not wallet:
                raise ValidationError({"hd_wallet": f"Error creating wallet: {error}"})
            fund.hd_wallet = wallet
            fund.save()
            
            # Crear la instancia del contrato token
            token_instance, error = create_instance_token_contract_721(
                user,
                fund.name,
                fund.name[:3].upper(),
                promote_contract=promote_contract
                )
            if not token_instance:
                raise ValidationError({"token_contract": f"Error creating token contract instance: {error}"})
            # Asignar el token_instance al fund
            fund.token_contract_721 = token_instance
            fund.save(update_fields=['token_contract_721'])
            return fund

class TransferReceiptSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = TransferReceipt
        fields = ['id','user', 'transaction_id', 'fund', 'description', 'created_at']
        read_only_fields = ['created_at']

class FundTokenSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reserved_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reservation_expires_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = FundToken
        fields = ['id', 'fund', 'token_id', 'nickname', 'status', 'created_by', 'owner_user', 'reserved_for_sale', 'reserved_for_purchase', 'reserved_at', 'reservation_expires_at' , 'created_at']
        read_only_fields = ['id', 'created_at']
