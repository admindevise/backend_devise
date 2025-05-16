from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

from config.const_kaleido import CONSORTIA, ENVIRONMENT_ID, USERNAME, PASSWORD, BEARER, SERVICE_WALLET, SERVICE_HOST, ZONE_DOMAIN, USER_ACCOUNTS

from apps.kaleido.models import Wallet, InstanceOfTokenContract721
from apps.fund.models import Fund, FundInvestment

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
    Verifica si un usuario es inversor de un fondo específico.
    
    Args:
        user: El usuario a verificar
        fund_id: El ID del fondo
    
    Returns:
        Tupla (investment, error_message) donde investment es el objeto FundInvestment si existe,
        o None si no existe. Si hay error, error_message contiene el mensaje de error.
    """
    
    try:
        if user.is_staff:
        # Si el usuario es staff, no se requiere verificar la inversión
            return True, None
        
        # Buscar una inversión para este usuario en el fondo especificado
        investment = FundInvestment.objects.filter(investor=user, fund_id=fund_id).first()
        
        if investment:
            # Inversor válido
            return investment, None
        else:
            return None, f"User {user.username} is not an investor in fund {fund_id}"
            
    except Exception as e:
        return None, f"Error verifying investment: {str(e)}"

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
    Retrieves the wallet index for the given user, specific to a Fund.

    Returns:
      A tuple (data, error) where data is the JSON response from the external service
      if successful, or error is a string with the error message.
    """
    try:
        # Try to get a FundInvestment for the user and use its associated Fund's hd_wallet if available
        investment = FundInvestment.objects.filter(investor=user, fund_id=fund_id).first()
        if not investment:
            return None, "No investment found for this user in the specified fund"

        if investment.fund.hd_wallet:
            wallet_id_value = investment.fund.hd_wallet.id_wallet
            print(f"Found hd_wallet for user {user.email} in fund {fund_id}: {wallet_id_value}")
        else:
            return None, "No hd_wallet found for the specified fund"

    except FundInvestment.DoesNotExist:
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
