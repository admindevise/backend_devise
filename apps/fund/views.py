from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user
from config.const_kaleido import CONSORTIA, ENVIRONMENT_ID, USERNAME, PASSWORD, BEARER, SERVICE_HOST, NODE_ID, CONSOLE_URL, SERVICE_WALLET, MEMBERSHIP_ID, ZONE_DOMAIN, USER_ACCOUNTS

import time

from django.utils import timezone
from datetime import timedelta

from apps.fund.models import Fund, FundPrice, FundInvestment, TransferReceipt
from apps.kaleido.models import Wallet
from apps.fund.serializers import FundPriceSerializer, FundSerializer, FundInvestmentSerializer, TransferReceiptSerializer

import requests
from requests.auth import HTTPBasicAuth
import json
from rest_framework.views import APIView
from rest_framework import status
from django.core.cache import cache


""" Wallets """

class ListRuntimeWalletsView(APIView):
    """
    List all services/runtimes in a environment
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        url = f'https://{CONSOLE_URL}/api/v1/consortia/{CONSORTIA}/environments/{ENVIRONMENT_ID}/services'
        
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BEARER}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.json(), status=response.status_code)

class ListWalletsView(APIView):
    """
    List all wallets in a service/runtime
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        url = f'https://{SERVICE_WALLET}/api/v1/wallets'
        
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        
        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.json(), status=response.status_code)

class CreateWalletView(APIView):
    """ 
    Create a new wallet inside a service/runtime for a user
    data :
    - secret: wallet secret (12 prahse)
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        url = f"https://{SERVICE_WALLET}/api/v1/wallets"
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BEARER}'
            }
        
        data = request.data
        
        try: 
            response = requests.post(
                url,
                headers=headers, 
                json=data,
                auth=HTTPBasicAuth(USERNAME, PASSWORD)                
                )
            
            print(response.text)

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                return Response(
                    {'error': 'Invalid JSON response', 'content': response.text},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            if response.status_code in [200, 201,]:
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(
                    response_data,
                    status=response.status_code
                )
        except requests.exceptions.RequestException as e:
            mensaje = f'Error de solicitud: {str(e)}'
            return Response(
                {'error': 'Request failed', 'message': mensaje},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class IndexWalletView(APIView):
    """
    Retrieve a wallet by its index 
    """
    permission_classes = [AllowAny]
    def get(self, request):
        url = f'https://{SERVICE_WALLET}/api/v1/wallets/hcvh45kk/accounts/1'
        
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }   
        
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        
        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.json(), status=response.status_code)

""" Wallets Connect Devise """

class CreateWalletCDView(APIView):
    """ 
    Create a new wallet inside a service/runtime for a user
    data:
    - secret: wallet secret (12 phrase)
    """
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        url = f"https://{SERVICE_WALLET}/api/v1/wallets"
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BEARER}'
        }
        
        data = request.data
        
        try:
            # Crear wallet en el servicio externo
            response = requests.post(
                url,
                headers=headers,
                json=data,
                auth=HTTPBasicAuth(USERNAME, PASSWORD)
            )
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                return Response(
                    {'error': 'Invalid JSON response', 'content': response.text},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            if response.status_code in [200, 201]:
                # Guardar la wallet en nuestro modelo
                try:
                    wallet = Wallet.objects.create(
                        user=request.user,  # Usuario autenticado
                        id_wallet=response_data['id'],
                        secret=data.get('secret', ''),
                        environment_id=ENVIRONMENT_ID,
                        wallet_service=SERVICE_WALLET,
                        zone_domain=ZONE_DOMAIN,
                        consortia=CONSORTIA
                    )
                    return Response(response_data, status=status.HTTP_201_CREATED)
                
                except Exception as e:
                    return Response(
                        {'error': 'Failed to save wallet', 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                return Response(
                    response_data,
                    status=response.status_code
                )
                
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class IndexWalletCDView(APIView):
    """
    Retrieve a wallet by its index using authenticated user's ID
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        # Obtenemos el wallet del usuario autenticado
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            return Response(
                {'error': 'No wallet found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )

        url = f'https://{SERVICE_WALLET}/api/v1/wallets/{wallet.id_wallet}/accounts/{request.user.id}'
        
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }   
        
        try:
            response = requests.get(
                url, 
                headers=headers, 
                auth=HTTPBasicAuth(USERNAME, PASSWORD)
            )
            
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response(
                    response.json(), 
                    status=response.status_code
                )
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

""" Contracts """

class CreateContractView(APIView):
    """
    Create a new contract
    data :
    - name : contract name
    - membership_id : membership id
    - type : contract type (github)
    """
    
    permission_classes = [AllowAny]
    def post(self, request):
        url = f'https://{CONSOLE_URL}/api/v1/consortia/{CONSORTIA}/contracts/'
        
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BEARER}'
            }
        
        data = request.data
        data['membership_id'] = MEMBERSHIP_ID
        
        try: 
            response = requests.post(
                url,
                headers=headers, 
                json=data          
                )

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                return Response(
                    {'error': 'Invalid JSON response', 'content': response.text},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            if response.status_code in [200, 201, 202]:
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(
                    response_data,
                    status=response.status_code
                )
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CompileContractView(APIView):
    """
    Compile a contract
    data :
    - description: contract description
    - membership_id: membership id
    - contract_url: (link github)
    - evm_version: default (constantinople)
    """
    
    permission_classes = [AllowAny]
    def post(self, request):
        # value a 'contract_id' create contract
        contract_id = 'u0jv7vqncj'
        
        url = f'https://{CONSOLE_URL}/api/v1/consortia/{CONSORTIA}/contracts/{contract_id}/compiled_contracts'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BEARER}'
        }
        data = request.data
        data['membership_id'] = MEMBERSHIP_ID
        
        try: 
            response = requests.post(
                url,
                headers=headers, 
                json=data          
                )

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                return Response(
                    {'error': 'Invalid JSON response', 'content': response.text},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            if response.status_code in [200, 201, 202]:
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(
                    response_data,
                    status=response.status_code
                )
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class PromoteContractView(APIView):
    """
    Promote a contract
    data :
    - environment_id: environment id
    - endpoint: name of the endpoint associated with the compiled contract
    """
    permission_classes = [AllowAny]
    def post(self, request):
        # value a 'contract_id' promote contract
        contract_id = 'u0ajnikjus'
        # value a 'compile_contract_id' promote contract
        compile_contract_id = 'u0sjibif5j'
        
        url = f'https://{CONSOLE_URL}/api/v1/consortia/{CONSORTIA}/contracts/{contract_id}/compiled_contracts/{compile_contract_id}/promote'
        
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BEARER}'
            }
        
        data = request.data
        data['environment_id'] = ENVIRONMENT_ID
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data
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

class DeployInstanceOfTokenContract20View(APIView):
    """
    Deploy an instance of the token contract
    data :
    - decimals: number of decimals (default 0)
    - initial_supply: initial supply of the token
    - name: name of the token
    - symbol: symbol of the token
    """
    permission_classes = [AllowAny]
    def post(self, request):
        # value a 'endpoint' promote contract
        endpoint = '721contract'
        # the 'from' address memebership NODE WALLET
        from_address = '0xdc2162b4d2e41beb1d6bc07d2e2ce865235b4cac'
        
        url = f'https://{SERVICE_HOST}/gateways/{endpoint}'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': from_address
        }
        
        data = request.data
        
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

class DeployInstanceOfTokenContract721View(APIView):
    """
    Deploy an instance of the token contract
    data :
    - name: name of the token
    - symbol: symbol of the token
    """
    permission_classes = [AllowAny]
    def post(self, request):
        # value a 'endpoint' promote contract
        endpoint = '721contract'
        # the 'from' address memebership NODE WALLET
        from_address = '0xdc2162b4d2e41beb1d6bc07d2e2ce865235b4cac'
        
        url = f'https://{SERVICE_HOST}/gateways/{endpoint}'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': from_address
        }
        
        data = request.data
        
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

""" Contracts Connect Devise """

class DeployInstanceOfTokenContract721CDView(APIView):
    """
    Deploy an instance of the token contract
    data :
    - name: name of the token
    - symbol: symbol of the token
    """
    permission_classes = [AllowAny]
    def post(self, request):
        # value a 'endpoint' promote contract
        endpoint = '721contract'
        # the 'from' address memebership NODE WALLET
        from_address = '0xdc2162b4d2e41beb1d6bc07d2e2ce865235b4cac'
        
        url = f'https://{SERVICE_HOST}/gateways/{endpoint}'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': from_address
        }
        
        data = request.data
        
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

""" Tokens """

class TransferTokenToAddressUserView(APIView):
    """
    Send token to address user, this is a transaction (simulate a purchase of tokens)
    
    data:
    - amount: amount of tokens to send (integer)
    - recipient: address of the recipient
    """
    
    permission_classes = [AllowAny]
    def post(self, request):
        # the 'from' address memebership NODE WALLET
        from_address = '0x88734cf0eeb46e524f86b9d5a139f42b31462192'
        #value instance of token contract
        instance_token = '0xf4d95a180c4d0fd411618dadbb829f8eb6055ba1'
        
        url = f'https://{SERVICE_HOST}/api/v1/instances/{instance_token}/transfer'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': from_address
            }
        
        data = request.data
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                )
            if response.status_code in [200, 201]:
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

class TransferTokenUserToUserView(APIView):
    """
    Send token from user to user, this is a transaction (simulate a purchase of tokens)
    
    data:
    - amount: amount of tokens to send (integer)
    - recipient: address of the recipient
    """
    def post(self, request):
        #value a service_id (wallet) - hdWallet_id - index
        from_address = 'hd-u0jpuddt9r-juaudvzm-3'
        #value instance of token contract
        instance_token = '0xf4d95a180c4d0fd411618dadbb829f8eb6055ba1'
        
        url = f'https://{SERVICE_HOST}/api/v1/instances/{instance_token}/transfer'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': from_address
            }
        
        data = request.data
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                )
            if response.status_code in [200, 201]:
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

class Mint721View(APIView):
    """
    Mint 721 token
    data :
    - to: address of the recipient without (0x)
    - tokenId: token id
    """
    permission_classes = [AllowAny]
    def post(self, request):
        #value a address DIS
        from_address = '0xdc2162b4d2e41beb1d6bc07d2e2ce865235b4cac'
        
        #value a instance_id
        instance_id = '0x04a7e2459822edbd4b1aa09ebf1e19b713b009d9'
        
        url = f'https://{SERVICE_HOST}/instances/{instance_id}/mint'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': from_address
        }
        
        data = request.data
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
        from_address = 'hd-u0bjjeaxpr-hcvh45kk-27'
        instance_id = '0x04a7e2459822edbd4b1aa09ebf1e19b713b009d9'
        
        # 1. Primero verificar propiedad del token
        owner_url = f'https://{SERVICE_HOST}/instances/{instance_id}/ownerOf'
        owner_data = {
            "tokenId": request.data.get('tokenId')
        }
        
        try:
            # Verificar propietario
            owner_response = requests.post(
                owner_url,
                headers={
                    'accept': 'application/json',
                    'Content-Type': 'application/json',
                    'x-kaleido-from': from_address
                },
                json=owner_data,
                auth=HTTPBasicAuth(USERNAME, PASSWORD)
            )
            
            if owner_response.status_code != 200:
                return Response({
                    'error': 'Failed to verify token ownership',
                    'details': owner_response.json()
                }, status=status.HTTP_400_BAD_REQUEST)

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

class SafeTransfer721View(APIView):
    """
    Safe transfer 721 token
    data :
    - from: address of the sender
    - to: address of the recipient without (0x)
    - tokenId: token id
    """
    permission_classes = [AllowAny]
    def post(self, request):
        #value a address DIS
        from_address = '0xdc2162b4d2e41beb1d6bc07d2e2ce865235b4cac'
        #value a instance_id
        instance_id = '0x04a7e2459822edbd4b1aa09ebf1e19b713b009d9'
        
        url = f'https://{SERVICE_HOST}/instances/{instance_id}/safeTransferFrom'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-kaleido-from': from_address
        }
        
        data = request.data
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

class ReceipStoreView(APIView):
    """
    Store a receipt
    """        
    permission_classes = [AllowAny]
    def get(self, request):
        transfer_id = cache.get('transfer_id')
        
        if not transfer_id:
            return Response(
                {'error': 'No transfer_id found in cache'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        url = f'https://{SERVICE_HOST}/replies/{transfer_id}'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            }
        
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

class OwnerOfView(APIView):
    """
    Call the balanceOf endpoint (acting as ownerOf) in Kaleido.

    data:
    - tokenId: token id
    """
    permission_classes = [AllowAny]

    def post(self, request):
        instance_id = "0x5ca2454f756be6cebb1a741e80341aa612962c45"
        
        url = (
            f"https://{SERVICE_HOST}/instances/{instance_id}/ownerOf"
        )
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {BEARER}",
            "x-kaleido-from": USER_ACCOUNTS
        }
        data = request.data

        try:
            response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(USERNAME, PASSWORD))
            response_data = response.json()
            if response.status_code in [200, 201, 202]:
                return Response(response_data, status=response.status_code)
            else:
                return Response(
                    {"error": "Invalid response", "details": response_data},
                    status=response.status_code
                )
        except requests.exceptions.RequestException as e:
            return Response(
                {"error": "Request failed", "message": str(e)},
                status=500
            )

""" Funds """    
class FundPriceViewSet(viewsets.ViewSet):
    def list(self, request, fund_id, interval):
        now = timezone.now()
        if interval == 'hourly':
            start_time = now - timedelta(hours=1)
        elif interval == 'weekly':
            start_time = now - timedelta(weeks=1)
        elif interval == 'monthly':
            start_time = now - timedelta(days=30)
        elif interval == 'quarterly':
            start_time = now - timedelta(days=90)
        elif interval == 'semiannually':
            start_time = now - timedelta(days=180)
        elif interval == 'annually':
            start_time = now - timedelta(days=365)
        elif interval == '5years':
            start_time = now - timedelta(days=5*365)
        elif interval == '10years':
            start_time = now - timedelta(days=10*365)
        else:
            return Response({'error': 'Invalid interval'}, status=400)

        prices = FundPrice.objects.filter(fund_id=fund_id, timestamp__gte=start_time).order_by('timestamp')
        serializer = FundPriceSerializer(prices, many=True)
        return Response(serializer.data)

class FundViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Fund to be viewed or edited.
    Cada vez que se cree un Fund, se invoca la señal post_save que crea
    la wallet asociada.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FundSerializer

    def get_queryset(self):
        # Listamos los Fund del usuario autenticado
        return Fund.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Asigna el usuario autenticado al fondo
        serializer.save(user=self.request.user)

class FundInvestmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows FundInvestment to be viewed or edited.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FundInvestmentSerializer

    def get_queryset(self):
        # Listamos las inversiones del usuario autenticado
        return FundInvestment.objects.filter(investor=self.request.user)

    def perform_create(self, serializer):
        # Asigna el usuario autenticado a la inversión
        serializer.save(investor=self.request.user)

class TransferReceiptViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows TransferReceipt to be viewed or edited.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TransferReceiptSerializer

    def get_queryset(self):
        # Listamos los recibos de transferencia del usuario autenticado
        return TransferReceipt.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Asigna el usuario autenticado al recibo de transferencia
        serializer.save(user=self.request.user)