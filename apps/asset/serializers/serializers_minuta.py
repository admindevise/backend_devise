from ..models import MinutaEscrituracion, FeedbackMinutaEscrituracion

from rest_framework import serializers


class MinutaEscrituracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MinutaEscrituracion
        fields = [
            'activo', 'archivo', 'aprobado_fiducia', 'aprobado_notario',
            'aprobado_sponsor', 'aprobado_propietario', 
        ]

class FeedBackMinutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackMinutaEscrituracion
        fields = [
            'minuta', 'mensaje'
        ]

class ListFeedBackMinutaSerializer(serializers.ModelSerializer):

    remitente = serializers.SerializerMethodField('get_remitente_nombre')
    fecha = serializers.SerializerMethodField('get_fecha_mensaje')

    class Meta:
        model = FeedbackMinutaEscrituracion
        fields = [
            'id',
            'minuta', 'mensaje',
            'remitente', 'destinatario',
            'fecha'
        ]
    def get_remitente_nombre(self, obj):
        return {
            'id':obj.remitente.id,
            'nombre':obj.remitente.email,
            }
    
    def get_fecha_mensaje(self, obj):
        return obj.created_at.strftime('%I:%M %p %d/%m/%Y')