import json

import requests
from apps.user.models import User
from apps.sponsor_company.models import SponsorCompany
from apps.weetrust.models import AccessTokenWeetrust
from config.settings import WEETRUST_URL, WEETRUST_USER_ID
from ..models import ActivoInversion, FeedbackKPI, FeedbackMinutaEscrituracion, MinutaEscrituracion, Fideicomiso, TipoProyecto, Categoria, FeedbackActivoInversion, EstadoAprobacion
from apps.asset.forms.fideicomiso_form import FideicomisoUploadForm, FideicomisoForm
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.generic import View, ListView, DetailView
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator


from django.template.loader import get_template

from io import BytesIO
from xhtml2pdf import pisa
from import_export import fields, resources, widgets
import datetime as dt

from tempfile import NamedTemporaryFile
# =============================================================================
#                           IMPORT - EXPORT RESOURCE
# =============================================================================
class ActivoInversionResource(resources.ModelResource):
    def dehydrate_propietario(self, obj):
        # Return the name instead of the primary key
        if obj.propietario:
            return obj.propietario.email
        else:
            return ''
    def dehydrate_tipo_proyecto(self, obj):
        # Return the name instead of the primary key
        return obj.tipo_proyecto.nombre
    def dehydrate_categoria(self, obj):
        # Return the name instead of the primary key
        if obj.categoria:
            return obj.categoria.nombre
        else:
            return ''
    def dehydrate_sponsor(self, obj):
        # Return the name instead of the primary key
        if obj.sponsor:
            return obj.sponsor.company_name
        else:
            return ''
    def dehydrate_gerente_negocio(self, obj):
        # Return the name instead of the primary key
        if obj.gerente_negocio:
            return obj.gerente_negocio.email
        else:
            return ''
    class Meta:
        model = ActivoInversion
        fields = (
            'codigo',
            'propietario',
            'nombre',
            'tipo_proyecto',
            'dimension_m2',
            'ciudad',
            'direccion',
            'latitud',
            'longitud',
            'area_construida_m2',
            'area_gla_m2',
            'area_vendible_m2',
            'area_lote_m2',
            'ano_construccion',
            'categoria',
            'matricula_inmobiliaria',
            'cedula_catastral',
            'canon_arriendo',
            'valor_activo',
            'sponsor',
            'gerente_negocio',
        )
        export_order = (
            'codigo',
            'nombre',
        )



# =============================================================================
#                           BACKOFFICE RESOURCE
# =============================================================================

# Listar las propiedades Para aprobar

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('asset.view_activoinversion', raise_exception=True), name='dispatch')
class ListAdminAssetView(ListView):
    template_name = 'asset_list.html'
    url_name = 'asset-admin-list'
    model = ActivoInversion
    paginate_by = 25

    def get_queryset(self):
        filter_list = self.request.GET.getlist('filter')
        filters = Q()

        user = self.request.user
        if any(group.name in ["SPONSOR"] for group in user.groups.all()):
            queryset =ActivoInversion.objects.filter(estado_aprobacion__isnull=False)
        elif any(group.name in ["FIDUCIA"] for group in user.groups.all()):
            queryset =ActivoInversion.objects.filter(estado_aprobacion__paso__gt=2)
        elif any(group.name in ["NOTARIO"] for group in user.groups.all()):
            queryset =ActivoInversion.objects.filter(estado_aprobacion__paso__gt=6)
        elif any(group.name in ["ADMINISTRADOR"] for group in user.groups.all()):
            queryset =ActivoInversion.objects.all()
        else:
            print("Sin activos para mostrar")
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
# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('asset.view_activoinversion', raise_exception=True), name='dispatch')
class ListAdminAssetExportView(View):
    url_name = 'admin-asset-list-export'

    def _get_pdf_export(self, queryset, file_name):
        template = get_template('report/asset_list_export.html')
        context = {
            'user_report': self.request.user,
            'object_list': queryset,
            'current_scheme_host': self.request._current_scheme_host,
        }
        html  = template.render(context)
        result = BytesIO()

        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, debug=1)

        return result

    def _get_export_response(self, queryset, format='csv'):
        dataset = ActivoInversionResource().export(queryset)
        file_name = "Assets_{}".format(dt.datetime.now().strftime("%d-%m-%Y"))

        if (format == 'csv'):
            dataset_format = dataset.csv
            CONTENT_DISPOSITION = 'attachment; filename="{}.csv"'.format(file_name)
            CONTENT_TYPE = 'text/csv'

        elif (format == 'xls'):
            dataset_format = dataset.xls
            CONTENT_DISPOSITION = 'attachment; filename="{}.xls"'.format(file_name)
            CONTENT_TYPE = 'application/vnd.ms-excel'

        elif (format == 'xlsx'):
            dataset_format = dataset.xlsx
            CONTENT_DISPOSITION = 'attachment; filename="{}.xlsx"'.format(file_name)
            CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        elif (format == 'tsv'):
            dataset_format = dataset.tsv
            CONTENT_DISPOSITION = 'attachment; filename="{}.tsv"'.format(file_name)
            CONTENT_TYPE = 'text/tab-separated-values'

        elif (format == 'ods'):
            dataset_format = dataset.ods
            CONTENT_DISPOSITION = 'attachment; filename="{}.ods"'.format(file_name)
            CONTENT_TYPE = 'application/vnd.oasis.opendocument.spreadsheet'

        elif (format == 'json'):
            dataset_format = dataset.json
            CONTENT_DISPOSITION = 'attachment; filename="{}.json"'.format(file_name)
            CONTENT_TYPE = 'application/json'

        elif (format == 'yaml'):
            dataset_format = dataset.yaml
            CONTENT_DISPOSITION = 'attachment; filename="{}.yaml"'.format(file_name)
            CONTENT_TYPE = 'text/yaml'

        elif (format == 'html'):
            dataset_format = dataset.html
            CONTENT_DISPOSITION = 'attachment; filename="{}.html"'.format(file_name)
            CONTENT_TYPE = 'text/html'

        elif (format == 'pdf'):
            result = self._get_pdf_export(queryset, file_name)
            CONTENT_DISPOSITION = 'attachment; filename="{}.pdf"'.format(file_name)
            CONTENT_TYPE = 'application/pdf'

            response = HttpResponse(content_type=CONTENT_TYPE)
            response['Content-Disposition'] = CONTENT_DISPOSITION
            response.content = result.getvalue()
            return response

        else:
            dataset_format = dataset.csv
            CONTENT_DISPOSITION = 'attachment; filename="_{}.csv"'.format(filename)
            CONTENT_TYPE = 'text/csv'

        response = HttpResponse(dataset_format, content_type=CONTENT_TYPE)
        response['Content-Disposition'] = CONTENT_DISPOSITION
        return response


    def post(self, request, *args, **kwargs):
        format_file_available = {
            '0': 'csv',
            '1': 'xls',
            '2': 'xlsx',
            '3': 'pdf',
            # '4': 'ods',
            # '5': 'json',
            # '6': 'yaml',
            # '7': 'html',
        }

        id_seleccion = request.POST.getlist('_action_selection')
        action = request.POST.get('_action')
        selected_all_elements = request.POST.get('selected-all-elements')
        format_file_id = request.POST.get('_format_file')
        try:
            format_file = format_file_available[format_file_id]
        except:
            format_file = format_file_available['0']

        if (selected_all_elements == '1' or selected_all_elements == 1):
            queryset = ActivoInversion.objects.filter(filters).order_by('-pk')
            filter_verified = request.POST.get('filter_verified')
            if not (filter_verified == '' or filter_verified == None):
                queryset = queryset.filter(estado_aprobacion=filter_verified)

            filter_list = request.POST.getlist('filter')
            filters = Q()
            if ( filter_list and filter_list != ''):
                for filter in filter_list:
                    fields = [
                        'codigo__icontains',
                        'nombre__icontains',
                        'sponsor__company_name__icontains',
                        'propietario__email__icontains'
                    ]

                    for str_field in fields:
                        filters |= Q(**{str_field: filter})

                queryset = queryset.filter(filters)

        else:
            if not (id_seleccion == '' or id_seleccion == None):
                queryset = ActivoInversion.objects.filter(id__in=id_seleccion).order_by('-pk')
            else:
                queryset = ActivoInversion.objects.none()

        response = self._get_export_response(queryset, format=format_file)

        return response


# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('asset.view_activoinversion', raise_exception=True), name='dispatch')
class DetailAdminAssetView(DetailView):
    template_name = 'asset_detail.html'
    url_name = 'asset-detail'
    model = ActivoInversion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if Fideicomiso.objects.filter(activo=self.object).exists():
            fideicomiso = Fideicomiso.objects.get(activo=self.object)
            context['fideicomiso_form'] = FideicomisoForm(instance=fideicomiso)
        else:
            fideicomiso = None
            context['fideicomiso_upload'] = FideicomisoUploadForm(activo=self.object) #Paso filtro de los que son de esa fiducia

        if MinutaEscrituracion.objects.filter(activo=self.object).exists():
            minuta = MinutaEscrituracion.objects.get(activo=self.object)
            minuta_messages = FeedbackMinutaEscrituracion.objects.filter(minuta=minuta)
        else:
            minuta = None
            minuta_messages = None

        context['chat'] = FeedbackActivoInversion.objects.filter(activo=self.object)
        context['fideicomiso'] = fideicomiso
        context['minuta'] = minuta
        context['minuta_feedback'] = minuta_messages
        context['kpi_feedback'] = FeedbackKPI.objects.filter(activo=self.object)

        context['nav_assets'] = True
        return context

@login_required
def UploadFiduciaDocument(request, *args, **kwargs):
    if request.method == 'POST' and request.FILES.get('fideicomiso'):
        activo = get_object_or_404(ActivoInversion, pk=request.POST.get('id_activo'))
        activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_FIDEICOMISO_CARGADO")
        activo.gerente_negocio = User.objects.get(pk=request.POST.get('id_gerente_negocio'))
        activo.save()
        print("guardioe el activo")
        fiducia_user = User.objects.get(pk=request.POST.get('id_gerente_negocio'))
        # print("REQUEST FILES: ", request.FILES)
        documento = Fideicomiso(
            activo = activo,
            gerente_negocio = fiducia_user,
            fideicomiso = request.FILES.get('fideicomiso'),
            email_fiducia = fiducia_user.email,
            name_fiducia = fiducia_user.get_full_name(),
            email_devise = 'fastway0102@hotmail.com', #OJO ACA <<<<<< van fijos????
            name_devise = 'Administrador Devise Andres Hernandez',
            email_sponsor = activo.sponsor.user.email,
            name_sponsor = activo.sponsor.user.get_full_name() ,
            email_propietario = activo.propietario.email,
            name_propietario = activo.propietario.get_full_name(),
        )
        documento.save()
        return JsonResponse(
            {
                'status': 'success',
                'title': 'Documento Cargado exitosamente',
                'message': 'Revise los firmantes y proceda a solicitar las firmas'
            }
        )
    return JsonResponse({'error': 'Se esperaba una solicitud POST con un archivo'})

@login_required
def SendToSignFiduciaDocument(request, *args, **kwargs):
    if request.method == 'POST' and request.POST.get('id_fideicomiso'):
        print("Mando a firmar el fideicomiso del activo", request.POST)
        fideicomiso_model = get_object_or_404(Fideicomiso, pk =request.POST.get('id_fideicomiso'))
        fideicomiso_model.email_fiducia = request.POST.get('id_email_fiducia')
        fideicomiso_model.name_fiducia = request.POST.get('id_name_fiducia') 
        fideicomiso_model.email_devise = request.POST.get('id_email_devise') 
        fideicomiso_model.name_devise = request.POST.get('id_name_devise') 
        fideicomiso_model.email_sponsor = request.POST.get('id_email_sponsor') 
        fideicomiso_model.name_sponsor = request.POST.get('id_name_sponsor') 
        fideicomiso_model.email_propietario = request.POST.get('id_email_propietario') 
        fideicomiso_model.name_propietario = request.POST.get('id_name_propietario') 
        fideicomiso_model.enviado_weetrust = True
        fideicomiso_model.save()
        print("Cargando Documento al servidor")
        #Obtain Weetrust Token
        if AccessTokenWeetrust.objects.all().exists():
            token_model = AccessTokenWeetrust.objects.latest()
        else:
            token_model = AccessTokenWeetrust.obtain_new_token()

        if token_model.obtain_minutes() > 4.5 :
            token_model = AccessTokenWeetrust.obtain_new_token()
            token_value = token_model.value
        else:
            token_value = token_model.value

        headers = {
                    'user-id': WEETRUST_USER_ID,
                    'token': token_value,
                    }
                
        data = {
            'documentSignType': 'ELECTRONIC_SIGNATURE',
            'country': 'Colombia',
            'language': 'es',
            'position': 'geolocation',
        }

        url_create_document  = WEETRUST_URL+'documents'

        with NamedTemporaryFile(delete=True) as temp_file:
            temp_file.write(fideicomiso_model.fideicomiso.read())
            temp_file.seek(0)
            files = {
                'document': (fideicomiso_model.fideicomiso.name, temp_file),
            }

            # Realiza la solicitud POST con los encabezados y el cuerpo
            response = requests.post(url_create_document, headers=headers, data=data, files=files) #ojo es DATA

        # Verifica si la solicitud de subir documento fue exitosa
        if response.status_code == 200:
            result = response.json()
            print("Documento cargado exitosamente")
            print("RESULTADO CARGE weetrust DOCUMENT:\n", result)
            fideicomiso_model.response_weetrust = result
            fideicomiso_model.id_weetrust_document = result['responseData']['documentID']
            fideicomiso_model.save()
            print("FIN___________________\n")

            #Update Document signs 
            url_put_signs = WEETRUST_URL+'documents/signatory'
            headers = {
                        'user-id': WEETRUST_USER_ID,
                        'token': token_value,
                        }
                    
            data = {
                'documentID': fideicomiso_model.id_weetrust_document ,
                "nickname": fideicomiso_model.activo.codigo,
                "message": f'Cordial saludo Devise le solicita por favor firmar el documento correspondiente al fideicomiso de registro del activo: {fideicomiso_model.activo.nombre}',
                "title": "Firma constitución fideicomiso",
                "signatory": [
                    {
                        "emailID": fideicomiso_model.email_fiducia,
                        "name": fideicomiso_model.name_fiducia,
                        "forceBiometric":{
                            "forcedBackgroundCheck":False,
                            "forcedFaceID":True,
                            "forcedID":True,
                            "forcedPhotoID":False,
                        }
                    },
                    {
                        "emailID": fideicomiso_model.email_devise,
                        "name": fideicomiso_model.name_devise,
                        "forceBiometric":{
                            "forcedBackgroundCheck":False,
                            "forcedFaceID":True,
                            "forcedID":True,
                            "forcedPhotoID":False,
                        }
                    },
                    {
                        "emailID": fideicomiso_model.email_sponsor,
                        "name": fideicomiso_model.name_sponsor,
                        "forceBiometric":{
                            "forcedBackgroundCheck":False,
                            "forcedFaceID":True,
                            "forcedID":True,
                            "forcedPhotoID":False,
                        }
                    },
                    {
                        "emailID": fideicomiso_model.email_propietario,
                        "name": fideicomiso_model.name_propietario,
                        "forceBiometric":{
                            "forcedBackgroundCheck":False,
                            "forcedFaceID":True,
                            "forcedID":True,
                            "forcedPhotoID":False,
                        }
                    }
                ],
                "sharedWith": [
                    {
                        "emailID": "deviseadmon@gmail.com"
                    }
                ]
            }
            
            response = requests.put(url_put_signs, headers=headers, json=data) #Verificar es JSON
            # Verifica si la solicitud de actualizar los datos de los firmantes al documento fue exitosa

            if response.status_code == 200:
                result = response.json()
                print("Documento actualizado exitosamente OJO ACA CONTINUAR")
                print(result)
                fideicomiso_model.response_weetrust = result
                fideicomiso_model.save()
                activo = fideicomiso_model.activo
                activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_FIDEICOMISO_TRAMITE_FIRMA")
                activo.save()

                firmantes = result['responseData']['signatory']
                print("firmantes: ", firmantes)

                for firmante in firmantes:
                    correo = firmante['emailID']
                    print("Correo ", correo)
                    if correo == fideicomiso_model.email_fiducia:
                        fideicomiso_model.fiducia_signing_url = firmante['signing']['url']
                        fideicomiso_model.save()
                    if correo == fideicomiso_model.email_devise:
                        fideicomiso_model.devise_signing_url = firmante['signing']['url']
                        fideicomiso_model.save()
                    if correo == fideicomiso_model.email_sponsor:
                        fideicomiso_model.sponsor_signing_url = firmante['signing']['url']
                        fideicomiso_model.save()
                    if correo == fideicomiso_model.email_propietario:
                        fideicomiso_model.propietario_signing_url = firmante['signing']['url']
                        fideicomiso_model.save()

                return JsonResponse(
                {
                    'status': 'success',
                    'title': 'Documento Cargado exitosamente',
                    'message': 'Se enviaron correos a los destinatarios'
                })
            else:
                print(f"Error en la solicitud: {response.status_code}")
                print(response.text)
                fideicomiso_model.delete()
                print("Borrando Fiducia model")
                return JsonResponse(
                    {
                        'status': 'failed',
                        'title': 'Error Actualizando firmas!',
                        'message': response.text,
                    })
        else:
            print(f"Error en la solicitud: {response.status_code}")
            print(response.text)
            fideicomiso_model.delete()
            print("Borrando Fiducia model")
            return JsonResponse(
                {
                    'status': 'failed',
                    'title': 'Error en red Cargando documento!',
                    'message': response.text,
                })
        
    return JsonResponse({'error': 'Se esperaba una solicitud POST con un archivo'})

@login_required
def RetrySignDocument(request, *args, **kwargs):
    if request.method == 'POST':
        print("Solicitando la firma de ", request.POST.get('biometricLogID'))
        fideicomiso = get_object_or_404(Fideicomiso, pk=request.POST.get('id_fideicomiso'))
        biometricLogID = request.POST.get('biometricLogID')
        print("Solicitando del fideicomiso: ", fideicomiso.pk)
        #Obtain Weetrust Token
        token_model = AccessTokenWeetrust.objects.latest()
        if token_model.obtain_minutes() > 4.5 :
            token_model = AccessTokenWeetrust.obtain_new_token()
            token_value = token_model.value
        else:
            token_value = token_model.value
        #Update Document signs 
        url_retry_biometric = WEETRUST_URL+'documents/retry-biometric'
        headers = {
                    'Content-Type': 'application/json',
                    'user-id': WEETRUST_USER_ID,
                    'token': token_value,
                    }
                
        data = {
            'documentID': fideicomiso.id_weetrust_document,
            'biometricLogID': biometricLogID,
            'action': 'biometricRetry'
        }
        print("haciendo la solicitud con Data: ", data)
        response = requests.put(url_retry_biometric, headers=headers, json=data) #OJO es JSON

        if response.status_code == 200:
                result = response.json()
                print("Documento Con firma solicitada de nuevo exitosamente")
                print(result)
                if fideicomiso.fiducia_sesion == biometricLogID:
                    fideicomiso.fiducia_json = {}
                    fideicomiso.fiducia_signing_url = None

                elif fideicomiso.devise_sesion == biometricLogID:
                    fideicomiso.devise_json = {}
                    fideicomiso.devise_signing_url = None

                elif fideicomiso.sponsor_sesion == biometricLogID:
                    fideicomiso.sponsor_json = {}
                    fideicomiso.sponsor_signing_url = None

                elif fideicomiso.propietario_sesion == biometricLogID:
                    fideicomiso.propietario_json = {}
                    fideicomiso.propietario_signing_url = None

                
                fideicomiso.save()
                return JsonResponse(
                {
                    'status': 'success',
                    'title': 'Firma Solicitada Exitosamente',
                    'message': 'Se envio correo al destinatario'
                })
        else:
            print(f"Error en la solicitud: {response.status_code}")
            result = response.json()
            
            return JsonResponse(
                {
                    'status': 'failed',
                    'title': 'Error Actualizando firmas!',
                    'message': result["message"],
                })

       
    return JsonResponse({'error': 'Se esperaba una solicitud POST con un archivo'})

