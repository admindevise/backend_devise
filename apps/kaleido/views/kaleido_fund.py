from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404
from django.utils import timezone
import datetime

from config.const_kaleido import USERNAME, PASSWORD, BEARER, SERVICE_HOST, USER_ACCOUNTS, SERVICE

from apps.kaleido.utils import is_investor_valid, get_owner_of, get_wallet_index
from apps.fund.models import FundInvestment, TransferReceipt, Fund
from apps.audit.audit_service import AuditService
from apps.kaleido.serializers.serializer_token_operation import (
    TokenMintSerializer, 
    TokenBurnSerializer, 
    PurchaseTokenSerializer, 
    TokenMintBatchSerializer,
    PurchaseTokenIndexToIndexSerializer as PTIS,
    get_batch_creation_progress
    )

import requests
from requests.auth import HTTPBasicAuth
import json

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
    
    # Verificar si el fondo existe
    try:
        fund = Fund.objects.get(id=fund_id)
    except Fund.DoesNotExist:
        return Response({'error': 'Fund not found'}, status=404)
    
    # Verificar propiedad del token
    owner_data, error = get_owner_of(token_id, fund_id)
    if error is not None:
        # Auditar error - No se pudo verificar la propiedad
        AuditService.log_action(
            request=request,
            action_code="TOKEN_BURN",
            obj=fund,
            details={
                'token_id': token_id,
                'error': f"Failed to verify token ownership: {error}",
                'operation': 'burn'
            },
            status='ERROR'
        )
        return Response(
            {"error": "Failed to verify token ownership", "details": error},
                status=400
            )
    
    # Verificar que el token pertenece al remitente
    if owner_data.get('output', '').lower() != USER_ACCOUNTS.lower():
        # Auditar error - Token no pertenece al remitente
        AuditService.log_action(
            request=request,
            action_code="TOKEN_BURN",
            obj=fund,
            details={
                'token_id': token_id,
                'owner': owner_data.get('output'),
                'expected_owner': USER_ACCOUNTS,
                'error': "Token is not owned by the sender",
                'operation': 'burn'
            },
            status='ERROR'
        )
        return Response(
            {
                "message": "You do not have permission to perform this action",
                "owner": owner_data.get('output'),
            },
            status=400
        )
    
    # Auditar inicio del proceso de burn
    initial_audit = AuditService.log_action(
        request=request,
        action_code="TOKEN_BURN",
        obj=fund,
        details={
            'token_id': token_id,
            'operation': 'burn'
        },
        status='PENDING'
    )
    
    try:       
        response_data, error = get_burn_from_kaleido(fund.contract_address, token_id)
        if error:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                AuditService.update_transaction_status(
                    initial_audit.transaction_id, 
                    'ERROR'
                )
            
            # Auditar error - Fallo en la operación de burn
            AuditService.log_action(
                request=request,
                action_code="TOKEN_BURN",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': error,
                    'operation': 'burn'
                },
                status='ERROR'
            )
            return Response({'error': error}, status=400)
        
        # Actualizar estado de auditoría a SUCCESS
        transaction_id = response_data.get('id')
        if initial_audit:
            AuditService.update_transaction_status(
                initial_audit.transaction_id, 
                'SUCCESS',
                transaction_id
            )
        
        # Auditar éxito - Token quemado correctamente
        AuditService.log_action(
            request=request,
            action_code="TOKEN_BURN",
            obj=fund,
            transaction_id=transaction_id,
            details={
                'token_id': token_id,
                'result': response_data,
                'operation': 'burn'
            },
            status='SUCCESS'
        )
        
        return Response(response_data, status=200)
    except Exception as e:
        # Actualizar estado de auditoría a ERROR
        if initial_audit:
            AuditService.update_transaction_status(
                initial_audit.transaction_id, 
                'ERROR'
            )
        
        # Auditar error - Excepción durante el proceso
        AuditService.log_action(
            request=request,
            action_code="TOKEN_BURN",
            obj=fund,
            details={
                'token_id': token_id,
                'error': str(e),
                'operation': 'burn'
            },
            status='ERROR'
        )
        
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def batch_creation_progress_view(request, fund_id):
    """
    Vista para obtener el progreso de creación de tokens en lotes
    
    URL: GET /api/kaleido/fund/{fund_id}/batch-progress/
    
    Query Parameters:
    - start_time: Fecha inicio en formato ISO (opcional)
    
    Ejemplo:
    GET /api/kaleido/fund/1/batch-progress/?start_time=2025-01-15T10:00:00-05:00
    """
    try:
        # Verificar que el fondo existe
        fund = get_object_or_404(Fund, id=fund_id)
        
        # Verificar permisos de acceso al fondo
        if not _has_fund_access(request.user, fund):
            return Response({
                'error': 'No tienes permisos para acceder a este fondo'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Parsear parámetro start_time opcional
        start_time = None
        start_time_str = request.GET.get('start_time')
        
        if start_time_str:
            start_time = parse_datetime(start_time_str)
            if not start_time:
                return Response({
                    'error': 'Formato de start_time inválido. Usa formato ISO: YYYY-MM-DDTHH:MM:SS-05:00'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener datos de progreso
        progress_data = get_batch_creation_progress(fund_id, start_time)
        
        return Response({
            'success': True,
            'fund_id': fund_id,
            'fund_name': fund.name,
            'progress': progress_data,
            'query_params': {
                'start_time': start_time_str,
                'timestamp': datetime.datetime.now(timezone.get_current_timezone())
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error obteniendo progreso del lote: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def _has_fund_access(user, fund):
    """Función auxiliar para verificar acceso al fondo"""
    return (
        user.is_superuser or 
        user.is_staff or
        fund.created_by == user
    )

class Mint721View(APIView):
    """
    Mint 721 token
    data :
    - to: address of the recipient without (0x)
    - tokenId: token id
    """
    permission_classes = [IsAuthenticated]
    def post(self, request):
        token_id = request.data.get('tokenId')
        fund_id = request.data.get('fund_id')
        
        if not token_id:
            return Response({"error": "tokenId is required"}, status=400)
        if not fund_id:
            return Response({"error": "fund_id is required"}, status=400)
        
        try:
            #! 1. Verificar antes si el fondo ya existe
            fund = Fund.objects.get(id=fund_id)
            instance_id = fund.contract_address
            if not instance_id:
                # Auditar error - fondo sin dirección de contrato
                AuditService.log_action(
                    request=request,
                    action_code="TOKEN_CREATE",
                    obj=fund,
                    details={
                        'token_id': token_id,
                        'error': "Fund doesn't have a contract address",
                        'operation': 'mint'
                    },
                    status='ERROR'
                )
                return Response({"error": "Fund doesn't have a contract address"}, status=400)
            
            #! 2. Verificar si el token ya existe
            owner_data, owner_error = get_owner_of(token_id, fund_id)
            if owner_error is None:
                # Si la respuesta es exitosa, el token ya existe
                # Auditar error - token ya existe
                AuditService.log_action(
                    request=request,
                    action_code="TOKEN_CREATE",
                    obj=fund,
                    details={
                        'token_id': token_id,
                        'error': "Token already exists",
                        'owner': owner_data.get('output', None),
                        'operation': 'mint'
                    },
                    status='ERROR'
                )
                return Response({"message": "Token already exists", "owner": owner_data.get('output', None)}, status=400)
        
            url = f'https://{SERVICE_HOST}/instances/{instance_id}/mint'
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json',
                'x-kaleido-from': USER_ACCOUNTS,
            }
            
            data = request.data.copy()
            data['to'] = USER_ACCOUNTS
            to_address = USER_ACCOUNTS
            
            # Auditar inicio del proceso de mint
            initial_audit = AuditService.log_action(
                request=request,
                action_code="TOKEN_CREATE",
                obj=fund,
                details={
                    'token_id': token_id,
                    'to': to_address,
                    'operation': 'mint'
                },
                status='PENDING'
            )
            
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    auth=HTTPBasicAuth(USERNAME, PASSWORD),
                )
                if response.status_code in [200, 201, 202]:
                    response_data = response.json()
                    transaction_id = response_data.get('id')
                    
                    # Actualizar estado de auditoría a SUCCESS
                    if initial_audit:
                        AuditService.update_transaction_status(
                            initial_audit.transaction_id, 
                            'SUCCESS',
                            transaction_id
                        )
                    
                    # Crear nuevo registro de auditoría con el resultado
                    AuditService.log_action(
                        request=request,
                        action_code="TOKEN_CREATE",
                        obj=fund,
                        transaction_id=transaction_id,
                        details={
                            'token_id': token_id,
                            'to': to_address,
                            'result': response_data,
                            'operation': 'mint'
                        },
                        status='SUCCESS'
                    )
                    
                    return Response(response_data, status=response.status_code)
                else:
                    # Actualizar estado de auditoría a ERROR
                    if initial_audit:
                        AuditService.update_transaction_status(
                            initial_audit.transaction_id, 
                            'ERROR'
                        )
                    
                    # Crear nuevo registro de auditoría con el error
                    AuditService.log_action(
                        request=request,
                        action_code="TOKEN_CREATE",
                        obj=fund,
                        details={
                            'token_id': token_id,
                            'to': to_address,
                            'error': response.text,
                            'operation': 'mint'
                        },
                        status='ERROR'
                    )
                    
                    return Response(
                        {'error': 'Invalid response', 'content': response.text},
                        status=response.status_code
                    )
            except requests.exceptions.RequestException as e:
                # Actualizar estado de auditoría a ERROR
                if initial_audit:
                    AuditService.update_transaction_status(
                        initial_audit.transaction_id, 
                        'ERROR'
                    )
                
                # Crear nuevo registro de auditoría con el error
                AuditService.log_action(
                    request=request,
                    action_code="TOKEN_CREATE",
                    obj=fund,
                    details={
                        'token_id': token_id,
                        'to': to_address,
                        'error': str(e),
                        'operation': 'mint'
                    },
                    status='ERROR'
                )
                
                return Response(
                    {'error': 'Request failed', 'message': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Fund.DoesNotExist:
            # Auditar error - fondo no encontrado
            # Necesitaría un objeto para auditar, pero no tenemos el fondo
            # En este caso, podríamos usar un objeto genérico o simplemente no auditar
            # Si se tiene un objeto User, podría usarse ese como objeto para la auditoría
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
        
        # Verificar si el fondo existe
        try:
            fund = Fund.objects.get(id=fund_id)
        except Fund.DoesNotExist:
            return Response({"error": f"Fund with ID {fund_id} not found"}, status=404)
        
        # 2. Verificar que el usuario esté asociado al fondo (inversor)
        investment, error = is_investor_valid(request.user, fund_id)
        if not investment:
            # Auditar intento fallido - usuario no asociado
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': error,
                    'operation': 'safeTransferFrom'
                },
                status='ERROR'
            )
            return Response({"error": error}, status=400)
        
        # 3. Obtener el Fondo y validar que tenga una wallet y contract_address asociada
        fund = investment.fund
        if not fund.hd_wallet:
            # Auditar intento fallido - no hay wallet asociada
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': "The selected fund does not have an associated wallet",
                    'operation': 'safeTransferFrom'
                },
                status='ERROR'
            )
            return Response({"error": "The selected fund does not have an associated wallet"}, status=400)
        wallet = fund.hd_wallet
        
        if not fund.contract_address:
            # Auditar intento fallido - no hay contract_address
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': "The selected fund does not have a contract address",
                    'operation': 'safeTransferFrom'
                },
                status='ERROR'
            )
            return Response({"error": "The selected fund does not have a contract address"}, status=400)
        instance_id = fund.contract_address
        
        # 4. Obtener el token y verificar que pertenezca al usuario
        owner_data, owner_error = get_owner_of(token_id, fund_id)
        if owner_error is not None:
            # Auditar intento fallido - error al verificar propiedad
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': f"Failed to verify token ownership: {owner_error}",
                    'operation': 'safeTransferFrom'
                },
                status='ERROR'
            )
            return Response(
                {"error": "Failed to verify token ownership", "details": owner_error},
                status=400
            )
        
        # 5. Verificar que el token pertenece al usuario
        if owner_data.get('output', '').lower() != USER_ACCOUNTS.lower():
            # Auditar intento fallido - token no pertenece al remitente
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'owner': owner_data.get('output'),
                    'expected_owner': USER_ACCOUNTS,
                    'error': "Token is not owned by the sender",
                    'operation': 'safeTransferFrom'
                },
                status='ERROR'
            )
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
        to_address = data.get('to')
        
        # Auditar inicio de transferencia
        initial_audit = AuditService.log_action(
            request=request,
            action_code="TOKEN_TRANSFER",
            obj=fund,
            details={
                'token_id': token_id,
                'from': USER_ACCOUNTS,
                'to': to_address,
                'operation': 'safeTransferFrom'
            },
            status='PENDING'
        )
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
            )
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                transaction_id = response_data.get('id')
                
                # Crear recibo de transferencia
                receipt = TransferReceipt.objects.create(
                    user=request.user,
                    transfer_id=transaction_id,
                    fund=fund
                )
                
                # Actualizar estado de auditoría a SUCCESS
                if initial_audit:
                    AuditService.update_transaction_status(
                        initial_audit.transaction_id, 
                        'SUCCESS',
                        transaction_id
                    )
                
                # O crear nuevo registro de auditoría con el resultado
                AuditService.log_action(
                    request=request,
                    action_code="TOKEN_TRANSFER",
                    obj=fund,
                    transaction_id=transaction_id,
                    details={
                        'token_id': token_id,
                        'from': USER_ACCOUNTS,
                        'to': to_address,
                        'result': response_data,
                        'receipt_id': receipt.id,
                        'operation': 'safeTransferFrom'
                    },
                    status='SUCCESS'
                )
                
                return Response(response_data, status=response.status_code)
            else:
                # Actualizar estado de auditoría a ERROR
                if initial_audit:
                    AuditService.update_transaction_status(
                        initial_audit.transaction_id, 
                        'ERROR'
                    )
                
                # O crear nuevo registro de auditoría con el error
                AuditService.log_action(
                    request=request,
                    action_code="TOKEN_TRANSFER",
                    obj=fund,
                    details={
                        'token_id': token_id,
                        'from': USER_ACCOUNTS,
                        'to': to_address,
                        'error': response.text,
                        'operation': 'safeTransferFrom'
                    },
                    status='ERROR'
                )
                
            try:
                error_content = response.json()
            except json.JSONDecodeError:
                error_content = response.text
            
            return Response(
                {'error': 'Invalid response', 'content': error_content}, status=response.status_code
            )
        except requests.exceptions.RequestException as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                AuditService.update_transaction_status(
                    initial_audit.transaction_id, 
                    'ERROR'
                )
            
            # O crear nuevo registro de auditoría con el error
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'from': USER_ACCOUNTS,
                    'to': to_address,
                    'error': str(e),
                    'operation': 'safeTransferFrom'
                },
                status='ERROR'
            )
            
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

        # Verificar si el fondo existe
        try:
            fund = Fund.objects.get(id=fund_id)
        except Fund.DoesNotExist:
            return Response({"error": f"Fund with ID {fund_id} not found"}, status=404)

        # 2. Verificar que el usuario esté asociado al fondo (inversor)
        investment, error = is_investor_valid(request.user, fund_id)
        if not investment:
            # Auditar intento fallido - usuario no asociado
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': error,
                    'operation': 'safeTransferIndexToIndex'
                },
                status='ERROR'
            )
            return Response({"error": error}, status=400)
        
        # 3. Obtener el Fondo y validar que tenga una wallet asociada
        fund = investment.fund
        if not fund.hd_wallet:
            # Auditar error - no hay wallet asociada
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': "The selected fund does not have an associated hd_wallet",
                    'operation': 'safeTransferIndexToIndex'
                },
                status='ERROR'
            )
            return Response({"error": "The selected fund does not have an associated hd_wallet"}, status=400)
        wallet = fund.hd_wallet
        
        if not fund.contract_address:
            # Auditar error - no hay contract_address
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': "The selected fund does not have a contract address",
                    'operation': 'safeTransferIndexToIndex'
                },
                status='ERROR'
            )
            return Response({"error": "The selected fund does not have a contract address"}, status=400)
        instance_id = fund.contract_address

        # 4. Obtener la wallet index (wallet general de Kaleido) para validar token ownership
        wallet_index_data, error = get_wallet_index(request.user, fund_id)
        if error:
            # Auditar error - no se encontró wallet index
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': error,
                    'operation': 'safeTransferIndexToIndex'
                },
                status='ERROR'
            )
            return Response({"error": error}, status=400)
        
        general_wallet_address = wallet_index_data.get("address")
        if not general_wallet_address:
            # Auditar error - dirección no encontrada en wallet index
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': "No address found in wallet index data",
                    'operation': 'safeTransferIndexToIndex'
                },
                status='ERROR'
            )
            return Response({"error": "No address found in wallet index data"}, status=400)

        # 5. Verificar que el token pertenece a la wallet general
        owner_data, owner_error = get_owner_of(token_id, fund_id)
        if owner_error is not None:
            # Auditar error - no se pudo verificar propiedad
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'error': f"Failed to verify token ownership: {owner_error}",
                    'operation': 'safeTransferIndexToIndex'
                },
                status='ERROR'
            )
            return Response({"error": "Failed to verify token ownership", "details": owner_error}, status=400)
        
        if owner_data.get('output', '').lower() != general_wallet_address.lower():
            # Auditar error - token no pertenece a wallet general
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'owner': owner_data.get('output'),
                    'expected_owner': general_wallet_address,
                    'error': "Token does not belong to the wallet",
                    'operation': 'safeTransferIndexToIndex'
                },
                status='ERROR'
            )
            return Response({
                    "error": "Token does not belong to the wallet",
                    "owner": owner_data.get("output"),
                    "wallet": general_wallet_address,
                }, status=400)

        # 6. Preparar el payload y realizar la transferencia
        payload = request.data.copy()
        payload['from'] = general_wallet_address
        to_address = payload.get('to')

        # Auditar inicio de transferencia
        initial_audit = AuditService.log_action(
            request=request,
            action_code="TOKEN_TRANSFER",
            obj=fund,
            details={
                'token_id': token_id,
                'from': general_wallet_address,
                'to': to_address,
                'operation': 'safeTransferIndexToIndex'
            },
            status='PENDING'
        )

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
                transaction_id = response_data.get('id')
                
                # Crear recibo de transferencia
                receipt = TransferReceipt.objects.create(
                    user=request.user,
                    transfer_id=transaction_id,
                    fund=fund
                )
                
                # Crear registro de auditoría con el resultado
                AuditService.log_action(
                    request=request,
                    action_code="TOKEN_TRANSFER",
                    obj=fund,
                    transaction_id=transaction_id,
                    details={
                        'token_id': token_id,
                        'from': general_wallet_address,
                        'to': to_address,
                        'result': response_data,
                        'receipt_id': receipt.id,
                        'operation': 'safeTransferIndexToIndex'
                    },
                    status='SUCCESS'
                )
                
                return Response(response_data, status=response.status_code)
            else:
                # Actualizar estado de auditoría a ERROR
                if initial_audit:
                    AuditService.update_transaction_status(
                        initial_audit.id,
                        'ERROR'
                    )
                
                # Auditar error - respuesta inválida
                AuditService.log_action(
                    request=request,
                    action_code="TOKEN_TRANSFER",
                    obj=fund,
                    details={
                        'token_id': token_id,
                        'from': general_wallet_address,
                        'to': to_address,
                        'error': response.text,
                        'operation': 'safeTransferIndexToIndex'
                    },
                    status='ERROR'
                )
                
                return Response(
                    {'error': 'Transfer failed', 'details': response.json()},
                    status=response.status_code
                )
        except requests.exceptions.RequestException as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                AuditService.update_transaction_status(
                    initial_audit.id,
                    'ERROR'
                )
            
            # Auditar error - excepción en la solicitud
            AuditService.log_action(
                request=request,
                action_code="TOKEN_TRANSFER",
                obj=fund,
                details={
                    'token_id': token_id,
                    'from': general_wallet_address,
                    'to': to_address,
                    'error': str(e),
                    'operation': 'safeTransferIndexToIndex'
                },
                status='ERROR'
            )
            
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

class TokenOwnershipView(APIView):
    """
    Verifica el propietario de un token específico en un fondo de inversión.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # 1. Validar datos de entrada
        fund_id = request.data.get('fund_id')
        token_id = request.data.get('tokenId')
        
        if not fund_id:
            return Response({'error': 'fund_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not token_id:
            return Response({'error': 'tokenId is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            fund = Fund.objects.get(id=fund_id)
            
            # 2. Verificar si el usuario es inversor del fondo
            investment, error = is_investor_valid(request.user, fund_id)
            if not investment:
                return Response({"error": error}, status=status.HTTP_403_FORBIDDEN)
            
            # 3. Verificar dirección del contrato
            #fund = investment.fund
            if not fund.contract_address:
                return Response({"error": "Fund contract address not found"}, status=status.HTTP_400_BAD_REQUEST)
                
            # 4. Preparar y hacer la solicitud
            url = f'https://{SERVICE_HOST}/instances/{fund.contract_address}/ownerOf'
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json',
                'x-kaleido-from': USER_ACCOUNTS
            }
            payload = {'tokenId': token_id}
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD)
            )
            
            # 5. Procesar y devolver la respuesta
            try:
                response_data = response.json()
                if response.status_code in [200, 201, 202]:
                    return Response({
                        'owner': response_data['output']
                    }, status=status.HTTP_200_OK)
                else:
                    error_message = response_data.get('error', f'HTTP {response.status_code} error')
                    return Response(
                        {"error": error_message},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response({"error": "Invalid response format"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Fund.DoesNotExist:
            return Response({"error": "Fund not found"}, status=status.HTTP_404_NOT_FOUND)
        except requests.exceptions.RequestException as e:
            return Response({"error": "Connection error", "details": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

class TokenMintView(APIView):
    """
    Endpoint API para crear (mint) tokens para un fondo.
    Solo accesible por administradores.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = TokenMintSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            result = serializer.save()  # Esto llama a create() que ejecuta mint_tokens_for_amount
            
            if result['success'] is True:
                return Response({
                    "status": "success",
                    "message": f"Se han creado {result['minted']} tokens exitosamente",
                    "tokens_minted": result['minted'],
                    "tokens_failed": result['failures'],
                    "details": result['details']
                }, status=status.HTTP_200_OK)
            elif result['success'] == 'partial':
                return Response({
                    "status": "partial",
                    "message": f"Se han creado {result['minted']} tokens con {result['failures']} errores",
                    "tokens_minted": result['minted'],
                    "tokens_failed": result['failures'],
                    "details": result['details']
                }, status=status.HTTP_207_MULTI_STATUS)
            else:
                return Response({
                    "status": "error",
                    "message": result.get('error', f"Error al crear tokens: {result['failures']} fallidos"),
                    "tokens_minted": result['minted'],
                    "tokens_failed": result['failures'],
                    "details": result['details']
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TokenBurnView(APIView):
    """
    Endpoint API para quemar tokens para un fondo.
    Solo accesible por administradores.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = TokenBurnSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Ejecutar la operación de quemar tokens
        result = serializer.save()
        
        # Determinar estado y mensaje según el resultado
        if result.get('success') is True:
            # Crear el diccionario con status y message PRIMERO
            response_data = {
                "status": "success",
                "message": f"Se han quemado {result['burned']} tokens exitosamente",
                "tokens_burned": result.get('burned', 0),
                "tokens_failed": result.get('failures', 0),
                "details": result.get('details', [])
            }
            response_status = status.HTTP_200_OK
            
        elif result.get('success') == 'partial':
            response_data = {
                "status": "partial",
                "message": f"Se han quemado {result['burned']} tokens con {result['failures']} errores",
                "tokens_burned": result.get('burned', 0),
                "tokens_failed": result.get('failures', 0),
                "details": result.get('details', [])
            }
            response_status = status.HTTP_207_MULTI_STATUS
            
        else:
            response_data = {
                "status": "error",
                "message": result.get('error', f"Error al quemar tokens: {result['failures']} fallidos"),
                "tokens_burned": result.get('burned', 0),
                "tokens_failed": result.get('failures', 0), 
                "details": result.get('details', [])
            }
            response_status = status.HTTP_400_BAD_REQUEST
            
        return Response(response_data, status=response_status)

class PurchaseTokenView(APIView):
    """
    Vista para realizar una compra de tokens.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request, *args, **kwargs):
        serializer = PurchaseTokenSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ejecutar la operación de compra de tokens
        result = serializer.save()
        
        # Determinar estado y mensaje según el resultado
        if result.get('success') is True:
            response_data = {
                "status": "success",
                "message": "Compra exitosa",
                "tokens_bought": result.get('bought', 0),
                "tokens_failed": result.get('failures', 0),
                "details": result.get('details', [])
                }
            response_status = status.HTTP_200_OK
        
        elif result.get('success') == 'partial':
            response_data = {
                "status": "partial",
                "message": "Compra parcialmente exitosa",
                "tokens_bought": result.get('bought', 0),
                "tokens_failed": result.get('failures', 0),
                "details": result.get('details', [])
                }
            response_status = status.HTTP_207_MULTI_STATUS
        
        else:
            response_data = {
                "status": "error",
                "message": result.get('error', "Error al comprar tokens"),
                "tokens_bought": result.get('bought', 0),
                "tokens_failed": result.get('failures', 0),
                "details": result.get('details', [])
                }
            response_status = status.HTTP_400_BAD_REQUEST
        
        return Response(response_data, status=response_status)
    
class PurchaseTokenIndexToIndexView(APIView):
    """
    Vista para realizar una compra de tokens desde el mercado secundario
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = PTIS(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = serializer.save()
        
        if result.get('success') is True:
            response_data = {
                "status": "success",
                "message": "Transferencia exitosa",
                "tokens_bought": result.get('bought', 0),
                "tokens_failed": result.get('failures', 0),
                "details": result.get('details', [])
            }
            response_status = status.HTTP_200_OK
            
        elif result.get('success') == 'partial':
            response_data = {
                "status": "partial",
                "message": "Transferencia parcialmente exitosa",
                "tokens_bought": result.get('bought', 0),
                "tokens_failed": result.get('failures', 0),
                "details": result.get('details', [])
            }
            response_status = status.HTTP_207_MULTI_STATUS
        
        else:
            response_data = {
                "status": "error",
                "message": result.get('error', "Error al comprar tokens"),
                "tokens_bought": result.get('bought', 0),
                "tokens_failed": result.get('failures', 0),
                "details": result.get('details', [])
                }
            response_status = status.HTTP_400_BAD_REQUEST
        return Response(response_data, status=response_status)

class TokenMintBatchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = TokenMintBatchSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            results = serializer.save()
            
            # Validación defensiva
            minted = results.get('minted', 0)
            total_requested = results.get('total_requested', 0)
            failures = results.get('failures', 0)
            success = results.get('success', False)
            
            if success:
                message = f"Operación completada: {minted}/{total_requested} tokens creados exitosamente"
                response_status = status.HTTP_200_OK
            elif minted > 0:
                message = f"Operación parcial: {minted}/{total_requested} tokens creados, {failures} fallidos"
                response_status = status.HTTP_207_MULTI_STATUS
            else:
                message = f"Operación fallida: 0/{total_requested} tokens creados"
                response_status = status.HTTP_400_BAD_REQUEST
            
            return Response({
                'status': 'success' if success else ('partial_success' if minted > 0 else 'error'),
                'message': message,
                'data': results
            }, status=response_status)
            
        else:
            return Response({
                'status': 'error',
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
                

class Test(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        
        fund_id = request.data.get('fund_id')
        if not fund_id:
            return Response({'error': 'Fund ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar si el fondo existe
        try:
            fund = Fund.objects.get(id=fund_id)
            
            # Verificar si el usuario es inversor
            investment, error = is_investor_valid(request.user, fund_id)
            if not investment:
                return Response({"error": error}, status=403)
            
            # obtener el fondo y capturar la dirección del contrato
            fund = investment.fund
            if not fund.contract_address:
                return Response({"error": "Fund contract address not found"}, status=400)
            contract_address = fund.contract_address
            
            url = (
                f'https://{SERVICE_HOST}/instances/{contract_address}/ownerOf'
            )
            
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': f'Basic {BEARER}',
                'x-kaleido-from': USER_ACCOUNTS
                }
            
            payload = request.data.copy()
            payload['fund_id'] = fund_id
            
            try:
                response = requests.post(url, headers=headers, json=payload, auth=HTTPBasicAuth(USERNAME, PASSWORD))
                response_data = response.json()
                
                if response.status_code in [200, 201]:
                    return Response(response_data, status=200)
                else:
                    return Response(response_data, status=response.status_code)
            except requests.exceptions.RequestException as e:
                return Response({"error": str(e)}, status=500)
        except Fund.DoesNotExist:
            return Response({"error": "Fund not found"}, status=404)
        