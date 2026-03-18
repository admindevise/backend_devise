"""
Views para Comisiones (Commissions)
"""

from rest_framework import status
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists

from apps.fund.models.core import Fund
from apps.fund.models.commissions import Commissions
from apps.fund.serializers.commissions_serializers import (
    CommissionResponseSerializer,
    CommissionCreateSerializer,
    CommissionListSerializer,
)
from apps.fund.services.commissions import CommissionService, CommissionServiceError


# ============================================================================
# VIEWSET SOLO LECTURA
# ============================================================================

class CommissionsViewSet(ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Comisiones.
    
    GET /api/fund/commissions/          -> list
    GET /api/fund/commissions/{id}/     -> retrieve
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Filtros automáticos
    filterset_fields = {
        'fund': ['exact'],
        'name': ['exact', 'icontains'],
        'contract_num': ['exact', 'icontains'],
    }
    
    # Búsqueda por texto
    search_fields = ['name', 'description', 'contract_num', 'amount']
    
    # Ordenamiento
    ordering_fields = ['created_at', 'name', 'contract_num']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
        
    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return Commissions.objects.filter(fund_id=fund_id).order_by('-created_at')
    
    def get_serializer_class(self):
        """Retorna el serializer según la acción."""
        if self.action == 'list':
            return CommissionListSerializer
        return CommissionResponseSerializer
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/fund/commissions/
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'total_count': queryset.count(),
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/fund/commissions/{id}/
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })


# ============================================================================
# FUNCIONES PARA ESCRITURA
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_commission(request):
    """
    Crea una nueva comisión.
    
    POST /api/fund/commissions/create/
    
    Body (JSON):
    {
        "fund": 1,
        "contract_num": "5.1",
        "name": "Comisión de Administración",
        "description": "Comisión mensual por administración del fondo",
        "amount": "0.5% del AUM"
    }
    """
    serializer = CommissionCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = CommissionService()
        commission = service.create_commission(
            fund=serializer.validated_data['fund'],
            contract_num=serializer.validated_data['contract_num'],
            name=serializer.validated_data['name'],
            description=serializer.validated_data['description'],
            amount=serializer.validated_data['amount'],
        )
        
        response_serializer = CommissionResponseSerializer(commission)
        
        return Response({
            'success': True,
            'message': 'Comisión creada exitosamente',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except CommissionServiceError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_commission(request, commission_id):
    """
    Actualiza una comisión existente.
    
    PUT/PATCH /api/fund/commissions/{commission_id}/update/
    
    Body (JSON):
    {
        "name": "Nuevo nombre",
        "description": "Nueva descripción",
        "amount": "1% del AUM"
    }
    """
    service = CommissionService()
    
    try:
        commission = service.update_commission(
            commission_id=commission_id,
            update_data=request.data
        )
        
        response_serializer = CommissionResponseSerializer(commission)
        
        return Response({
            'success': True,
            'message': 'Comisión actualizada exitosamente',
            'data': response_serializer.data
        })
        
    except CommissionServiceError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_commission(request, commission_id):
    """
    Elimina una comisión.
    
    DELETE /api/fund/commissions/{commission_id}/delete/
    """
    service = CommissionService()
    
    try:
        service.delete_commission(commission_id)
        
        return Response({
            'success': True,
            'message': f'Comisión {commission_id} eliminada exitosamente'
        })
        
    except CommissionServiceError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
