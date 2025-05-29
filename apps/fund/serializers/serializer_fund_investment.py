from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework.exceptions import ValidationError
from django.core.validators import RegexValidator

from apps.fund.models import Fund, FundInvestment, FundApplication, FundToken
from apps.kaleido.models import InstanceOfTokenContract721, PromoteContract
from apps.kaleido.serializers.serializer_token_instance import InstanceOfTokenContract721Serializer
from apps.kaleido.serializers.serializer_wallet import WalletFundSerializer

from apps.kaleido.utils import create_wallet_for_fund, create_instance_token_contract_721

from django.db import transaction

class FundApplicationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    fund = serializers.PrimaryKeyRelatedField(queryset=Fund.objects.all(), write_only=True)
    applicant = serializers.PrimaryKeyRelatedField(read_only=True)
    reviewed_by = serializers.PrimaryKeyRelatedField(read_only=True)
    
    requested_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, 
        validators=[RegexValidator(
            regex=r'^\d+(\.\d{1,2})?$',
            message="Request amount must be a valid decimal number."
        )]
    )
    
    class Meta:
        model = FundApplication
        fields = [
            'id', 'fund', 'applicant', 'reviewed_by', 'requested_amount',
            'status', 'created_at', 'updated_at', 'reviewed_at', 
            'applicant_notes', 'reviewed_at', 'rejection_reason'
                  ]
        read_only_fields = ['applicant', 'reviewed_by', 'created_at']

    
    def validate_fund(self, value):
        try:
            fund = Fund.objects.get(id=value.id)
        except Fund.DoesNotExist:
            raise ValidationError(f"Fund with ID {value.id} does not exist.")
        if fund.status != 'active':
            raise ValidationError("Cannot apply to a fund that is not active.")
        return value
    
    def validate_request_amount(self, value):
        if value <= 0:
            raise ValidationError("Request amount must be greater than zero.")
        return value
    
    def create(self, validated_data):
        validated_data['applicant'] = self.context['request'].user        
        return super().create(validated_data)

class FundInvestmentSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    fund_id = serializers.IntegerField(write_only=True, required=True)
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
        fields = ['id', 'fund_id', 'investor', 'invested_amount', 'created_at']
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