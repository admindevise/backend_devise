
from datetime import datetime, timezone
from django.db import models
from apps.utils.models import base_model

from config.settings import WEETRUST_URL, WEETRUST_USER_ID, WEETRUST_API_KEY

import requests
import json
# In this model allows Weetrust result of validation.

class DocumentSesionResult(base_model.BaseModel):
    user = models.ForeignKey(
        'user.User',
        on_delete = models.PROTECT,
        blank=True,
    )
    expedition_country = models.CharField(max_length = 128)
    country_code = models.CharField(max_length = 16)
    document_type = models.CharField(max_length = 128)
    document_number = models.CharField(max_length=128)
    document_front_image = models.TextField()
    document_back_image = models.TextField(
        blank=True,
        null=True,
    )
    selfie = models.TextField()
    response_data = models.JSONField(
        blank=True,
        null=True,
    )
    response_validation = models.JSONField(
        blank=True,
        null=True,
    )
    id_validation = models.BooleanField(
        default=False
    )
    liveness = models.BooleanField(
        default=False
    )
    face_recognition = models.BooleanField(
        default=False
    )
    names_validation = models.BooleanField(
        default=False
    )
    birth_date_validation = models.BooleanField(
        default=False
    )
    doc_number_validation = models.BooleanField(
        default=False
    )
    expedition_date_validation = models.BooleanField(
        default=False
    )
    feedback_text = models.TextField(blank=True, null=True, default = '')

    def get_session_results(self):
        print("Validando resultados")
        session_id = self.response_data['responseData']['uuid']
        print("sesion_id es:", session_id)

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
            'token': token_value,
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': '*/*',
            }
        body = {
            'uuid': session_id
        }
        json_body = json.dumps(body)

        
        url_get_results_biometric = WEETRUST_URL+'biometric/get-results'
        print("url es ", url_get_results_biometric)
        response = requests.post(url_get_results_biometric, data=json_body, headers=headers)
        result = response.json()
        print("resultados de validacion", result)
        if response.status_code == 200:
            print("Ejecucion correcta documento analizando respuesta")
            self.response_validation = result
            self.feedback_text = ''

            
            #Ojo la configuracion de validacion se hace con base a validacion conSelfie pues varia el diccionario a los que tienen
            print("empezando validacion")
            #Verificando documento de identificación
            if result['responseData']['globalResult'] == 'Ok':
                print("01. Es un documento valido")
                self.id_validation = True

            else:
                print("01. Error presuntamente un documento falso")
                self.feedback_text += "Error en documento volver a cargar las imagenes de documento. "

            #Verificando si la persona esta viva
            if result['responseData']['scoreLiveness'] > 90: #Parametro liveness
                self.liveness = True
                print("02. Es una persona viva")

            else:
                print("02. No se puede validar si esta viva la persona")
                self.feedback_text += "Error en selfie volver a cargar la imagen. "

            #verificando el reconocimiento facial
            if result['responseData']['scoreFaceMatch'] > 90: #RECONOCIMIENTO FACIAL
                print("03. reconocimiento facial aprobado")
                self.face_recognition = True

            else:
                print("03. No paso el reconocimiento facial")
                self.feedback_text += "Error en selfie no corresponde al documento, vuelva a cargar la imagen. "
            
            self.save()
            #mensaje para el usuario:
            feedback_user = result['responseData']['globalResultDescription']
            print(">>>>>>> Señor usuario: ", feedback_user)
            if result['responseData']['globalResult'] != 'Failed':
                user_basic_info = self.user
                diccionario = result['responseData']['documentData']
                for item in diccionario:
                    print("analizando: ", item)
                    if item['type'] == 'FullName':
                        # Validando nombres
                        name_model_words = sorted(user_basic_info.get_full_name().upper().split())
                        name_ocr_words = sorted(item['value'].split())
                        if name_model_words == name_ocr_words:
                            print("1. Los nombres en base de datos y documento coinciden")
                            self.names_validation = True
                        else:
                            self.feedback_text += "Error los nombres no corresponden del documento no corresponden a los registrados. "
                            print("1. Error los nombres no corresponden a lo registrado en User")

                    if item['type'] == 'DateOfBirth':
                        # Validando birthDate
                        birth_date_string = item['value']
                        fecha_a_comparar = datetime.strptime(birth_date_string, '%d/%m/%Y').date()
                        if fecha_a_comparar == user_basic_info.birth_date:
                            print("2. La fecha en base de datos y documento son las Mismas fechas de nacimiento")
                            self.birth_date_validation = True
                        else:
                            self.feedback_text += "Error la fecha de nacimiento del documento no corresponden a los registrados. "
                            print("2. Error: Las Fechas de nacimiento no coinciden")

                    if item['type'] == 'DocumentNumber':
                        # Validando numero de Documento
                        document_number_ocr = item['value']
                        if document_number_ocr == self.document_number:
                            print("3. Los numeros de Documento coinciden")
                            self.doc_number_validation = True
                        else:
                            self.feedback_text += "Error el numero de documento no corresponden a los registrados. "
                            print("3. Error el Numero de documento registrado  no coincide con el usuario")

                    if item['type'] == 'First Issue Date':
                        # Validando Fecha expedicion
                        expedition_doc_date = item['value']
                        fecha_expdate_comparar = datetime.strptime(expedition_doc_date, '%d/%m/%Y').date()
                        if fecha_expdate_comparar == self.user.expedition_date:
                            print("4. La fecha en base de datos y documento de expedicion son las Mismas")
                            self.expedition_date_validation = True
                        else:
                            self.feedback_text += "Error la fecha de expedicion del documento no corresponden a los registrados. "
                            print("4. Error las Fechas de expedición no coinciden")

                    self.save()
            else:
                print("Documento invalido")
            
        else:
            print("Error del server weetrust")




class AccessTokenWeetrust(base_model.BaseModel):
    value = models.TextField()
    
    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def obtain_minutes(self):
        now = datetime.now(timezone.utc)
        minutes = (now-self.created_at).total_seconds()/60
        print(f"El token tiene {minutes} minutos")
        return minutes
    
    @classmethod
    def obtain_new_token(cls):
        headers = {
            'user-id': WEETRUST_USER_ID,
            'api-key': WEETRUST_API_KEY
            }
        data = {}
        url_obtain_token = WEETRUST_URL+'access/token/'
        
        response = requests.post(url_obtain_token, data=json.dumps(data), headers=headers)
        result = response.json()
        token = AccessTokenWeetrust.objects.create(
            value = result['responseData']['accessToken']
        )
        return token


    
