from rest_framework import serializers
from .models import FundPrice, Fund
from apps.kaleido.serializers.serializer_wallet import WalletFundSerializer

class FundSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    hd_wallet = WalletFundSerializer(read_only=True)
    
    class Meta:
        model = Fund
        fields = ['id', 'user', 'hd_wallet', 'name', 'description', 'amount', 'created_at']
        read_only_fields = ['hd_wallet', 'created_at', 'user']

class FundPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundPrice
        fields = ['timestamp', 'unitPrice']