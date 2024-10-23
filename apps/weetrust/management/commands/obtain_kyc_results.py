from ...models import DocumentSesionResult, AccessTokenWeetrust
from apps.user.models import User
from django.core.management.base import BaseCommand, CommandError

from config.settings import WEETRUST_URL, WEETRUST_USER_ID, WEETRUST_API_KEY


import base64
import json
import requests

class Command(BaseCommand):

    help = u'Obtain the documents pendindg for validate, then request a token to send an Verification Process'
    def handle(self, *args, **options):
        #Solicito la actualizacion de documentos enviados previamente 
        users_already_send = User.objects.filter(kyc_validated = 'validating_document')
        for user in users_already_send :
            print("validando usuarios pendientes de consultar de nuwvo a weetrust:", user)
            document = DocumentSesionResult.objects.filter(user = user).latest('id')
            document.get_session_results()
            if document.feedback_text =='':
                user.kyc_validated = 'sucessfull_document'
            else:
                user.kyc_validated = 'fail_document'
            user.save()
        

        # Envio nuevas peticiones de documentos nuevos listos para validar Actualizado 17-01-2024
        users = User.objects.filter(kyc_validated = 'ready_for_kyc')
        for user in users :
            print("Cargando documentos para:", user)
            if user.document_front_image != None:
                print("Cargando imagenes al documento")
                country = user.doc_country_expedition
                #Obtain Weetrust Token
                token_model = AccessTokenWeetrust.objects.latest()
                
                if token_model.obtain_minutes() > 4.5 :
                    token_model = AccessTokenWeetrust.obtain_new_token()
                    token_value = token_model.value
                else:
                    token_value = token_model.value

                with user.document_front_image.open(mode='rb') as front_image_file:
                    front_64 = base64.b64encode(front_image_file.read()).decode("utf-8")

                with user.document_back_image.open(mode='rb') as back_image_file:
                    back_64 = base64.b64encode(back_image_file.read()).decode("utf-8")

                with user.selfie.open(mode='rb') as selfie_image_file:
                    selfie_64 = base64.b64encode(selfie_image_file.read()).decode("utf-8")


                document_sesion = DocumentSesionResult.objects.create(
                    user= user, 
                    expedition_country= user.doc_country_expedition.name,
                    country_code = user.doc_country_expedition.code2,
                    document_type= user.local_id_type.value, 
                    document_number= user.document_number, 
                    document_front_image= front_64, 
                    document_back_image= back_64, 
                    selfie= selfie_64,
                )

                headers = {
                    'Content-Type': 'application/json',
                    'user-id': WEETRUST_USER_ID,
                    'token': token_value,
                    'Connection': 'keep-alive',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': '*/*',
                    }
                
                data = {
                    'frontImage': front_64,
                    'backImage': back_64,
                    'faceImage': selfie_64,
                }

                json_data = json.dumps(data)
                url_obtain_verification = WEETRUST_URL+'biometric/verify-document'
                response = requests.post(url_obtain_verification, data=json_data, headers=headers)
                result = response.json()
                print("Ruta de verificacion: ", url_obtain_verification)
                print("response de verificacion", response)
                print("result de verification", result)
                if response.status_code == 200:
                    print("Todo al pelo el documento se subio bien")
                    document_sesion.response_data = result
                    document_sesion.save()
                    user.kyc_validated ='validating_document'
                    user.save()

                else:
                    print("Respondiendo error del server weetrust")
                    document_sesion.response_data = result
                    document_sesion.save()
            print("----FIN-----\n\n")
      
        return