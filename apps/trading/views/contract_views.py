# apps/trading/views/contract_views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone

from apps.trading.models import OrderContract
from apps.trading.serializers.contract_serializers import (
    OrderContractSerializer, ContractApprovalSerializer
)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_contracts(request):
    """Lista contratos pendientes de aprobación"""
    
    contracts = OrderContract.objects.filter(
        status='PENDING'
    ).select_related(
        'purchase_order__supplier_user',
        'sales_order__seller_user'
    ).order_by('-created_at')
    
    serializer = OrderContractSerializer(contracts, many=True)
    
    return Response({
        'success': True,
        'count': contracts.count(),
        'contracts': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_contract(request, contract_id):
    """Aprobar o rechazar un contrato"""
    
    try:
        contract = OrderContract.objects.get(id=contract_id)
    except OrderContract.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Contrato no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ContractApprovalSerializer(data=request.data)
    
    if serializer.is_valid():
        new_status = serializer.validated_data['status']
        
        # Actualizar contrato
        contract.status = new_status
        if new_status == 'APPROVED':
            contract.approved_by = request.user
            contract.approved_at = timezone.now()
        
        contract.save()
        
        return Response({
            'success': True,
            'message': f'Contrato {new_status.lower()} exitosamente',
            'contract': OrderContractSerializer(contract).data
        })
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)