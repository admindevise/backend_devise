from django.http import JsonResponse
from django.db.models import Q
from apps.asset.serializers.serializers_kpi import FeedbackKpiCreateSerializer, FeedbackKpiListSerializer, UpdateActivoKPISerializer
from ..models import ActivoInversion, EstadoAprobacion, FeedbackKPI
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import generics
from django.utils.translation import ugettext as _


@permission_classes([IsAuthenticated])
class UpdateKPIAssetView(generics.UpdateAPIView):
    serializer_class = UpdateActivoKPISerializer
    queryset = ActivoInversion.objects.all()

    def perform_update(self, serializer):
        instance = serializer.instance
        print("update KPI", instance.estado_aprobacion.codigo)
        # Realiza la validación para verificar si el ActivoInversion está activo
        if instance.estado_aprobacion.paso < 11:
            serializer.save(
                estado_aprobacion = EstadoAprobacion.objects.get(codigo="PENDIENTE_RESPUESTA_KPI_DEVISE"),
            )
        else:
            raise PermissionDenied("No se puede editar los KPI previamente aprobado por Devise")

@permission_classes([IsAuthenticated])
class ReadKPIAssetView(generics.RetrieveAPIView):
    serializer_class = UpdateActivoKPISerializer
    queryset = ActivoInversion.objects.all()

# Endpoint que aprueba  Devise los KPI del activo

def ApprovedKpiAssetAdmin(request):
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        if update_activo.estado_aprobacion.codigo =="PENDIENTE_RESPUESTA_KPI_DEVISE" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_KPI_APROBADO_DEVISE")
            update_activo.save()
            response = {
                    'status': 'success',
                    'title': 'Activo Actualizado',
                    'message': 'Queda a la espera del smart contract'
                }
            return JsonResponse(response)
        else:
            JsonResponse({
                    'status': 'error',
                    'title': 'No aplica el estado de aprobación del activo',
                })
    else:
        response = {
                    'status': 'error',
                    'title': 'Not valid method',
                }
        return JsonResponse(response)
    
# ENDPOINT mensajes entre  SPONSOR Y EL ADMIN
def SendKPIMsjSponsor(request):
    if request.method == 'POST':
        print(">>VALIDATED request : ", request.POST)
        print(">>VALIDATED DATA : ", request.POST.get('mensaje'))
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        if update_activo.estado_aprobacion.codigo =="PENDIENTE_RESPUESTA_KPI_DEVISE" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_EN_CALCULO_KPI_SPONSOR")
            update_activo.save()
            mensaje = FeedbackKPI.objects.create(
                activo = update_activo,
                mensaje = request.POST.get('mensaje'),
                remitente = request.user,
                destinatario = update_activo.sponsor.user, #al usuario de la compañia sponsor
                )
            response = {
                    'status': 'success',
                    'title': _('Activo msj KPI Actualizado'),
                    'message': _('Se ha enviado el mensaje sobre KPI al sponsor')
                }
            return JsonResponse(response)
        else:
            JsonResponse({
                    'status': 'error',
                    'title': 'No aplica el estado de aprobación del activo',
                })
            
@permission_classes([IsAuthenticated])
class FeedbackKPICreate(generics.CreateAPIView):
    serializer_class = FeedbackKpiCreateSerializer
    queryset = FeedbackKPI.objects.all()

    def perform_create(self, serializer):
        validated_data =self.request.data
        update_activo = ActivoInversion.objects.get(id=validated_data.get('activo'))
        #Primer caso paso 1 al 2 Visto Bueno del sponsor le escribe al propietario algo falta
        if 10 <= update_activo.estado_aprobacion.paso < 11 :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="PENDIENTE_RESPUESTA_KPI_DEVISE")
            update_activo.save()
            serializer.save(
                remitente = self.request.user,
                destinatario = update_activo.propietario,
                )
        else:
            raise PermissionDenied("No se puede enviar mensajes de KPI en el estado actual del Activo")


# Enpoint que solicita los Mensajes del sobre la MinutaEscrituracion Mandan el PK Activo
@permission_classes([IsAuthenticated])
class ListMessagesKPIView(generics.ListAPIView):
    queryset = FeedbackKPI.objects.all()
    serializer_class = FeedbackKpiListSerializer


    def get_queryset(self):
        asset_model = ActivoInversion.objects.get(id=self.kwargs.get('pk'))
        queryset = FeedbackKPI.objects.filter(activo=asset_model)
        return queryset