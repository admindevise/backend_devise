from ..models import AccountSubtype
from rest_framework import serializers

class AccountSubtypeSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'id',
            'value',
            'name'
        )
        model = AccountSubtype
