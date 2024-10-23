from django.forms import ValidationError
from requests import Response
from apps.user.models import User, Group
from apps.sponsor_company.models import SponsorCompany
from ..models import ActivoInversion, EstadoAprobacion, TipoProyecto, Categoria, FeedbackActivoInversion
from ..serializers.serializers_activo import (CreateActivoSerializer, TipoProyectoSerializer,
                        UpdateActivoSerializer, CategoriaSerializer,
                        ListActivoSerializer,
                        CreateDocumentalActivoSerializer,UpdateDocumentalActivoSerializer,
                        #Aprobacion del sponsor
                        RetrieveActivoSerializer, FeedbackActivoInversionCreateSerializer, ApprovedActivoSerializer,
                        ListFeedbackActivoInversion
                        )
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils.translation import ugettext as _

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from rest_framework import status

from rest_framework.exceptions import PermissionDenied



@permission_classes([IsAuthenticated])
class ListTipoProyectoView(generics.ListAPIView):
    queryset = TipoProyecto.objects.all()
    serializer_class = TipoProyectoSerializer
    pagination_class = None

@permission_classes([IsAuthenticated])
class ListCategoriaView(generics.ListAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    pagination_class = None

@permission_classes([IsAuthenticated])
class CreateAssetView(generics.CreateAPIView):
    serializer_class = CreateActivoSerializer
    queryset = ActivoInversion.objects.all()

    def perform_create(self, serializer):
        serializer.save(propietario=self.request.user)



@permission_classes([IsAuthenticated])
class UpdateAssetView(generics.UpdateAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = UpdateActivoSerializer

@permission_classes([IsAuthenticated])
class ListAssetView(generics.ListAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = ListActivoSerializer

@permission_classes([IsAuthenticated])
class ListOwnAssetView(generics.ListAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = ListActivoSerializer

    def get_queryset(self):
        user = self.request.user
        return ActivoInversion.objects.filter(propietario=user)
    
@permission_classes([IsAuthenticated])
class ListAssetApproveView(generics.ListAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = ListActivoSerializer

    def get_queryset(self):
        tipo = self.request.query_params.get('tipo', None)
        if tipo == "0":
            return ActivoInversion.objects.filter(estado_aprobacion=34,notaria_id= not None)
        return ActivoInversion.objects.filter(estado_aprobacion=34,notaria_id= not None,tipo_proyecto_id=tipo)
    
@permission_classes([IsAuthenticated])
class ListAssetTipoProyecto(generics.ListAPIView):
    queryset = TipoProyecto.objects.all()
    serializer_class = TipoProyectoSerializer
    pagination_class = None

    def get_queryset(self):
        id = self.request.query_params.get('tipo', None)
        print("get_tipo_proyecto_nombre",id)
        return TipoProyecto.objects.filter(id=id)


#   MANAGE DOCUMENTAL INFORMATION

@permission_classes([IsAuthenticated])
class CreateDocumentalAssetView(generics.UpdateAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = CreateDocumentalActivoSerializer

@permission_classes([IsAuthenticated])
class UpdateDocumentalAssetView(generics.UpdateAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = UpdateDocumentalActivoSerializer

# 2Do paso Aprobacion del sponsor y Feedback Sponsor-Propietario
@permission_classes([IsAuthenticated])
class ListSponsorToApprvedAssetView(generics.ListAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = ListActivoSerializer

    def get_queryset(self):
        user = self.request.user
        if SponsorCompany.objects.filter(user = user).exists():
            return ActivoInversion.objects.filter(sponsor=SponsorCompany.objects.get(user = user)).filter(estado_aprobacion__paso__gte=1, estado_aprobacion__paso__lte=2)
        else:
            return ActivoInversion.objects.none()

@permission_classes([IsAuthenticated])
class ListSponsorAssetView(generics.ListAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = ListActivoSerializer

    def get_queryset(self):
        user = self.request.user
        if SponsorCompany.objects.filter(user = user).exists():
            return ActivoInversion.objects.filter(sponsor=SponsorCompany.objects.get(user=user)).filter(estado_aprobacion__paso__gte=2)
        else:
            return ActivoInversion.objects.none()
    
@permission_classes([IsAuthenticated])
class RetrieveAssetView(generics.RetrieveAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = RetrieveActivoSerializer



@permission_classes([IsAuthenticated])
class ValidateAssetSponsorView(generics.UpdateAPIView):
    ''' Cuando el propietario decida entonces llega aca y cambia de estado a espera de validar por Sponsor'''
    queryset = ActivoInversion.objects.all()
    serializer_class = ApprovedActivoSerializer

    def perform_update(self, serializer):
        serializer.save(
            estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_SIN_APROBAR_SPONSOR"),
            )
        
@permission_classes([IsAuthenticated])
class FeedbackActivoCreate(generics.CreateAPIView):
    serializer_class = FeedbackActivoInversionCreateSerializer
    queryset = FeedbackActivoInversion.objects.all()

    def perform_create(self, serializer):
        validated_data =self.request.data
        update_activo = ActivoInversion.objects.get(id=validated_data.get('activo'))
        #Primer caso paso 1 al 2 Visto Bueno del sponsor le escribe al propietario algo falta
        if update_activo.estado_aprobacion.codigo =="ACTIVO_SIN_APROBAR_SPONSOR" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="PENDIENTE_RESPUESTA_PROPIETARIO")
            update_activo.save()
            serializer.save(
                remitente = self.request.user,
                destinatario = update_activo.propietario,
                estado_actual = "PENDIENTE_RESPUESTA_PROPIETARIO",
                )
        #El Propietario responde al Sponsor puede posiblemente enviar un archivo    
        elif update_activo.estado_aprobacion.codigo =="PENDIENTE_RESPUESTA_PROPIETARIO" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_SIN_APROBAR_SPONSOR")
            update_activo.save()
            serializer.save(
                remitente = self.request.user,
                destinatario = update_activo.sponsor.user, #al usuario de la compañia sponsor
                estado_actual = "ACTIVO_SIN_APROBAR_SPONSOR",
                )
        #Devise le envia un mensaje al Sponsor si archivo   
        
        elif update_activo.estado_aprobacion.codigo =="ACTIVO_APROBADO_SPONSOR" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="PENDIENTE_RESPUESTA_SPONSOR")
            update_activo.save()
            serializer.save(
                remitente = self.request.user,
                destinatario = update_activo.sponsor.user, #al usuario de la compañia sponsor
                estado_actual = "PENDIENTE_RESPUESTA_SPONSOR",
                )
        #El Sponsor le responde a Devise y puede posiblemente enviar un archivo    
        elif update_activo.estado_aprobacion.codigo =="PENDIENTE_RESPUESTA_SPONSOR" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_APROBADO_SPONSOR")
            update_activo.save()
            ultimo_mensaje = FeedbackActivoInversion.objects.filter(activo=update_activo)[0]
            print("Ultimo mensaje remitente ", ultimo_mensaje)
            print("Le envio a ", ultimo_mensaje.remitente)
            serializer.save(
                remitente = self.request.user,
                destinatario = ultimo_mensaje.remitente,
                estado_actual = "ACTIVO_APROBADO_SPONSOR",
                )
        else:
            raise PermissionDenied("No se puede enviar mensajes de validación en el estado actual del Activo")


            

@permission_classes([IsAuthenticated])
class ApprovedSponsorAssetView(generics.UpdateAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = ApprovedActivoSerializer

    def perform_update(self, serializer):
        # Verificar si el usuario pertenece a alguno de los grupos permitidos
        allowed_groups = ["SPONSOR", "ADMINISTRADOR"]
        user = self.request.user
        if any(group.name in allowed_groups for group in user.groups.all()):
            serializer.save(
                estado_aprobacion=EstadoAprobacion.objects.get(codigo="ACTIVO_APROBADO_SPONSOR")
            )
        else:
           # Si el usuario no pertenece a ninguno de los grupos permitidos, retornar un error 403 (Forbidden)
            raise PermissionDenied("No tienes permisos debes ser Sponsor o Administrador")
        

@permission_classes([IsAuthenticated])
class ListMessagesAssetView(generics.ListAPIView):
    queryset = FeedbackActivoInversion.objects.all()
    serializer_class = ListFeedbackActivoInversion

    def get_queryset(self):
        asset_model = ActivoInversion.objects.get(id=self.kwargs.get('pk'))
        queryset = FeedbackActivoInversion.objects.filter(activo=asset_model)
        queryset_final = queryset.filter(
        Q(estado_actual='ACTIVO_SIN_APROBAR_SPONSOR') |
        Q(estado_actual='PENDIENTE_RESPUESTA_PROPIETARIO') 
        )
        return queryset_final

            
@permission_classes([IsAuthenticated])
class ApprovedAdminDeviseAssetView(generics.UpdateAPIView):
    queryset = ActivoInversion.objects.all()
    serializer_class = ApprovedActivoSerializer

    def perform_update(self, serializer):
        # Verificar si el usuario pertenece a alguno de los grupos permitidos
        allowed_groups = ["ADMINISTRADOR"]
        user = self.request.user
        if any(group.name in allowed_groups for group in user.groups.all()):
            serializer.save(
                estado_aprobacion=EstadoAprobacion.objects.get(codigo="ACTIVO_APROBADO_DEVISE")
            )
        else:
            # Si el usuario no pertenece a ninguno de los grupos permitidos, retornar un error 403 (Forbidden)
            raise PermissionDenied("No tienes permisos debes ser Administrador")
            
        

# Enpoint que envia mensajes del admin al sponsor
def SendAdminMsjSponsor(request):
    if request.method == 'POST':
        print(">>VALIDATED request : ", request.POST)
        print(">>VALIDATED DATA : ", request.POST.get('mensaje'))
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        #Segundo  caso paso 2.1 al 2.2 Visto Bueno del AdminDevise le escribe al Sponsor algo falta
        if update_activo.estado_aprobacion.codigo =="ACTIVO_APROBADO_SPONSOR" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="PENDIENTE_RESPUESTA_SPONSOR")
            update_activo.save()
            mensaje = FeedbackActivoInversion.objects.create(
                activo = update_activo,
                mensaje = request.POST.get('mensaje'),
                remitente = request.user,
                destinatario = update_activo.sponsor.user, #al usuario de la compañia sponsor
                estado_actual = "PENDIENTE_RESPUESTA_SPONSOR",
                )
            # print("creado el msj :", mensaje)
            response = {
                    'status': 'success',
                    'title': _('Activo Actualizado'),
                    'message': _('Se ha enviado el mensaje al sponsor')
                }
            return JsonResponse(response)
        
        
# Endpoint que aprueba el admin Devise el activo

def ApprovedAssetAdmin(request):
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        #Segundo  caso paso 2.1 al 2.2 Visto Bueno del AdminDevise le escribe al Sponsor algo falta
        if update_activo.estado_aprobacion.codigo =="ACTIVO_APROBADO_SPONSOR" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_APROBADO_DEVISE")
            update_activo.save()
            response = {
                    'status': 'success',
                    'title': 'Activo Actualizado',
                    'message': 'Queda a la espera de la constitucion del fideicomiso'
                }
            return JsonResponse(response)
        else:
            JsonResponse({
                    'status': 'error',
                    'title': 'Unsoprted estado aprobacion',
                })
    else:
        response = {
                    'status': 'error',
                    'title': 'Not valid method',
                }
        return JsonResponse(response)

# ENDPOINT mensajes entre  SPONSOR Y EL ADMIN

@permission_classes([IsAuthenticated])
class ListMessagesSponsorDeviseAssetView(generics.ListAPIView):
    queryset = FeedbackActivoInversion.objects.all()
    serializer_class = ListFeedbackActivoInversion

    def get_queryset(self):
        asset_model = ActivoInversion.objects.get(id=self.kwargs.get('pk'))
        queryset = FeedbackActivoInversion.objects.filter(activo=asset_model)
        queryset_final = queryset.filter(
        Q(estado_actual='ACTIVO_APROBADO_SPONSOR') |
        Q(estado_actual='PENDIENTE_RESPUESTA_SPONSOR') 
        )
        return queryset_final

# Endpoint que aprueba el admin Devise el activo

def ApprovedAssetFiducia(request):
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        #Segundo  caso paso 2.1 al 2.2 Visto Bueno del AdminDevise le escribe al Sponsor algo falta
        if update_activo.estado_aprobacion.codigo == "ACTIVO_APROBADO_DEVISE" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo='ACTIVO_APROBADO_FIDUCIA')
            update_activo.save()
            response = {
                    'status': 'success',
                    'title': _('Activo Actualizado'),
                    'message': _('Recuerda cargar la constitucion del fideicomiso')
                }
            return JsonResponse(response)
        
# Endpoint que Valida la activacion del encargo Fiduciario para pasar a KPI

def FiduciaApprovedEncargoFiduciario(request):
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        #Segundo  caso paso 2.1 al 2.2 Visto Bueno del AdminDevise le escribe al Sponsor algo falta
        if update_activo.estado_aprobacion.codigo == "NUEVO_CERTIFICADO_TRADICION_Y_LIBERTAD" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo='ACTIVO_EN_CALCULO_KPI_SPONSOR')
            update_activo.save()
            response = {
                    'status': 'success',
                    'title': _('Activo Actualizado'),
                    'message': _('Queda en espera de los KPI del Sponsor')
                }
            return JsonResponse(response)