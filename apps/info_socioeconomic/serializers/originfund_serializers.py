from ..models import OriginFund
from rest_framework import serializers

class OriginFundSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = OriginFund
        fields = [
            'id', 'name'
        ]