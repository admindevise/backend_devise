from apps.asset.models import ActivoInversion
from rest_framework import serializers

class NuevaEscrituraActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInversion
        fields = [
            'nueva_escritura'
            ]
    