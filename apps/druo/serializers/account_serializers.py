from ..models import AccountType
from rest_framework import serializers

class AccountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'id',
            'value',
            'name'
        )
        model = AccountType
