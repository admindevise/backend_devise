from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from apps.utils.views.Mixins import DateFilterMixin
from rest_framework import status, viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend

from apps.trading.models.core_models import OrderContract
from apps.fund.models.core import Fund
from apps.trading.serializers.contract_serializers import (
    OrderContractSerializer, ContractApprovalSerializer
)
from apps.trading.views.utils_views import validate_entity_exists

class OrderContractListView(DateFilterMixin,viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderContractSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [filters.OrderingFilter, filters.SearchFilter, DjangoFilterBackend]
    #filterset_fields = ['status', 'approved_by', 'purchase_order__supplier_user', 'sales_order__seller_user']
    #search_fields = ['purchase_order__order_number', 'sales_order__order_number']
    ordering_fields = ['created_at', 'approved_at']
    ordering = ['-created_at']
    
    def get_queryset(self):        
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        queryset = OrderContract.objects.select_related(
            'purchase_order__supplier_user',
            'sales_order__seller_user',
            'purchase_order__fund',
            'sales_order__fund',
            'approved_by'
        )
        
        if fund_id:
            if not Fund.objects.filter(id=fund_id).exists():
                raise NotFound(
                    detail=f'El fideicomiso con ID {fund_id} no existe.',
                    code=404
                )
            queryset = queryset.filter(
                Q(purchase_order__fund_id=fund_id) | 
                Q(sales_order__fund_id=fund_id)
            )        
        
        if not user.is_staff:
            queryset = queryset.filter(
                Q(purchase_order__supplier_user=user) |
                Q(sales_order__seller_user=user)
            )
        
        return self.apply_date_filters(queryset)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_contracts(request, fund_id):
    """Lista contratos pendientes de aprobación"""
    validate_entity_exists(Fund, 'Fideicomiso', fund_id)
    contracts = OrderContract.objects.filter(
        status='PENDING',
    ).filter(
        Q(purchase_order__fund_id=fund_id) |
        Q(sales_order__fund_id=fund_id)
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
def approve_contract(request, fund_id, contract_id):
    """Aprobar o rechazar un contrato"""
    validate_entity_exists(Fund, 'Fideicomiso', fund_id)
    validate_entity_exists(OrderContract, 'Contrato', contract_id)
    contract = OrderContract.objects.get(id=contract_id)
    
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