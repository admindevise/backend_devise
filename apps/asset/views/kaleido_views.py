

import json
from django.http import JsonResponse
import requests
from apps.asset.models import ActivoInversion, EstadoAprobacion
from config.settings import ENVIRONMENT_ID, NODE_ID, PASSWORD, USERNAME, ZONE_DOMAIN, SC_WALLET_TYPE1,SC_WALLET_TYPE2,SC_WALLET_TYPE2, KLD_SYNC, USER_ACCOUNTS,GATEWAY_API
from django.utils.translation import ugettext as _
from apps.kaleido.views import kaleido_views

import codecs

def UpdateSmartcontractAsset(request):
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        #Segundo  caso paso 2.1 al 2.2 Visto Bueno del AdminDevise le escribe al Sponsor algo falta
        
        if update_activo.estado_aprobacion.codigo =="ACTIVO_KPI_APROBADO_DEVISE" :
            update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo="CONTRATO_CONFIGURADO_KALEIDO")
            update_activo.id_smartcontract = request.POST.get('idSmartContract')
            update_activo.save()
            response = {
                    'status': 'success',
                    'title': 'Activo Actualizado',
                    'message': 'Contrato actualizado'
                }
            return JsonResponse(response)
        else:
            return JsonResponse({
                    'status': 'error',
                    'title': 'Unsoprted estado aprobacion',
                })
    else:
        response = {
                    'status': 'error',
                    'title': 'Not valid method',
                }
        return JsonResponse(response)
    
from requests.auth import HTTPBasicAuth

def ReadTokenSmartContract(request): #CUando el Smart contract existia ya podia consultar la información
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        id_smartcontract = update_activo.id_smartcontract
        #tomamos el id del contrato y consultammos la información
        command = 'totalSupply'
        url = f'https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{id_smartcontract}/{command}'
        print("Pegandole a URL: ", url)
        
        try:
            # Realiza la solicitud GET con autenticación básica
            response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))

            # Verifica si la solicitud fue exitosa (código de respuesta 200)
            if response.status_code == 200:
                # Si la solicitud fue exitosa, puedes procesar la respuesta aquí
                data = response.json()  # Si la respuesta es JSON
                print("La consulta trajo: ", data )

                return JsonResponse(data, safe=False)
            else:
                # Si la solicitud no fue exitosa, puedes manejar el error aquí
                return JsonResponse({"error": "No se pudo obtener la información"}, status=500)

        except requests.exceptions.RequestException as e:
            # Manejar excepciones de solicitud, como conexiones fallidas
            return JsonResponse({"error": f"Error de solicitud: {str(e)}"}, status=500)

    else:
        response = {
                    'status': 'error',
                    'title': 'Not valid method',
                }
        return JsonResponse(response)

#TRAEMOS LOS PARAMETROS DEL SETTINGS Y SE SOLICITA LA CREACION DEL CONTRATO SOBRE LA BASE QUE FUE CONFIGURADA CON ESAS CREDENCIALES


def CreateSmartContractToken(request):
    
    if request.method == 'POST':
        update_activo = ActivoInversion.objects.get(id=request.POST.get('activo'))
        nombre = codecs.decode(update_activo.nombre, 'raw_unicode_escape')
        nombre = nombre.encode('latin1').decode('utf-8')
        #tomamos el id del contrato y consultammos la información 
        
        #url = f'https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/gateways/tokenizationdev?kld-from={KLD_FROM}&kld-sync={KLD_SYNC}'
        url = f'https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/gateways/{GATEWAY_API}?kld-from={USER_ACCOUNTS}&kld-sync={KLD_SYNC}'
        print("Pegandole a URL: ", url)
        tokens_totales =  update_activo.tokens_totales
        if not tokens_totales:
            errResponse = {
                    'status': 'error',
                    'title': _('Error al crear el SmartContract'),
                    'message': _('Tokens totales requerido*'),
                    "status_code":400
                }
            return errResponse
        data = {
            #'initialSupply': update_activo.tokens_totales,# 1. Ya podemos meter más datos?2tipo JSON o 30Fijos ¿que variables necesito inmediatas?
            #'landlord': LANDLORD, #Ojo toca cambiarlo ¿como me van a dar la wallet del dueño? 2. ¿Como vamos a asignar los Token al dueño?
            'name': nombre,
            'symbol': update_activo.codigo,
        }
        #Hay que fortalecer la creacion del SMART CONTRACT (Debe ser capaz de guardar la data del ActivoInversion-HIstorico de transferencias token y como se las transefrencias)
        try:
            data_json = json.dumps(data)
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), data=data_json, headers=headers)

            # Verifica si la solicitud fue exitosa (código de respuesta 200)
            if response.status_code == 200:
                # Si la solicitud fue exitosa, puedes procesar la respuesta aquí
                #SC_WALLET_TYPE2 = "tokens"
                
                keleido_response_wallet1 = kaleido_views.createSmartContractWalletToken(update_activo,SC_WALLET_TYPE1)
                print("keleido_response_wallet1 trajo: ", keleido_response_wallet1 )
                #SC_WALLET_TYPE2 = "rendimientos"
                keleido_response_wallet2 = kaleido_views.createSmartContractWalletToken(update_activo,SC_WALLET_TYPE2)
                print("keleido_response_wallet2 trajo: ", keleido_response_wallet2 )
                # Creación del Smart Contract 2
                keleido_response = kaleido_views.createSmartContractERC20(update_activo,USER_ACCOUNTS)
                print("keleido_response trajo: ", keleido_response )
                # Fin Creación del Smart Contract 2

                data = response.json()  # Si la respuesta es JSON
                print("La peticion trajo: ", data )
                update_activo.metadata_smartcontract = data
                update_activo.id_smartcontract = data['contractAddress']
                update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo='CONTRATO_CONFIGURADO_KALEIDO')
                update_activo.save()
                response = {
                    'status': 'success',
                    'title': _('Activo Actualizado'),
                    'message': _('Se ha Creado el SmartContract')
                }
                #generar tokens de: tokens_totales
                #mintear token, esto puede tomar mucho tiempo! de 2 a 3 segundos
                #guardar los indices de los tokens creados
                return JsonResponse(response)
            else:
                # Si la solicitud no fue exitosa, puedes manejar el error aquí
                return JsonResponse({"error": "No se pudo obtener la información"}, status=500)

        except requests.exceptions.RequestException as e:
            # Manejar excepciones de solicitud, como conexiones fallidas
            return JsonResponse({"error": f"Error de solicitud: {str(e)}"}, status=500)

    else:
        response = {
                    'status': 'error',
                    'title': 'Not valid method',
                }
        return JsonResponse(response)