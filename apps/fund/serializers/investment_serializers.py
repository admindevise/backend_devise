from rest_framework import serializers
from django.core.validators import RegexValidator
from rest_framework.exceptions import ValidationError

from apps.fund.models.membership import FundInvestment
from apps.fund.models.core import Fund

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