from rest_framework import serializers
from ..models import Wallet
from apps.user.serializers.basic_info_user_serializer import UserBasicInfoSerializer

class WalletSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    user_detail = UserBasicInfoSerializer(source='user', read_only=True)
    class Meta:
        model=Wallet
        fields = ['id', 'id_wallet', 'secret','user_id', 'environment_id','wallet_service', 'zone_domain','created_at', 'consortia', 'user_detail']

class WalletFundSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    class Meta:
        model=Wallet
        fields = ['id', 'id_wallet', 'secret', 'environment_id','wallet_service', 'zone_domain','consortia', 'created_at']
        read_only_fields = ['id', 'id_wallet', 'created_at']
