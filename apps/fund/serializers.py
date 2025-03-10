from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework.exceptions import ValidationError

from apps.fund.models import FundPrice, Fund, FundInvestment, TransferReceipt
from apps.kaleido.models import InstanceOfTokenContract721, PromoteContract
from apps.kaleido.serializers.serializer_token_instance import InstanceOfTokenContract721Serializer
from apps.kaleido.serializers.serializer_wallet import WalletFundSerializer
from apps.kaleido.utils import create_wallet_for_user, create_instance_token_contract_721


class FundSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    hd_wallet = WalletFundSerializer(read_only=True)
    token_contract_721 = InstanceOfTokenContract721Serializer(read_only=True)
    promote_contract_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Fund
        fields = ['id', 'user', 'hd_wallet', 'name', 'description', 'amount', 'token_contract_721', 'secret', 'promote_contract_id', 'created_at']
        read_only_fields = ['hd_wallet', 'token_contract_721', 'created_at', 'user']

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
            wallet, error = create_wallet_for_user(user, secret)
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

class FundInvestmentSerializer(serializers.ModelSerializer):
    investor = serializers.HiddenField(default=serializers.CurrentUserDefault())
    joined_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = FundInvestment
        fields = ['fund', 'investor', 'invested_amount', 'joined_at']
        read_only_fields = ['joined_at']
        validators = [
            UniqueTogetherValidator(
                queryset=FundInvestment.objects.all(),
                fields=['fund', 'investor'],
                message="You have already invested in this fund."
            )
        ]

class TransferReceiptSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = TransferReceipt
        fields = ['user', 'transfer_id', 'fund', 'created_at']
        read_only_fields = ['created_at']

class FundPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundPrice
        fields = ['timestamp', 'unitPrice']