from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from apps.asset.forms.fideicomiso_form import FideicomisoForm
from apps.asset.models import ActivoInversion, EstadoAprobacion, FeedbackMinutaEscrituracion, Fideicomiso, MinutaEscrituracion
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.views.generic import View, ListView, DetailView

from django.db.models import Q

from apps.notaria.forms.asset_form import NuevaEscrituraActivoForm



@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('asset.view_activoinversion', raise_exception=True), name='dispatch')
class ListAssetNotariaView(ListView):
    template_name = 'asset/asset_list.html'
    url_name = 'asset-notaria-list'
    model = ActivoInversion
    paginate_by = 25

    def get_queryset(self):
        filter_list = self.request.GET.getlist('filter')
        filters = Q()

        user = self.request.user
        if any(group.name in ["NOTARIO"] for group in user.groups.all()):
            queryset =ActivoInversion.objects.filter(estado_aprobacion__paso__gt=6)
        else:
            queryset =ActivoInversion.objects.none()
            
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'codigo__icontains',
                    'nombre__icontains',
                    'sponsor__company_name__icontains',
                    'propietario__email__icontains'
                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})

        queryset = queryset.filter(filters).order_by('-pk')
        filter_verified = self.request.GET.get('verified')

        if not (filter_verified == '' or filter_verified == None):
            queryset = queryset.filter(estado_aprobacion__id=filter_verified)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_obj = {
            'value': [],
            'url': ''
        }

        filter_list = self.request.GET.getlist('filter')
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                filter_obj['value'].append(
                    filter
                )
                filter_obj['url'] += '&filter={}'.format(filter)

        filter_verified = self.request.GET.get('verified')
        if not (filter_verified == '' or filter_verified == None):
            filter_obj['filter_verified'] = filter_verified
            filter_obj['url'] += '&verified={}'.format(filter_verified)
        context['filter_verified'] = filter_verified
        context['filter_obj'] = filter_obj
        context['estados_aprobacion'] = EstadoAprobacion.objects.all()
        context['nav_assets'] = True

        paginator = context.get('paginator')
        num_pages = paginator.num_pages
        current_page = context.get('page_obj')
        page_no = current_page.number

        if num_pages <= 11 or page_no <= 6:  # case 1 and 2
            pages = [x for x in range(1, min(num_pages + 1, 12))]
        elif page_no > num_pages - 6:  # case 4
            pages = [x for x in range(num_pages - 10, num_pages + 1)]
        else:  # case 3
            pages = [x for x in range(page_no - 5, page_no + 6)]

        context.update({'pages': pages})
        return context
    
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('asset.view_activoinversion', raise_exception=True), name='dispatch')
class DetailAssetNotariaView(DetailView):
    template_name = 'asset/asset_detail.html'
    url_name = 'asset-notaria-detail'
    model = ActivoInversion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if Fideicomiso.objects.filter(activo=self.object).exists():
            fideicomiso = Fideicomiso.objects.get(activo=self.object)
        else:
            fideicomiso = None

        if MinutaEscrituracion.objects.filter(activo=self.object).exists():
            minuta = MinutaEscrituracion.objects.get(activo=self.object)
            minuta_messages = FeedbackMinutaEscrituracion.objects.filter(minuta=minuta)

        else:
            minuta = None
            minuta_messages = None
        
        if self.object.nueva_escritura:
            print("Todo bien ya tiene Nueva escritura")
        else:
            print("Pailas no tiene escritura toca mandar form")
            context['form_escritura'] = NuevaEscrituraActivoForm

        context['fideicomiso'] = fideicomiso
        context['minuta'] = minuta
        context['minuta_feedback'] = minuta_messages
        context['nav_assets'] = True

        return context


# Endpoint que aprueba la minuta de escrituracion por el Notario

def MinutaEscrituracionApprovedNotaria(request):
    if request.method == 'POST':
        notario = request.user
        print(" MinutaEscrituracionApprovedNotariaEl usuario es : ", notario)
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        minuta_escrituracion = MinutaEscrituracion.objects.get(activo=update_activo)
        minuta_escrituracion.aprobado_notario = True
        minuta_escrituracion.save()
        update_activo.notaria = notario.notaria
        update_activo.save()

        if (minuta_escrituracion.aprobado_fiducia and 
            minuta_escrituracion.aprobado_propietario and
            minuta_escrituracion.aprobado_notario ):
            minuta_escrituracion.minuta_aprobada = True
            minuta_escrituracion.save()
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo='MINUTA_ESCRITURACION_APROBADA')
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
    
# Enpoint que envia mensajes del sobre la MinutaEscrituracion del notario
def MinutaEscrituracionNotarioMessage(request):
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
    
    #EndPoint que Permite a la Notaria empezar el proceso de Nueva escritura

def TramitarNuevaEscritura(request):
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        #Segundo  caso paso 2.1 al 2.2 Visto Bueno del AdminDevise le escribe al Sponsor algo falta
        if update_activo.estado_aprobacion.codigo =="MINUTA_ESCRITURACION_APROBADA" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="EN_REVISION_POR_NOTARIA")
            update_activo.save()
            response = {
                    'status': 'success',
                    'title': 'Activo Actualizado',
                    'message': 'Queda a la espera de la constitucion de la nueva escritura'
                }
            return JsonResponse(response)
        else:
            JsonResponse({
                    'status': 'error',
                    'title': 'No existe el estado aprobacion para el activo',
                })
    else:
        response = {
                    'status': 'error',
                    'title': 'Not valid method',
                }
        return JsonResponse(response)
    
@login_required
def UploadNotariaEscritura(request, *args, **kwargs):
    if request.method == 'POST' and request.FILES.get('escritura'):
        activo = get_object_or_404(ActivoInversion, pk=request.POST.get('id_activo'))
        activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="NUEVA_ESCRITURA_TRAMITADA")
        activo.nueva_escritura = request.FILES.get('escritura')
        activo.save()
        print("Guardada la nueva escritura: ", activo)
        
        return JsonResponse(
            {
                'status': 'success',
                'title': 'Documento Cargado exitosamente',
                'message': 'Ha sido actualizada la Nueva escritura del activo'
            }
        )
    return JsonResponse({'error': 'Se esperaba una solicitud POST con un archivo'})
