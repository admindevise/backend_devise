from rest_framework import serializers
from .models import FundPrice, Fund

class FundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ['id', 'name', 'description', 'amount', 'created_at']
        read_only_fields = ['created_at']

class FundPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundPrice
        fields = ['timestamp', 'unitPrice']