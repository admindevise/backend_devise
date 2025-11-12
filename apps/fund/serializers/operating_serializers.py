from rest_framework import serializers
from apps.fund.models.operating import FundOperatingExpense, FundOperatingIncome


class FundOperatingExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundOperatingExpense
        fields = '__all__'
        
class FundOperatingIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundOperatingIncome
        fields = '__all__'