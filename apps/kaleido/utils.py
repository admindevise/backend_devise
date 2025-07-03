from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

from config.const_kaleido import CONSORTIA, ENVIRONMENT_ID, USERNAME, PASSWORD, BEARER, SERVICE_WALLET, SERVICE_HOST, ZONE_DOMAIN, USER_ACCOUNTS, SERVICE

from apps.kaleido.models import Wallet, InstanceOfTokenContract721
from apps.fund.models import Fund, FundInvestment, FundApplication

from requests.auth import HTTPBasicAuth
from django.db import transaction
import requests
import time
import json

@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def create_wallet_for_fund(user, secret):
    url = f"https://{SERVICE_WALLET}/api/v1/wallets"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {BEARER}'
    }
    data = {'secret': secret}
    try:
        response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        response_data = response.json()
    except Exception as e:
        return None, str(e)

    if response.status_code in [200, 201]:
        try:
            wallet = Wallet.objects.create(
                user=user,
                id_wallet=response_data['id'],
                secret=secret,
                environment_id=ENVIRONMENT_ID,
                wallet_service=SERVICE_WALLET,
                zone_domain=ZONE_DOMAIN,
                consortia=CONSORTIA
            )
            return wallet, None
        except Exception as e:
            return None, str(e)
    else:
        return None, f"Error from external service: {response_data}"
    
    
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def create_instance_token_contract_721(user, name, symbol, promote_contract=None):
    
    if promote_contract:
        endpoint = promote_contract.endpoint
    else:
        endpoint = None
            
    url = f'https://{SERVICE_HOST}/gateways/{endpoint}'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {BEARER}',
        'x-kaleido-from': USER_ACCOUNTS,
        'x-kaleido-sync': 'false'  # Modo asíncrono
    }
    data = { 'name': name, 'symbol': symbol }
    
    try:
        response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        response_data = response.json()
        print(f"Response from token creation: {response_data}")  # Para depuración
    except Exception as e:
        return None, str(e)
    
    # Si obtenemos un ID de transacción o hay indicación de éxito
    if (response.status_code in [200, 201, 202]) and ('id' in response_data or response_data.get('sent') is True):
        # Usamos el transaction ID como identificador temporal
        tx_id = response_data.get('id', 'pending-tx')
        
        try:
            # Crear la instancia con un marcador temporal para contract_address
            with transaction.atomic():
                instance = InstanceOfTokenContract721.objects.create(
                    user=user,
                    promote_contract=promote_contract,
                    name=name,
                    symbol=symbol,
                    contract_address=tx_id  # Usamos el ID de transacción temporalmente
                )
            
            # BLOQUE PARA CONSULTAR Y ACTUALIZAR CONTRACT_ADDRESS
            # Intentar obtener el recibo con más reintentos y tiempo de espera incremental
            max_attempts = 15  # Aumentamos a 15 intentos
            initial_wait = 2   # Empezamos esperando 2 segundos
            address_found = False
            
            for attempt in range(max_attempts):
                if address_found:
                    break
                    
                wait_time = initial_wait * (attempt + 1)  # Tiempo de espera incremental
                receipt_url = f'https://{SERVICE_HOST}/replies/{tx_id}'
                receipt_headers = {
                    'accept': 'application/json',
                    'Content-Type': 'application/json',
                }
                
                try:
                    receipt_response = requests.get(
                        receipt_url,
                        headers=receipt_headers,
                        auth=HTTPBasicAuth(USERNAME, PASSWORD),
                    )
                    
                    if receipt_response.status_code == 200:
                        receipt_data = receipt_response.json()
                        
                        # Si hay error "Receipt not available", esperamos más
                        if 'error' in receipt_data and 'Receipt not available' in receipt_data['error']:
                            print(f"Intento {attempt+1}/{max_attempts}: Recibo no disponible, esperando {wait_time}s")
                            time.sleep(wait_time)
                            continue
                        
                        # Intentamos extraer la dirección del contrato de diferentes partes de la respuesta
                        contract_address = None
                        
                        # Opción 1: Directamente en contractAddress
                        if 'contractAddress' in receipt_data:
                            contract_address = receipt_data['contractAddress']
                        
                        # Opción 2: En los eventos
                        elif 'events' in receipt_data and receipt_data['events']:
                            for event in receipt_data['events']:
                                if 'address' in event:
                                    contract_address = event['address']
                                    break
                        
                        # Opción 3: En la respuesta de output
                        elif 'output' in receipt_data:
                            contract_address = receipt_data['output']
                            
                        # Si encontramos una dirección, actualizamos la instancia
                        if contract_address:
                            with transaction.atomic():
                                instance.contract_address = contract_address
                                instance.save(update_fields=['contract_address'])
                            address_found = True
                            print(f"Dirección del contrato encontrada: {contract_address}")
                            break
                        else:
                            print(f"Intento {attempt+1}/{max_attempts}: No se encontró dirección en la respuesta")
                            
                except Exception as e:
                    print(f"Error en intento {attempt+1}/{max_attempts}: {str(e)}")
                
                # Si llegamos aquí sin encontrar la dirección, esperamos antes del siguiente intento
                time.sleep(wait_time)
            
            # Verificamos si finalmente encontramos la dirección
            if not address_found:
                print(f"No se pudo obtener la dirección del contrato después de {max_attempts} intentos")
            
            return instance, None
            
        except Exception as e:
            return None, str(e)
    else:
        return None, f"Error from external service: {response_data}"
    

#! ================ Funciones de verificación ================ #
def is_investor_valid(user, fund_id):
    """
    Verifica si un usuario es inversor de un fondo específico basándose en FundApplication.
    
    Args:
        user: El usuario a verificar
        fund_id: El ID del fondo
    
    Returns:
        Tupla (application, error_message) donde application es el objeto FundApplication aprobado o True (para staff),
        o None si no existe o no está aprobado. Si hay error, error_message contiene el mensaje de error.
        
    Examples:
        >>> application, error = is_investor_valid(request.user, fund_id)
        >>> if application:
        >>>     # Usuario tiene aplicación aprobada o es staff
        >>> else:
        >>>     # Mostrar mensaje de error
    """
    # Si el usuario es staff, devolver inmediatamente
    if user.is_staff:
        return True, None
    
    try:
        # Buscar aplicación del usuario para el fondo específico
        application = FundApplication.objects.get(applicant=user, fund_id=fund_id)
        
        # Verificar que la aplicación esté aprobada
        if application.status == FundApplication.ApplicationStatus.APPROVED:
            return application, None
        else:
            status_display = application.get_status_display()
            return None, f"La aplicación del usuario {user.email} al fondo con ID {fund_id} está en estado: {status_display}. Se requiere estado 'Aprobada' para ser considerado inversor."
    
    except FundApplication.DoesNotExist:
        return None, f"El usuario {user.email} no tiene una aplicación para el fondo con ID {fund_id}"
        
    except FundApplication.MultipleObjectsReturned:
        # Caso improbable pero posible si hay duplicados
        application = FundApplication.objects.filter(applicant=user, fund_id=fund_id, status=FundApplication.ApplicationStatus.APPROVED).first()
        if application:
            return application, "Advertencia: Se encontraron múltiples aplicaciones. Se retornó la primera aprobada."
        else:
            return None, f"Se encontraron múltiples aplicaciones para el usuario {user.email} en el fondo {fund_id}, pero ninguna está aprobada"
        
    except Exception as e:
        return None, f"Error al verificar la aplicación: {str(e)}"

def get_owner_of(token_id, fund_id):
    """
    Calls the ownerOf endpoint to get the owner of a token.
    Input:
      - token_id: ID of the token to check ownership for.
    Returns:
      - A tuple (response_data, error), where response_data is the JSON response on success,
        or error contains an error message on failure.
    """
    
    try:
        fund = Fund.objects.get(id=fund_id)
        instance_id = fund.contract_address
        if not instance_id:
            return None, "No instance_id found for the specified fund"
        
        url = f"https://{SERVICE_HOST}/instances/{instance_id}/ownerOf"
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': USER_ACCOUNTS,
        }
        data = {"tokenId": token_id}
        try:
            response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
            response_data = response.json()
        except Exception as e:
            return None, str(e)
        if response.status_code == 200:
            return response_data, None
        else:
            return None, f"Error {response.status_code}: {response_data}"
    except Fund.DoesNotExist:
        return None, "Fund not found"

def get_wallet_index(user, fund_id):
    """
    This function queries the FundInvestment model to verify the user's investment
    in the specified fund, then makes an API call to an external wallet service
    to retrieve the wallet index information.
    
    Parameters:
        user: User object
            The user whose wallet index is being retrieved
        fund_id: int or str
            The ID of the fund to check for user's investment
            
        tuple: A tuple containing two elements:
            - data (dict or None): The JSON response from the external service if successful
            - error (str or None): An error message if the operation failed
            
    Raises:
        No explicit exceptions are raised as they are caught internally
    """
    try:
        # Try to get a FundInvestment for the user and use its associated Fund's hd_wallet if available
        investment = FundApplication.objects.filter(applicant=user, fund_id=fund_id).first()
        if not investment:
            return None, "No investment found for this user in the specified fund"

        if investment.fund.hd_wallet:
            wallet_id_value = investment.fund.hd_wallet.id_wallet
        else:
            return None, "No hd_wallet found for the specified fund"

    except FundApplication.DoesNotExist:
        return None, "No investment found for this user in the specified fund"
    except Wallet.DoesNotExist:
        return None, "No wallet found for this user"

    url = f"https://{SERVICE_WALLET}/api/v1/wallets/{wallet_id_value}/accounts/{user.id}"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error from service: {response.json()}"
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"

#! ================ Funciones de utilidad ================ #
def mint_721_token(token_id, fund_id, contract_address_id):
    # Verificar primero si el token ya existe
    owner_data, owner_error = get_owner_of(token_id, fund_id)
    if owner_error is None and owner_data.get('output'):
        # Token ya existe
        return None, f"Token {token_id} already minted. Owner: {owner_data.get('output')}"
        
    url = f'https://{SERVICE_HOST}/instances/{contract_address_id}/mint'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-kaleido-from': USER_ACCOUNTS,
        'x-kaleido-sync': 'false',
    }
    data = {
        'to': USER_ACCOUNTS,
        'tokenId': token_id
    }
    try:
        response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            return None, f'Invalid JSON response: {response.text}'
    except Exception as e:
        return None, str(e)
    
    if response.status_code in [200, 201, 202]:
        return response_data, None
    else:
        return None, f"Error from external service: {response_data}"

def burn_721_token(token_id, fund_id, contract_address_id):
    # Verificar la propiedad del token
    owner_data, owner_error = get_owner_of(token_id, fund_id)
    if owner_error is not None:
        error_obj = {
            "message": "No se pudo verificar la propiedad del token en el fondo",  
            "details": {
                "owner_error": str(owner_error),
                "token_id": token_id,
                "fund_id": fund_id
            }
        }
        return None, error_obj

    if owner_data.get('output', '').lower() != USER_ACCOUNTS.lower():
        return None, f"Token {token_id} is not owned by the sender. Owner: {owner_data.get('output')}"

    
    url = f'https://{SERVICE_HOST}/instances/{contract_address_id}/burn'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-kaleido-from': USER_ACCOUNTS,
    }
    data = {
        'tokenId': token_id
        }
    try:
        response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            return None, f'Invalid JSON response: {response.text}'
    except Exception as e:
        return None, str(e)
    
    if response.status_code in [200, 201, 202]:
        return response_data, None
    else:
        return None, f"Error from external service: {response_data}"

#* Simula la compra de un token / inversion en un fondo
def safe_transfer_721(token_id, fund_id, contract_address_id, user_investor):
    # 1. Verificar que el usuario este asociado al fondo
    investment, error = is_investor_valid(user_investor, fund_id)
    if error is not None:
        return None, error
    
    # 2. Verificar la propiedad del token
    owner_data, owner_error = get_owner_of(token_id, fund_id)
    if owner_error is not None:
        error_obj = {
            "message": "No se pudo verificar la propiedad del token en el fondo",
            "details": {
                "owner_error": str(owner_error),
                "token_id": token_id,
                "fund_id": fund_id
                }
        }
        return None, error_obj
    
    if owner_data.get('output', '').lower() != USER_ACCOUNTS.lower():
        error_obj = {
            "message": "Token no pertenece al remitente",
            "details": {
                "token_id": token_id,
                "fund_id": fund_id,
                "owner": owner_data.get('output'),
                "sender": USER_ACCOUNTS
            }
        }
        return None, error_obj
    
    # 3. Obtener la dirección de la wallet del usuario inversor
    address_wallet, error = get_wallet_index(user_investor, fund_id)
    if error is not None:
        return None, error
    
    url = f'https://{SERVICE_HOST}/instances/{contract_address_id}/safeTransferFrom'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-kaleido-from': USER_ACCOUNTS,
    }
    data = {
        "from": USER_ACCOUNTS,
        "to": address_wallet['address'],
        "tokenId": token_id,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            return None, f'Invalid JSON response: {response.text}'
    except Exception as e:
        return None, str(e)
    
    if response.status_code in [200, 201, 202]:
        return response_data, None
    else:
        return None, f"Error from external service: {response_data}"
    
#* Simula la compra de un token en el mercado secundario
def safe_transfer_721_index_to_index(token_id, fund_id, contract_address_id, user_investor, address_wallet_sender, wallet_id):
    # 1. Verificar que el usuario este asociado al fondo
    investment, error = is_investor_valid(user_investor, fund_id)
    if error is not None:
        return None, error
    
    # 2. Obtener la dirección de la wallet del usuario inversor
    address_wallet, error = get_wallet_index(user_investor, fund_id)
    if error is not None:
        return None, error
    
    address_wallet_user = address_wallet['address']
    
    # 3. Verificar la propiedad del token en el fondo
    owner_data, owner_error = get_owner_of(token_id, fund_id)
    if owner_error is not None:
        error_obj = {
            "message": "No se pudo verificar la propiedad del token en el fondo",
            "details": {
                "owner_error": str(owner_error),
                "token_id": token_id,
                "fund_id": fund_id
                }
        }
        return None, error_obj
    
    # 4. Verificar que el token pertenece al remitente
    if owner_data.get('output', '').lower() != address_wallet_user.lower():
        error_obj = {
            "message": "Token no pertenece al remitente",
            "details": {
                "token_id": token_id,
                "fund_id": fund_id,
                "owner": owner_data.get('output'),
                "sender": address_wallet_user
            }
        }    
        return None, error_obj

    print('address_wallet_user', address_wallet_user)
    # 5. Preparar el payload y realizar la transferencia
    payload = {
        "from": address_wallet_user,
        "to": address_wallet_sender,
        "tokenId": token_id,
    }
    
    # 6. Realizar la transferencia
    from_address = f'hd-{SERVICE}-{wallet_id}-{user_investor.id}'
    url = f'https://{SERVICE_HOST}/instances/{contract_address_id}/safeTransferFrom'
    
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-kaleido-from': from_address,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            return None, f'Invalid JSON response: {response.text}'
    except Exception as e:
        return None, str(e)
    
    if response.status_code in [200, 201, 202]:
        return response_data, None
    else:
        return None, f"Error from external service: {response_data}"
