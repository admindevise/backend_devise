from django.http import JsonResponse
from ..models import ActivoInversion, EstadoAprobacion, MinutaEscrituracion, FeedbackMinutaEscrituracion
from ..serializers.serializers_minuta import FeedBackMinutaSerializer, ListFeedBackMinutaSerializer, MinutaEscrituracionSerializer
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status


@permission_classes([IsAuthenticated])
class CreateMinutaEscrituracionView(generics.CreateAPIView):
    serializer_class = MinutaEscrituracionSerializer
    queryset = MinutaEscrituracion.objects.all()

    def perform_create(self, serializer):
        # Obtén el usuario que está realizando la solicitud
        user = self.request.user
        activo = serializer.validated_data['activo'] 
        print("activo es =", activo)
        print("Usuario es: ", user)
        user_sponsor = activo.sponsor.user
        print("Usuario sponsor es es: ", user_sponsor)
        # Verifica si el usuario es el responsable
        if user != user_sponsor:
            print("No es el mismo SPONSOR")
            return Response(
                {"detail": "No tienes permiso para crear esta minuta."},
                status=status.HTTP_403_FORBIDDEN
            )
        print("Si esel mismo SPONSOR se crea el documento y se avanza")
        # Si el usuario es el responsable, crea la minuta
        serializer.save()
        activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo='MINUTA_ESCRITURACION_CARGADA')
        activo.save()

# Endpoint que aprueba el admin Devise el activo

def MinutaEscrituracionApprovedFiducia(request):
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        minuta_escrituracion = MinutaEscrituracion.objects.get(activo=update_activo)
        minuta_escrituracion.aprobado_fiducia = True
        minuta_escrituracion.save()
        if (minuta_escrituracion.aprobado_fiducia == True and 
            minuta_escrituracion.aprobado_propietario and
            minuta_escrituracion.aprobado_notario):
            minuta_escrituracion.minuta_aprobada = True
            minuta_escrituracion.save()
            update_activo.estado = EstadoAprobacion.objects.get(codigo='MINUTA_ESCRITURACION_APROBADA')
            update_activo.save()
            response = {
                    'status': 'success',
                    'title': 'Activo Actualizado',
                    'message': 'Queda a la espera de actualización por Notaria'
                }
            return JsonResponse(response)
        
        return JsonResponse({
                    'status': 'success',
                    'title': 'Activo Actualizado',
                    'message': 'Queda a la espera de respuesta de los demás actores'
                })
    else:
        response = {
                    'status': 'error',
                    'title': 'Not valid method',
                }
        return JsonResponse(response)
    
# Enpoint que envia mensajes del sobre la MinutaEscrituracion
def MinutaEscrituracionMessage(request):
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        minuta = MinutaEscrituracion.objects.get(activo=update_activo)
        mensaje = FeedbackMinutaEscrituracion.objects.create(
            minuta = minuta,
            mensaje = request.POST.get('mensaje'),
            remitente = request.user,
            destinatario = update_activo.sponsor.user, #al sponsor que carga
            )
        response = {
                'status': 'success',
                'title': 'Mensaje enviado',
                'message': 'Se ha enviado el mensaje al sponsor'
            }
        return JsonResponse(response)
    
# Enpoint que envian desde el front mensajes del sobre la MinutaEscrituracion
@permission_classes([IsAuthenticated])
class FeedbackMinutaCreateMessage(generics.CreateAPIView):
    serializer_class = FeedBackMinutaSerializer
    queryset = FeedbackMinutaEscrituracion.objects.all()

    def perform_create(self, serializer):
        validated_data =self.request.data
        update_activo = ActivoInversion.objects.get(id=validated_data.get('activo'))
        serializer.save(
            remitente = self.request.user,
            destinatario = update_activo.sponsor.user,
            minuta = MinutaEscrituracion.objects.get(activo=update_activo),
        )

# Enpoint que solicita los Mensajes del sobre la MinutaEscrituracion Mandan el PK Activo
@permission_classes([IsAuthenticated])
class ListMessagesMinutaEscrituracionView(generics.ListAPIView):
    queryset = FeedbackMinutaEscrituracion.objects.all()
    serializer_class = ListFeedBackMinutaSerializer

    def get_queryset(self):
        asset_model = ActivoInversion.objects.get(id=self.kwargs.get('pk'))
        queryset = FeedbackMinutaEscrituracion.objects.filter(minuta__activo=asset_model)
        return queryset

# Enpoint que envian desde el front mensajes del sobre la MinutaEscrituracion
@permission_classes([IsAuthenticated])
class MinutaEscrituracionApprovedPropietario(generics.UpdateAPIView):
    serializer_class = MinutaEscrituracionSerializer
    queryset = MinutaEscrituracion.objects.all()

    def perform_update(self, serializer):
        if serializer.is_valid():
            serializer.save()
            minuta_escrituracion = serializer.instance  # Obtén la instancia del serializer
            if (
                minuta_escrituracion.aprobado_fiducia and 
                minuta_escrituracion.aprobado_sponsor and
                minuta_escrituracion.aprobado_notario
            ):
                minuta_escrituracion.minuta_aprobada = True
                minuta_escrituracion.save()
                asset = minuta_escrituracion.activo
                asset.estado_aprobacion = EstadoAprobacion.objects.get(codigo='MINUTA_ESCRITURACION_APROBADA')
                asset.save()




                