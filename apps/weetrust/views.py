from django.shortcuts import render
from django.http import HttpResponse

from config.settings import MIN_FACERECOGNITION, MIN_LIVENESS_RECORD, WEETRUST_URL, WEETRUST_USER_ID

from .models import AccessTokenWeetrust

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
import requests


def landing_view(request):
    html_message = "<html><body><h1>this is an app landing</h1></body></html>"
    response = HttpResponse(html_message)
    return response
    
def validate_biometric_info(uuid):
    print("Validating Biometric Info uuid=", uuid)
    resultado = {}
    if uuid != '' :
        token_model = AccessTokenWeetrust.objects.latest()
        
        if token_model.obtain_minutes() > 4.5 :
                print("requiendo token")
                token_model = AccessTokenWeetrust.obtain_new_token()
                token_value = token_model.value
        else:
            print("Reutilizando token")
            token_value = token_model.value
        
        headers = {
            'Content-Type': 'application/json',
            'user-id': WEETRUST_USER_ID,
            'token': token_value
            }
        body = {
            'uuid' : uuid
        } 
        #https://api-sandbox.weetrust.com.mx/biometric/get-results/
        url_obtain_results = WEETRUST_URL+'biometric/get-results/'
        response = requests.post(url_obtain_results, headers=headers, json=body)
        result = response.json()
        print("XXX resultado > results", result)
        
        if response.status_code == 200:
            print("Ejecucion correcta documento analizando respuesta")
            

            #Ojo la configuracion de validacion se hace con base a validacion conSelfie pues varia el diccionario a los que tienen
            print("Resultado validacion: ")
            #Verificando documento de identificación
            if result['responseData']['globalResult'] == 'Ok':
                print("01. Documento Valido :  SI VALIDADO ")
                resultado['id_validation'] = True
                #
                #Verificando si la persona esta viva
                if result['responseData']['scoreLiveness'] > MIN_LIVENESS_RECORD :
                    resultado['liveness'] = True
                    print("02. Comprobacion de Vida: APROBADA")
                else:
                    print("02. Comprobacion de Vida: NO CON PROBLEMAS")
                    resultado['liveness'] = False

                #verificando el reconocimiento facial
                if result['responseData']['scoreFaceMatch'] > MIN_FACERECOGNITION :
                    print("03. Resonocimiento facial: APROBADO")
                    resultado['face_recognition'] = True
                else:
                    print("03. Resonocimiento facial: FALLO")
                    resultado['face_recognition'] = False

                #verificando el reconocimiento facial
                if result['responseData']['globalResult'] == 'Ok':
                    print("04. Promedio reconocimiento : VALIDADO")
                    resultado['overall'] = True
                else:
                    print("04. Promedio reconocimiento : FALLIDO ")
                    resultado['overall'] = False
                #
            else:
                print("01. Documento Valido :  NO CON PROBLEMAS ")
                resultado['id_validation'] = False
                resultado['liveness'] = False
                resultado['face_recognition'] = False
                resultado['overall'] = False
            
                


            
            resultado['metadata'] = result['responseData']

            return(resultado)
            
        else:
            return({
                'fallo': f'Error al hacer la petición al servidor Weetrust: {result}'
            })
    else:
        print("UUID nulo")
        resultado['overall'] = None
        return(resultado)
    
def validate_biometric_info_new(identitySessionId):
    print("Validating Biometric Info identitySessionId=", identitySessionId)
    resultado = {}
    if identitySessionId != '' :
        token_model = AccessTokenWeetrust.objects.latest()
        
        if token_model.obtain_minutes() > 4.5 :
                print("requiendo token")
                token_model = AccessTokenWeetrust.obtain_new_token()
                token_value = token_model.value
        else:
            print("Reutilizando token")
            token_value = token_model.value
        
        headers = {
            'Content-Type': 'application/json',
            'user-id': WEETRUST_USER_ID,
            'token': token_value
            }
        body = {
            'uuid' : identitySessionId
        } 
        #https://api-sandbox.weetrust.com.mx/biometric/get-results/
        url_obtain_results = WEETRUST_URL+f'biometric/identity/session/results/{identitySessionId}'
        response = requests.post(url_obtain_results, headers=headers, json=body)
        if response.status_code == 200:
            result = response.json()
            print("XXX resultado > results OK", response)
            print("XXX resultado > results status", response.status_code)
            return result
        print('fallo Error al hacer la petición al servidor Weetrust:', response)
        print("fallo Error al hacer la petición al servidor status_code:", response.status_code)
        return({
                'fallo': f'Error al hacer la petición al servidor Weetrust: {response}'
            })
        
        if response.status_code == 200:
            print("Ejecucion correcta documento analizando respuesta")
            

            #Ojo la configuracion de validacion se hace con base a validacion conSelfie pues varia el diccionario a los que tienen
            print("Resultado validacion: ")
            #Verificando documento de identificación
            if result['responseData']['globalResult'] == 'Ok':
                print("01. Documento Valido :  SI VALIDADO ")
                resultado['id_validation'] = True
                #
                #Verificando si la persona esta viva
                if result['responseData']['scoreLiveness'] > MIN_LIVENESS_RECORD :
                    resultado['liveness'] = True
                    print("02. Comprobacion de Vida: APROBADA")
                else:
                    print("02. Comprobacion de Vida: NO CON PROBLEMAS")
                    resultado['liveness'] = False

                #verificando el reconocimiento facial
                if result['responseData']['scoreFaceMatch'] > MIN_FACERECOGNITION :
                    print("03. Resonocimiento facial: APROBADO")
                    resultado['face_recognition'] = True
                else:
                    print("03. Resonocimiento facial: FALLO")
                    resultado['face_recognition'] = False

                #verificando el reconocimiento facial
                if result['responseData']['globalResult'] == 'Ok':
                    print("04. Promedio reconocimiento : VALIDADO")
                    resultado['overall'] = True
                else:
                    print("04. Promedio reconocimiento : FALLIDO ")
                    resultado['overall'] = False
                #
            else:
                print("01. Documento Valido :  NO CON PROBLEMAS ")
                resultado['id_validation'] = False
                resultado['liveness'] = False
                resultado['face_recognition'] = False
                resultado['overall'] = False
            
                


            
            resultado['metadata'] = result['responseData']

            return(resultado)
            
        else:
            return({
                'fallo': f'Error al hacer la petición al servidor Weetrust: {result}'
            })
    else:
        print("UUID nulo")
        resultado['overall'] = None
        return(resultado)
    
    