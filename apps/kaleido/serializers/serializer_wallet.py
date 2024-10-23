from rest_framework import serializers
from ..models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model=Wallet
        fields = [
            'id',
            'id_wallet',
            'secret',
            'user_id',
            'environment_id',
            'wallet_service',
            'zone_domain',
            'created_at',
            'consortia'
            ]
