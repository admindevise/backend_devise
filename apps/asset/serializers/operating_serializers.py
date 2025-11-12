from rest_framework import serializers
from apps.asset.models.operating import AssetOperatingExpense, AssetOperatingIncome

class AssetOperatingExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetOperatingExpense
        fields = '__all__'
        
class AssetOperatingIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetOperatingIncome
        fields = '__all__'