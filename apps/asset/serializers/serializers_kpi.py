from ..models import ActivoInversion, FeedbackKPI
from rest_framework import serializers
from django.utils import timezone

class UpdateActivoKPISerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInversion
        fields = [
            'id',
            'valor_token', 'tokens_totales', 'tokens_disponibles', 'tir_ea',
            'pago_rendimiento', 'tenencia_sugerida', 'renta_mensual', 'renta_por_m2',
            'incremento_anual', 'modelo_financiero', 'clase_inversion',
            'plazo_contrato', 'teaser', 'no_id_fideicomiso', 'nombre_fideicomiso',
            ]
        
class FeedbackKpiCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackKPI
        fields = [
            'id',
            'activo', 'mensaje',
            ]
        
class FeedbackKpiListSerializer(serializers.ModelSerializer):
    remitente = serializers.SerializerMethodField('get_remitente_nombre')
    fecha = serializers.SerializerMethodField('get_fecha_mensaje')
    class Meta:
        model = FeedbackKPI
        fields = [
            'id',
            'activo', 'mensaje',
            'remitente', 'destinatario',
            'fecha'
            ]
    def get_remitente_nombre(self, obj):
        return {
            'id':obj.remitente.id,
            'nombre':obj.remitente.email,
            }
    
    def get_fecha_mensaje(self, obj):
        hora = obj.created_at.astimezone(timezone.get_current_timezone())
        return hora.strftime('%I:%M %p %d/%m/%Y')