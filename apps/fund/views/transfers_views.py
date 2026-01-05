"""
Views para Cesiones (Transfers)
"""

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.fund.models.core import Fund
from apps.fund.models.commissions import Transfers
from apps.fund.serializers.transfer_serializers import (
    TransferCreateSerializer,
    TransferResponseSerializer,
)
from apps.fund.services.transfers import TransferService, TransferServiceError


class TransfersViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver las cesiones de participación.
    
    GET /api/fund/transfers/            --> list
    GET /api/fund/transfers/{id}/       --> retrieve
    """
    queryset = Transfers.objects.select_related('fund').all()
    serializer_class = TransferResponseSerializer
    permission_classes = [IsAuthenticated,]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Filtros automaticos
    filterset_fields = {
        'fund': ['exact'],
        'effective_date': ['exact', 'gte', 'lte'],
        'settlor': ['icontains'],
        'assignee': ['icontains'],
    }
    search_fields = ['settlor', 'assignee', 'actor_settlor', 'actor_assignee']
    ordering_fields = ['created_at', 'effective_date', 'assigned_amount']
    ordering = ['-effective_date']


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_transfer(request):
    """
    Crea una nueva cesión de participación.
    
    POST /api/fund/transfers/create/
    
    Body (multipart/form-data o JSON):
    {
        "fund": 1,
        "effective_date": "2024-01-15",
        "class_transfer": "Clase A",
        "settlor": "Empresa Cedente S.A.S",
        "assignee": "Empresa Cesionario S.A.S",
        "assigned_amount": 1000000.00,
        "actor_settlor": "Juan Pérez",
        "nit_settlor": 900123456,
        "type_doc_settlor": "national identity card",
        "id_doc_settlor": 12345678,
        "actor_assignee": "María García",
        "nit_assignee": 900654321,
        "type_doc_assignee": "national identity card",
        "id_doc_assignee": 87654321,
        "doc_transfer": <archivo> (opcional)
    }
    """
    serializer = TransferCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        transfer = serializer.save()
        response_serializer = TransferResponseSerializer(transfer)
        
        return Response({
            'success': True,
            'message': 'Cesión creada exitosamente',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fund_transfer_summary(request, fund_id):
    """
    Obtiene un resumen de cesiones para un fondo.
    
    GET /api/fund/<fund_id>/transfers/summary/
    """
    try:
        fund = Fund.objects.get(id=fund_id)
    except Fund.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Fondo con ID {fund_id} no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    service = TransferService(fund)
    summary = service.get_fund_transfer_summary(fund)
    
    # Serializar la última cesión si existe
    if summary.get('last_transfer'):
        summary['last_transfer'] = TransferResponseSerializer(
            summary['last_transfer']
        ).data
    
    return Response({
        'success': True,
        'data': summary
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_transfer(request, transfer_id):
    """
    Elimina una cesión.
    
    DELETE /api/fund/transfers/<transfer_id>/delete/
    """
    service = TransferService()
    
    try:
        service.delete_transfer(transfer_id)
        return Response({
            'success': True,
            'message': f'Cesión {transfer_id} eliminada exitosamente'
        }, status=status.HTTP_200_OK)
        
    except TransferServiceError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
