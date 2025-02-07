from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user
from config.const_kaleido import CONSORTIA, ENVIRONMENT_ID, USERNAME, PASSWORD, BEARER, SERVICE_HOST, NODE_ID, CONSOLE_URL, SERVICE_WALLET, MEMBERSHIP_ID, ZONE_DOMAIN, USER_ACCOUNTS, SERVICE

from apps.kaleido.models import Wallet

import requests
from requests.auth import HTTPBasicAuth
import json


@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def create_wallet_for_user(user, secret):
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

def get_owner_of(token_id):
    """
    Calls the ownerOf endpoint to get the owner of a token.
    Input:
      - token_id: ID of the token to check ownership for.
    Returns:
      - A tuple (response_data, error), where response_data is the JSON response on success,
        or error contains an error message on failure.
    """
    
    instance_id = '0x04a7e2459822edbd4b1aa09ebf1e19b713b009d9'
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

def get_wallet_index(user):
    """
    Retrieves the wallet index for the given user.
    
    Returns:
      A tuple (data, error) where data is the JSON response from the external service
      if successful, or error is a string with the error message.
    """
    try:
        wallet = Wallet.objects.get(user=user)
    except Wallet.DoesNotExist:
        return None, "No wallet found for this user"
    
    url = f"https://{SERVICE_WALLET}/api/v1/wallets/hcvh45kk/accounts/{user.id}"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(settings.USERNAME, settings.PASSWORD))
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error from service: {response.json()}"
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"
 
""" Tokens """
def mint_721_token(wallet, token_id, token_uri):
    #value a instance_id
    instance_id = '0x04a7e2459822edbd4b1aa09ebf1e19b713b009d9'
        
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
        if not token_id:
            return Response({"error": "tokenId is required"}, status=400)
        
        # Verificar antes si el token ya existe
        owner_data, owner_error = get_owner_of(token_id)
        if owner_error is None:
            # Si la respuesta es exitosa, el token ya existe
            return Response({"message": "Token already exists", "owner": owner_data.get('output', None)}, status=400)
        
        
        #value a smartcontract token instance_id
        instance_id = '0x04a7e2459822edbd4b1aa09ebf1e19b713b009d9'
        url = f'https://{SERVICE_HOST}/instances/{instance_id}/mint'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': USER_ACCOUNTS,
        }
        
        data = request.data
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
            
class SafeTransfer721View(APIView):
    """
    Safe transfer 721 token
    data :
    - from: current owner of the token
    - to: address to receive the ownership of the given token ID
    - tokenId: token id
    """
    permission_classes = [AllowAny]
    def post(self, request):
        token_id = request.data.get('tokenId')
        sender = request.data.get('from')
        if not token_id:
            return Response({"error": "tokenId is required"}, status=400)
        
        # Verificar que el token existe y que es propiedad del 'from' proporcionado
        owner_data, owner_error = get_owner_of(token_id)
        if owner_error is not None:
            return Response(
                {"error": "Failed to verify token ownership", "details": owner_error},
                status=400
            )
        
        if owner_data.get('output') != sender:
            return Response(
                {
                    "message": "Token is not owned by the sender",
                    "owner": owner_data.get('output')
                },
                status=400
            )
            
        #value a instance_id
        instance_id = '0x04a7e2459822edbd4b1aa09ebf1e19b713b009d9'
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
    permission_classes = [AllowAny]
    def post(self, request):        
        token_id = request.data.get('tokenId')
        sender = request.data.get('from')
        if not token_id:
            return Response({"error": "tokenId is required"}, status=400)
        
        # Verificar que el token existe y que es propiedad del 'from' proporcionado
        owner_data, owner_error = get_owner_of(token_id)
        if owner_error is not None:
            return Response(
                {"error": "Failed to verify token ownership", "details": owner_error},
                status=400
            )
        
        if owner_data.get('output') != sender:
            return Response(
                {
                    "message": "Token is not owned by the sender",
                    "owner": owner_data.get('output')
                },
                status=400
            )
        
        try:

            # 2. Si no es propietario, verificar si está aprobado
            if owner_response.json()['output'] != request.data.get('from'):
                approval_url = f'https://{SERVICE_HOST}/instances/{instance_id}/getApproved'
                approval_response = requests.post(
                    approval_url,
                    headers={
                        'accept': 'application/json',
                        'Content-Type': 'application/json',
                        'x-kaleido-from': from_address
                    },
                    json=owner_data,
                    auth=HTTPBasicAuth(USERNAME, PASSWORD)
                )
                
                if approval_response.status_code != 200:
                    return Response({
                        'error': 'Not authorized to transfer token',
                        'details': 'Caller is not owner nor approved'
                    }, status=status.HTTP_403_FORBIDDEN)

            # 3. Proceder con la transferencia
            from_address = f'hd-{SERVICE}-hcvh45kk-{request.user.id}'
            instance_id = '0x04a7e2459822edbd4b1aa09ebf1e19b713b009d9'
            url = f'https://{SERVICE_HOST}/instances/{instance_id}/safeTransferFrom'
            response = requests.post(
                url,
                headers={
                    'accept': 'application/json',
                    'Content-Type': 'application/json',
                    'x-kaleido-from': from_address
                },
                json=request.data,
                auth=HTTPBasicAuth(USERNAME, PASSWORD)
            )
            
            data = request.data
            data['from'] = USER_ACCOUNTS
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                cache.set('transfer_id', response_data['id'])
                return Response(response_data, status=response.status_code)
            
            return Response(
                {'error': 'Transfer failed', 'details': response.json()},
                status=response.status_code
            )
            
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )