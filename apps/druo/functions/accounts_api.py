from apps.user.models import User
from apps.info_financial.models import Financial
from ..models import Token, UserDruo
from config.settings import AUTH_DRUO_URL, DRUO_URL, CLIENT_ID, CLIENT_SECRET
import requests
import json
import time

# Define the URL
url = 'https://api-staging.druo.com/accounts/connect'


def create_account(user, account_info):
    # Verificar si hay tokens disponibles
    if not Token.objects.exists():
        return None, "No hay tokens disponibles. Por favor ejecute el comando obtain_druo_token primero."
    
    try:
        # Obtener el último token especificando el campo
        token = Token.objects.latest('created_at')
    except (Token.DoesNotExist, IndexError):
        return None, "Error al obtener un token válido. Verifique que exista al menos un token."
    # Define the headers
    headers = {
        'DRUO-Version': '2021-11-22',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token.access_token}'
    }
    # Manejar de manera segura los campos que podrían ser None
    local_id_type_value = None
    if user.local_id_type:
        local_id_type_value = user.local_id_type.value
    
    local_id_country = None
    if hasattr(user, 'doc_country_expedition') and user.doc_country_expedition:
        local_id_country = user.doc_country_expedition.code3
        
    # Verificar si tiene una fecha de nacimiento
    birth_date = None
    if user.birth_date:
        birth_date = user.birth_date.isoformat()
        
    # Obtener grupo de forma segura
    user_note = "Sin grupo"
    try:
        if user.groups.exists():
            user_note = user.groups.all()[0].name
    except:
        pass
    
    # Obtener datos de forma segura para el metadata
    codigo_para_referir = None
    referido_por = None
    
    if hasattr(user, 'code'):
        codigo_para_referir = user.code
    
    if hasattr(user, 'referred_by_code'):
        referido_por = user.referred_by_code
    
    # Manejar valores nulos para campos opcionales
    aba_code = account_info.aba_code if account_info.aba_code else ""
    swift_code = account_info.swift_code if account_info.swift_code else ""
    
    # Crear diccionario de datos
    data = {
        "institution_uuid": account_info.bank.uuid,
        "account_number": account_info.account_number,
        "type": account_info.account_type.value,
        "subtype": account_info.account_subtype.value,
        "user_authorization": True,
        "existing_end_user_id": None,
        "new_end_user_details": {
            "type": user.user_type_druo(),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "organization": user.user_organization_druo(),
            "local_id": user.document_number,
            "local_id_type": local_id_type_value,
            "local_id_country": local_id_country,
            "date_of_birth": birth_date,
            "email": user.email,
            "phone_number": {
                "number": user.get_phone_number(),
                "country_code": user.get_phone_indicative()
            },
            "address": user.get_address_info(),
            "preferred_language": None,
            "note": user_note,  # Usar variable segura en lugar de acceso directo
            "primary_reference": "Devise",
            "secondary_reference": "",
            "metadata": {
                "codigo_para_referir": codigo_para_referir,
                "referido_por": referido_por,
            }
        },
        "primary_reference": "Account Primary Reference Here",
        "secondary_reference": "Account Secondary Reference Here",
        "metadata": {
            "id_user_devise": user.pk,
            "id_financial_devise": account_info.pk,
            "abba_code": aba_code,
            "swift_code": swift_code,
        }
    }
    print("Data: ", data)
    print("headers: ", headers)
    print("access_token: ", token.access_token)

    response = requests.post(url, headers=headers, json=data)

    # Imprime la respuesta del servidor
    response_code = response.status_code
    respuesta_druo = response.text
    print("codigo response", response.status_code)
    print("respuesta", respuesta_druo)
    data = json.loads(respuesta_druo)
    if response_code == 200:
        
        UserDruo.objects.create(
            user_devise = user,
            uuid = data['account']['uuid'],
            code = data['account']['code'],
            current_status = data['account']['current_status'],
            metadata = data
        )
    else:
        UserDruo.objects.create(
            user_devise = user,
            created = False,
            metadata = data
        )
    
    return


    