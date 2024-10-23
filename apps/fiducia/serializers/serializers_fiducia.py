from ..models import Fiducia
from rest_framework import serializers

class ListSelectFiduciaSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = Fiducia
        fields = [
                'id',
                'name',
                ]

class ListSelectFiduciaSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = Fiducia
        fields = [
                'id',
                'name',
                ]