from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
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
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists


class TransfersViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver las cesiones de participación.

    GET  /fund/<fund_id>/transfers/                     --> list
    GET  /fund/<fund_id>/transfers/{id}/                --> retrieve
    POST /fund/<fund_id>/transfers/create/              --> create_transfer
    GET  /fund/<fund_id>/transfers/summary/             --> fund_transfer_summary
    DELETE /fund/<fund_id>/transfers/{id}/delete/       --> delete_transfer
    """
    serializer_class = TransferResponseSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    parser_classes = [MultiPartParser, FormParser]

    filterset_fields = {
        'fund': ['exact'],
        'effective_date': ['exact', 'gte', 'lte'],
        'settlor': ['icontains'],
        'assignee': ['icontains'],
    }
    search_fields = ['settlor', 'assignee', 'actor_settlor', 'actor_assignee']
    ordering_fields = ['created_at', 'effective_date', 'assigned_amount']
    ordering = ['-effective_date']

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return Transfers.objects.filter(fund_id=fund_id).order_by('-effective_date')

    @action(detail=False, methods=['post'], url_path='create')
    def create_transfer(self, request, **kwargs):
        """
        Crea una nueva cesión de participación.

        POST /fund/<fund_id>/transfers/create/
        """
        serializer = TransferCreateSerializer(
            data=request.data,
            context={
                'request': request,
                'fund_id': self.kwargs.get('fund_id')
            }
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

    @action(detail=False, methods=['get'], url_path='summary')
    def fund_transfer_summary(self, request, **kwargs):
        """
        Obtiene un resumen de cesiones para un fondo.

        GET /fund/<fund_id>/transfers/summary/
        """
        fund_id = self.kwargs.get('fund_id')

        try:
            fund = Fund.objects.get(id=fund_id)
        except Fund.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Fondo con ID {fund_id} no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

        service = TransferService(fund)
        summary = service.get_fund_transfer_summary(fund)

        if summary.get('last_transfer'):
            summary['last_transfer'] = TransferResponseSerializer(
                summary['last_transfer']
            ).data

        return Response({
            'success': True,
            'data': summary
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_transfer(self, request, pk=None, **kwargs):
        """
        Elimina una cesión.

        DELETE /fund/<fund_id>/transfers/<pk>/delete/
        """
        service = TransferService()

        try:
            service.delete_transfer(pk)
            return Response({
                'success': True,
                'message': f'Cesión {pk} eliminada exitosamente'
            }, status=status.HTTP_200_OK)

        except TransferServiceError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)