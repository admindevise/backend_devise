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

from apps.audit.audit_service import AuditService
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
        
        # Auditar inicio del proceso de creación de contrato
        # Buscar un objeto AppContract existente para usar como referencia
        try:
            reference_obj = AppContract.objects.filter(user=request.user).first()
            
            if not reference_obj:
                # Si este usuario no tiene AppContracts, intentar con cualquiera
                reference_obj = AppContract.objects.first()
                
            # Si aún no hay ninguno, usamos el usuario como último recurso
            if not reference_obj:
                reference_obj = request.user
                
            initial_audit = AuditService.log_action(
                request=request,
                action_code="SC_CREATE",
                obj=reference_obj,
                details={
                    'name': data.get('name'),
                    'operation': 'create_app_contract'
                },
                status='PENDING'
            )
        except Exception as e:
            # Si hay algún error al crear el registro de auditoría, continuamos pero lo registramos
            initial_audit = None
            print(f"Error creating initial audit record: {str(e)}")
            
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
                # Actualizar estado de auditoría a ERROR
                if initial_audit:
                    initial_audit.status = 'ERROR'
                    initial_audit.save(update_fields=['status'])
                
                return Response(
                    {'error': 'Invalid JSON response', 'content': response.text},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            if response.status_code in [200, 201, 202]:
                app_contract_id = response_data['_id']
                if not app_contract_id:
                    # Actualizar estado de auditoría a ERROR
                    if initial_audit:
                        initial_audit.status = 'ERROR'
                        initial_audit.save(update_fields=['status'])
                    
                    return Response(
                        {'error': 'Invalid response, no app_contract_id', 'content': response_data},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                    
                try:
                    instance = serializer.save(user=request.user, app_contract_id=app_contract_id)
                    
                    
                    # Actualizar el registro de auditoría inicial a SUCCESS
                    if initial_audit:
                        initial_audit.status = 'SUCCESS'
                        initial_audit.transaction_id = None
                        # Nota: blockchain_tx_hash queda reservado para cuando se tenga un hash real de blockchain
                        initial_audit.save(update_fields=['status', 'transaction_id'])
                    
                    combined_response = {
                        'kaleido_response': response_data,
                        'devise_response': serializer.data
                    }
                    return Response(combined_response, status=status.HTTP_201_CREATED)
                    
                except Exception as e:
                    # Actualizar estado de auditoría a ERROR
                    if initial_audit:
                        initial_audit.status = 'ERROR'
                        initial_audit.save(update_fields=['status'])
                    
                    return Response(
                        {'error': 'Failed to save serializer', 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                # Actualizar estado de auditoría a ERROR
                if initial_audit:
                    initial_audit.status = 'ERROR'
                    initial_audit.save(update_fields=['status'])
                
                return Response(
                    response_data,
                    status=response.status_code
                )
                
        except requests.exceptions.RequestException as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.save(update_fields=['status'])
            
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
        
        try:
            app_contract = AppContract.objects.get(app_contract_id=app_contract_id)
        except AppContract.DoesNotExist:
            return Response(
                {'error': 'App contract not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        data = dict(validated_data)
        data['membership_id'] = MEMBERSHIP_ID
        data['evm_version'] = 'constantinople'
        
        # No crear registro de auditoría inicial para evitar problemas de tipo de contenido
        # Este enfoque eliminará el problema de contenttype=app_contract
        
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
                        {'error': 'Invalid response, no compiled_contract_id', 'content': response_data},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                try:
                    instance = serializer.save(user=request.user, app_contract=app_contract, compiled_contract_id=compiled_contract_id)
                    
                    # Crear registro de auditoría SOLO cuando la operación es exitosa
                    # y usando la instancia correcta de CompileContract
                    AuditService.log_action(
                        request=request,
                        action_code="SC_COMPILE",
                        obj=instance,  # Usar la instancia de CompileContract aquí
                        # No incluir transaction_id ya que no aplica para este caso
                        details={
                            'description': instance.description,
                            'contract_url': instance.contract_url,
                            'app_contract_id': app_contract_id,
                            'compiled_contract_id': compiled_contract_id,
                            'operation': 'compile_contract'
                        },
                        status='SUCCESS'
                    )
                    
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
        
        try:
            app_contract = AppContract.objects.get(app_contract_id=app_contract_id)
        except AppContract.DoesNotExist:
            return Response(
                {'error': 'App contract not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener el CompileContract asociado
        compiled_contract_id = validated_data.pop('compiled_contract_id')
        
        try:
            compiled_contract = CompileContract.objects.get(compiled_contract_id=compiled_contract_id)
        except CompileContract.DoesNotExist:
            return Response(
                {'error': 'Compiled contract not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        data = dict(validated_data)
        data['environment_id'] = ENVIRONMENT_ID
        
        # NO crear registro de auditoría inicial para evitar problemas de content_type
        
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
                    
                    # Crear UN SOLO registro de auditoría con el objeto correcto (PromoteContract)
                    # y sin usar transaction_id si no es necesario
                    transaction_id = response_data.get('id')
                    AuditService.log_action(
                        request=request,
                        action_code="SC_PROMOTE",
                        obj=instance,  # Usar la instancia de PromoteContract
                        transaction_id=transaction_id if transaction_id else None,
                        details={
                            'endpoint': instance.endpoint,
                            'app_contract_id': app_contract_id,
                            'compiled_contract_id': compiled_contract_id,
                            'result': response_data,
                            'operation': 'promote_contract'
                        },
                        status='SUCCESS'
                    )
                    
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