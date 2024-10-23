from apps.asset.models import EstadoAprobacion, Fideicomiso
from ...models import DocumentSesionResult, AccessTokenWeetrust
from apps.user.models import User
from django.core.management.base import BaseCommand, CommandError

from config.settings import WEETRUST_URL, WEETRUST_USER_ID, WEETRUST_API_KEY
from ....weetrust.views import validate_biometric_info, validate_biometric_info_new

import base64
import json
import requests
from urllib.parse import urlparse
from django.core.files.base import ContentFile


class Command(BaseCommand):

    help = u'Obtain the documents pendindg for validate, signs and update local database'
    def handle(self, *args, **options):
        #Solicito la actualizacion de fideicomisos enviados previamente 
        fideicomisos_sended = Fideicomiso.objects.filter(enviado_weetrust = True, firmado_todos = False)
        for fideicomiso in fideicomisos_sended :
            print("validando documentos pendientes de firma en weetrust:", fideicomiso.id_weetrust_document)
            print("validando documentos pendientes de firma en Código:", fideicomiso.activo.codigo)
            id_weetrust_document = fideicomiso.id_weetrust_document
            #Obtain Weetrust Token
            token_model = AccessTokenWeetrust.objects.latest()
            if token_model.obtain_minutes() > 4.5 :
                token_model = AccessTokenWeetrust.obtain_new_token()
                token_value = token_model.value
            else:
                token_value = token_model.value

            #Update Document signs 
            url_check_signs = WEETRUST_URL+f'documents/{id_weetrust_document}'
            print("\n Solicitando a: ", url_check_signs)
            headers = {
                        'user-id': WEETRUST_USER_ID,
                        'token': token_value,
                        }
            response = requests.get(url_check_signs, headers=headers) #OJO es GET
            if response.status_code == 200:
                result = response.json()
                print("...........EL get obtuvo", result )
                firmantes = result['responseData']['signatory']
                print("\n  >>>>>>>>>>>>>>>>>>>>>>>>>>>   los firmantes son: ", firmantes)
                print("\n ")
                for data in firmantes:
                    sign_email = data['emailID']
                    identitySessionId = data['identitySessionId']
                    # print("||||||||||||     analizando la DATA: ", data)
                    # print("Validando correo: ", sign_email)
                    # print("COn el fideicomiso no: ", fideicomiso.id)
                    #Verificando si es la fiducia
                    if sign_email == fideicomiso.email_fiducia:
                        print("Validando Fiducia")
                        if data['isSigned'] == 1:
                            fideicomiso.aprobado_fiducia = True
                            fideicomiso.fiducia_sesion = data['biometricResultInfo']['biometricLogID']
                            fideicomiso.fiducia_json = validate_biometric_info_new( identitySessionId ) #reparando acá
                            fideicomiso.fiducia_biometric_url =  data['biometricResultInfo']['biometricResultUrl']
                        else:
                            fideicomiso.fiducia_signing_url = data['signing']['url']
                    #Verificando si es Devise
                    if sign_email == fideicomiso.email_devise:
                        print("Validando DEVISE")
                        if data['isSigned'] == 1:
                            fideicomiso.aprobado_devise = True
                            fideicomiso.devise_sesion = data['biometricResultInfo']['biometricLogID']
                            fideicomiso.devise_json = validate_biometric_info_new( identitySessionId )
                            fideicomiso.devise_biometric_url =  data['biometricResultInfo']['biometricResultUrl']
                            print("\n \n \n ---- EL ACTUAL ES ", fideicomiso.devise_biometric_url)
                        else:
                            fideicomiso.devise_signing_url = data['signing']['url']

                    #Verificando si es Sponsor
                    if sign_email == fideicomiso.email_sponsor:
                        print("Validando SPONSOR")
                        if data['isSigned'] == 1:
                            fideicomiso.aprobado_sponsor = True
                            fideicomiso.sponsor_sesion = data['biometricResultInfo']['biometricLogID']
                            fideicomiso.sponsor_json = validate_biometric_info_new( identitySessionId )
                            fideicomiso.sponsor_biometric_url =  data['biometricResultInfo']['biometricResultUrl']
                        else:
                            fideicomiso.sponsor_signing_url = data['signing']['url']

                    #Verificando si es Propietario
                    if sign_email == fideicomiso.email_propietario:
                        print("Validando PROPIETARIO")
                        if data['isSigned'] == 1:
                            fideicomiso.aprobado_propietario = True
                            fideicomiso.propietario_sesion = data['biometricResultInfo']['biometricLogID']
                            fideicomiso.propietario_json = validate_biometric_info_new( identitySessionId)
                            fideicomiso.propietario_biometric_url =  data['biometricResultInfo']['biometricResultUrl']
                        else:
                            fideicomiso.propietario_signing_url = data['signing']['url']

                    fideicomiso.save()

                if result['responseData']['status'] == 'COMPLETED':
                    #Grabo el archivo
                    url_file = result['responseData']['documentFileObj']['url']
                    print("La url es: ", url_file)
                    response = requests.get(url_file)
                    if response.status_code == 200:
                        url = url_file.split("?")[0]
                        file_name = url.split("/")[-1]
                        fideicomiso.fideicomiso_firmado.save(file_name, ContentFile(response.content), save=True)
                        print("archivo grabado exitosamente")
                    else:
                        print("error al guardar el archivo")
                    fideicomiso.firmado_todos = True
                    activo_model = fideicomiso.activo
                    activo_model.estado_aprobacion = EstadoAprobacion.objects.get(codigo="ACTIVO_FIDEICOMISO_FIRMADO")
                    activo_model.save()
                    fideicomiso.save()
                    
                print("fideicomiso actualizad: ", fideicomiso)

                
            


            