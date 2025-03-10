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

from apps.kaleido.models import AppContract, CompileContract, PromoteContract
from apps.fund.models import FundInvestment, TransferReceipt, Fund
from apps.kaleido.serializers.serializer_core import AppContractSerializer, CompileContractSerializer, PromoteContractSerializer
import requests
from requests.auth import HTTPBasicAuth
import json

class AppContractView(APIView):
    serializer_class = AppContractSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        data = dict(validated_data)
        data['membership_id'] = MEMBERSHIP_ID
        data['type'] = 'github'
        
        url = f"https://{CONSOLE_URL}/api/v1//consortia/{CONSORTIA}/contracts/"
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BEARER}',
            }
        
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
                app_contract_id = response_data['_id']
                if not app_contract_id:
                    return Response(
                        {'error': 'Invalid response', 'content': response_data},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                try:
                    instance = serializer.save(user=request.user, app_contract_id=app_contract_id)
                    
                    combined_response = {
                        'kaleido_response': response_data,
                        'devise_response': serializer.data
                    }
                    return Response(combined_response,status=status.HTTP_200_OK)
                except Exception as e:
                    return Response(
                        {'error': 'Failed to save serializer', 'message': str(e)},
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
            
class CompileContractView(APIView):
    serializer_class = CompileContractSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        # Obtener el AppContract asociado
        app_contract_id = validated_data.pop('app_contract_id')
        app_contract = AppContract.objects.get(app_contract_id=app_contract_id)
        
        data = dict(validated_data)
        data['membership_id'] = MEMBERSHIP_ID
        data['evm_version'] = 'constantinople'
        
        # Usar el app_contract_id dinámicamente en la URL
        url = f"https://{CONSOLE_URL}/api/v1/consortia/{CONSORTIA}/contracts/{app_contract_id}/compiled_contracts"
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BEARER}'
        }
        
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
                compiled_contract_id = response_data.get('_id')
                if not compiled_contract_id:
                    return Response(
                        {'error': 'Invalid response', 'content': response_data},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                try:
                    instance = serializer.save(user=request.user, app_contract=app_contract, compiled_contract_id=compiled_contract_id)
                    combined_response = {
                        'kaleido_response': response_data,
                        'devise_response': serializer.data
                    }
                
                    return Response(combined_response, status=status.HTTP_201_CREATED)
                except Exception as e:
                    return Response(
                        {'error': 'Failed to save serializer', 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                return Response(response_data, status=response.status_code)
                
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class PromoteContractView(APIView):
    serializer_class = PromoteContractSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        # Obtener el AppContract asociado
        app_contract_id = validated_data.pop('app_contract_id')
        app_contract = AppContract.objects.get(app_contract_id=app_contract_id)
        
        # Obtener el CompileContract asociado
        compiled_contract_id = validated_data.pop('compiled_contract_id')
        compiled_contract = CompileContract.objects.get(compiled_contract_id=compiled_contract_id)
        
        data = dict(validated_data)
        data['environment_id'] = ENVIRONMENT_ID
        
        url = f"https://{CONSOLE_URL}/api/v1/consortia/{CONSORTIA}/contracts/{app_contract_id}/compiled_contracts/{compiled_contract_id}/promote"
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {BEARER}",
            }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                return Response(
                    {'error': 'Invalid JSON response', 'content': response.text},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            if response.status_code in [200, 201, 202]:
                try:
                    instance = serializer.save(user=request.user, app_contract=app_contract, compiled_contract=compiled_contract)
                    combined_response = {
                        'kaleido_response': response_data,
                        'devise_response': serializer.data
                    }
                    
                    return Response(combined_response, status=status.HTTP_201_CREATED)
                except Exception as e:
                    return Response(
                        {'error': 'Error saving instance', 'content': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
            else:
                return Response(response_data, status=response.status_code)
        
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': 'Request failed', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        