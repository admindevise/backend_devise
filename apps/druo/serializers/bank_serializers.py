from ..models import Bank
from rest_framework import serializers

class BankSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'id',
            'institution_name',
            'country'
        )
        model = Bank
