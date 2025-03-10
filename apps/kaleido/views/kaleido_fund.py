from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user
from django.core.cache import cache

from config.const_kaleido import CONSORTIA, ENVIRONMENT_ID, USERNAME, PASSWORD, BEARER, SERVICE_HOST, NODE_ID, CONSOLE_URL, SERVICE_WALLET, MEMBERSHIP_ID, ZONE_DOMAIN, USER_ACCOUNTS, SERVICE

from apps.kaleido.models import Wallet, InstanceOfTokenContract721
from apps.fund.models import FundInvestment, TransferReceipt, Fund

import requests
from requests.auth import HTTPBasicAuth
import json

def is_investor_valid(user, fund_id):
    try:
        # Buscar una inversión para este usuario en el fondo especificado
        investment = FundInvestment.objects.filter(investor=user, fund__id=fund_id).first()
        
        if investment:
            print(f'Inversor válido: {user.email} en fondo {fund_id}')
            return investment, None
        else:
            return None, "The user is not associated with the specified fund"
            
    except Exception as e:
        return None, f"Error verifying investment:{str(e)}"

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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def burn_721_token(request):
    """
    Burn a 721 token for a user.
    """
    fund_id = request.data.get('fund_id')
    token_id = request.data.get('tokenId')
    
    if not fund_id:
        return Response({'error': 'fund_id is required'}, status=400)
    if not token_id:
        return Response({'error': 'tokenId is required'}, status=400)
    
    owner_data, error = get_owner_of(token_id, fund_id)
    if error is not None:
        return Response(
            {"error": "Failed to verify token ownership", "details": error},
                status=400
            )
    
    if owner_data.get('output', '').lower() != USER_ACCOUNTS.lower():
            return Response(
                {
                    "message": "Token is not owned by the sender",
                    "owner": owner_data.get('output'),
                },
                status=400
            )
    
    try:
        fund = Fund.objects.get(id=fund_id)
    except Fund.DoesNotExist:
        return Response({'error': 'Fund not found'}, status=404)
    
    try:       
        response_data, error = get_burn_from_kaleido(fund.contract_address, token_id)
        if error:
            return Response({'error': error}, status=400)
        return Response(response_data, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

def get_burn_from_kaleido(contract_address, token_id):
    url = f'https://{SERVICE_HOST}/instances/{contract_address}/burn'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-kaleido-from': USER_ACCOUNTS,
    }
    data = {'tokenId': token_id}
    
    response = requests.post(
        url,
        headers=headers,
        json=data,
        auth=HTTPBasicAuth(USERNAME, PASSWORD)
    )
    
    response_data = response.json()
    
    if response.status_code in [200, 201] or (response_data and response_data.get('sent') is True):
        return response_data, None
    else:
        return None, f"API error: {response_data}"

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_wallet_address(request):
    fund_id = request.data.get('fund_id')
    if not fund_id:
        return Response({'error': 'fund_id is required'}, status=400)
    
    try:
        investment = FundInvestment.objects.get(investor=request.user, fund__id=fund_id)
    except FundInvestment.DoesNotExist:
        return Response({'error': 'User is not associated with the specified fund'}, status=404)
    
    wallet_data, error = get_wallet_index(request.user, fund_id)
    if error or not wallet_data:
        return Response({'error': error or "No wallet index found"}, status=400)
    
    address = wallet_data.get('address')
    private_key = wallet_data.get('privateKey')
    return Response({'address': address, 'privateKey': private_key}, status=200)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_token_balance(request):
    """
    Obtiene el balance de tokens de un usuario en un fondo específico.
    
    Args:
        request: HTTP request con fund_id en el body
        
    Returns:
        Response: Balance de tokens o mensaje de error
    """
    # 1. Validación de entrada
    fund_id = request.data.get('fund_id')
    if not fund_id:
        return Response({'error': 'fund_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 2. Verificación de inversión
    investment, error = is_investor_valid(request.user, fund_id)
    if not investment:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    # 3. Obtener información del fondo
    fund = investment.fund
    if not fund.contract_address:
        return Response(
            {'error': 'Fund contract address is not set'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 4. Obtener wallet del usuario
    wallet_data, error = get_wallet_index(request.user, fund_id)
    if error or not wallet_data:
        return Response(
            {'error': error or "No wallet index found"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 5. Preparar y ejecutar la solicitud al API de Kaleido
    try:
        balance = get_token_balance_from_kaleido(
            fund.contract_address,
            wallet_data.get('address')
        )
        return Response(balance, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Failed to get token balance', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def get_token_balance_from_kaleido(contract_address, owner_address):
    """Helper para obtener el balance desde Kaleido"""
    url = f'https://{SERVICE_HOST}/instances/{contract_address}/balanceOf'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-kaleido-from': USER_ACCOUNTS,
    }
    
    data = {'owner': owner_address}
    
    response = requests.post(
        url, 
        headers=headers, 
        json=data, 
        auth=HTTPBasicAuth(USERNAME, PASSWORD)
    )
    
    if response.status_code not in [200, 201]:
        raise Exception(f"API error: {response.text}")
    
    return response.json()

""" Tokens """
def mint_721_token(wallet, token_id, token_uri, fund_id):
    try:
        fund = Fund.objects.get(id=fund_id)
        instance_id = fund.contract_address
        if not instance_id:
            return None, "Fund doesn't have a contract address"
            
        url = f'https://{SERVICE_HOST}/instances/{instance_id}/mint'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': USER_ACCOUNTS,
        }
        data = {
            'to': USER_ACCOUNTS,
            'tokenId': token_uri
        }
        try:
            response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
            response_data = response.json()
        except Exception as e:
            return None, str(e)

        if response.status_code in [200, 201]:
            return response_data, None
        else:
            return None, f"Error from external service: {response_data}"
    except Fund.DoesNotExist:
        return None, "Fund not found"
    
class Mint721View(APIView):
    """
    Mint 721 token
    data :
    - to: address of the recipient without (0x)
    - tokenId: token id
    """
    permission_classes = [AllowAny]
    def post(self, request):
        token_id = request.data.get('tokenId')
        fund_id = request.data.get('fund_id')
        
        if not token_id:
            return Response({"error": "tokenId is required"}, status=400)
        if not fund_id:
            return Response({"error": "fund_id is required"}, status=400)
        
        # Verificar antes si el token y fondo ya existe
        try:
            fund = Fund.objects.get(id=fund_id)
            instance_id = fund.contract_address
            if not instance_id:
                return Response({"error": "Fund doesn't have a contract address"}, status=400)
            
            # Verificar si el token ya existe
            owner_data, owner_error = get_owner_of(token_id, fund_id)
            if owner_error is None:
                # Si la respuesta es exitosa, el token ya existe
                return Response({"message": "Token already exists", "owner": owner_data.get('output', None)}, status=400)
        
            url = f'https://{SERVICE_HOST}/instances/{instance_id}/mint'
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json',
                'x-kaleido-from': USER_ACCOUNTS,
            }
            
            data = request.data.copy()
            data['to'] = USER_ACCOUNTS
            
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    auth=HTTPBasicAuth(USERNAME, PASSWORD),
                    )
                if response.status_code in [200, 201, 202]:
                    response_data = response.json()
                    return Response(response_data, status=response.status_code)
                else:
                    return Response(
                        {'error': 'Invalid response', 'content': response.text},
                        status=response.status_code
                        )
            except requests.exceptions.RequestException as e:
                return Response(
                    {'error': 'Request failed', 'message': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        except Fund.DoesNotExist:
            return Response({"error": "Fund not found"}, status=404)
            
class SafeTransfer721View(APIView):
    """
    Safe transfer 721 token
    data :
    - from: current owner of the token
    - to: address to receive the ownership of the given token ID
    - tokenId: token id
    """
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # 1. Validar token_id y fund_id
        token_id = request.data.get('tokenId')
        fund_id = request.data.get('fund_id')
        
        if not token_id:
            return Response({"error": "tokenId is required"}, status=400)
        if not fund_id:
            return Response({"error": "fund_id is required"}, status=400)
        
        # 2. Verificar que el usuario esté asociado al fondo (inversor)
        investment, error = is_investor_valid(request.user, fund_id)
        if not investment:
            return Response({"error": error}, status=400)
        
        # 3. Obtener el Fondo y validar que tenga una wallet y contract_address asociada
        fund = investment.fund
        if not fund.hd_wallet:
            return Response({"error": "The selected fund does not have an associated wallet"}, status=400)
        wallet = fund.hd_wallet
        
        if not fund.contract_address:
            return Response({"error": "The selected fund does not have a contract address"}, status=400)
        instance_id = fund.contract_address
        
        # 4. Obtener el token y verificar que pertenezca al usuario
        owner_data, owner_error = get_owner_of(token_id, fund_id)
        if owner_error is not None:
            return Response(
                {"error": "Failed to verify token ownership", "details": owner_error},
                status=400
            )
        
        # 5. Verificar que el token pertenece al usuario
        if owner_data.get('output', '').lower() != USER_ACCOUNTS.lower():
            return Response(
                {
                    "message": "Token is not owned by the sender",
                    "owner": owner_data.get('output'),
                },
                status=400
            )
            
        # 6. Preparar el payload y realizar la transferencia
        url = f'https://{SERVICE_HOST}/instances/{instance_id}/safeTransferFrom'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': USER_ACCOUNTS,
        }
        
        data = request.data
        data['from'] = USER_ACCOUNTS
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                )
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                return Response(response_data, status=response.status_code)
            else:
                return Response(
                    {'error': 'Invalid response', 'content': response.text},
                    status=response.status_code
                    )
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )             

class SafeTransfer721IndexToIndexView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # 1. Validar token_id y fund_id
        token_id = request.data.get('tokenId')
        fund_id = request.data.get('fund_id')

        if not token_id:
            return Response({"error": "tokenId is required"}, status=400)
        if not fund_id:
            return Response({"error": "fund_id is required"}, status=400)

        # 2. Verificar que el usuario esté asociado al fondo (inversor)
        investment, error = is_investor_valid(request.user, fund_id)
        if not investment:
            return Response({"error": error}, status=400)
        
        # 3. Obtener el Fondo y validar que tenga una wallet asociada
        fund = investment.fund
        if not fund.hd_wallet:
            return Response({"error": "The selected fund does not have an associated hd_wallet"}, status=400)
        wallet = fund.hd_wallet
        
        if not fund.contract_address:
            return Response({"error": "The selected fund does not have a contract address"}, status=400)
        instance_id = fund.contract_address

        # 4. Obtener la wallet index (wallet general de Kaleido) para validar token ownership
        wallet_index_data, error = get_wallet_index(request.user, fund_id)
        if error:
            return Response({"error": error}, status=400)
        general_wallet_address = wallet_index_data.get("address")
        if not general_wallet_address:
            return Response({"error": "No address found in wallet index data"}, status=400)

        # 5. Verificar que el token pertenece a la wallet general
        owner_data, owner_error = get_owner_of(token_id, fund_id)
        if owner_error is not None:
            return Response({"error": "Failed to verify token ownership", "details": owner_error}, status=400)
        if owner_data.get('output', '').lower() != general_wallet_address.lower():
            return Response({
                    "error": "Token does not belong to the wallet",
                    "owner": owner_data.get("output"),
                    "wallet": general_wallet_address,
                }, status=400)

        # 6. Preparar el payload y realizar la transferencia
        payload = request.data.copy()
        payload['from'] = general_wallet_address

        from_address = f'hd-{SERVICE}-{wallet.id_wallet}-{request.user.id}'
        url = f'https://{SERVICE_HOST}/instances/{instance_id}/safeTransferFrom'
        try:
            response = requests.post(
                url,
                headers={
                    'accept': 'application/json',
                    'Content-Type': 'application/json',
                    'x-kaleido-from': from_address
                },
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD)
            )
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
               
                fund_instance = None
                if fund_id:
                    try:
                        fund_instance = Fund.objects.get(id=fund_id)
                    except Fund.DoesNotExist:
                        pass
                TransferReceipt.objects.create(
                    user=request.user,
                    transfer_id=response_data.get('id'),
                    fund=fund_instance
                )
                print(general_wallet_address, request.user.email, wallet.id_wallet)
                return Response(response_data, status=response.status_code)
            return Response(
                {'error': 'Transfer failed', 'details': response.json()},
                status=response.status_code
            )
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=500
            )

class ReceipStoreView(APIView):
    """
    Store a receipt
    """        
    permission_classes = [AllowAny]
    def post(self, request):
        transfer_id = request.data.get('transfer_id')
        
        if not transfer_id:
            return Response(
                {'error': 'transfer_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        url = f'https://{SERVICE_HOST}/replies/{transfer_id}'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            }
        
        data = request.data
        
        print(f'Transfer ID2: {transfer_id}')
        # Intentar hasta 3 veces con espera de 2 segundos
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    auth=HTTPBasicAuth(USERNAME, PASSWORD),
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if 'error' in response_data and 'Receipt not available' in response_data['error']:
                        if attempt < max_attempts - 1:
                            time.sleep(2)  # esperar 2 segundos
                            continue
                    return Response(response_data, status=response.status_code)
                else:
                    return Response(
                        {'error': 'Invalid response', 'content': response.text},
                        status=response.status_code
                    )
                    
            except requests.exceptions.RequestException as e:
                return Response(
                    {'error': 'Request failed', 'message': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        return Response(
            {'error': 'Receipt not available after multiple attempts'},
            status=status.HTTP_404_NOT_FOUND
        )

class Test(APIView):
    """
    Returns the wallet address for the authenticated user
    associated with a given Fund (fund_id). Normal users do not have
    their own wallet instance; they simply consult the address using their user id.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        fund_id = request.data.get('fund_id')
        if not fund_id:
            return Response({'error': 'fund_id is required'}, status=400)
        
        # Check that the user is associated to the specified fund
        try:
            investment = FundInvestment.objects.get(investor=request.user, fund__id=fund_id)
        except FundInvestment.DoesNotExist:
            return Response({'error': 'User is not associated with the specified fund'}, status=404)
        
        # For a normal user, simply retrieve the address based on the user id.
        wallet_data, error = get_wallet_index(request.user, fund_id)
        if error or not wallet_data:
            return Response({'error': error or "No wallet index found"}, status=400)
        
        address = wallet_data.get('address')
        return Response({'address': address}, status=200)