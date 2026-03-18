from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from apps.utils.views.Mixins import DateFilterMixin
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.core_permissions.api_permissions import RegistryPermission

from apps.trading.models.core_models import OrderContract
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.fund.models.core import Fund
from apps.trading.serializers.contract_serializers import (
    OrderContractSerializer, ContractApprovalSerializer
)


class OrderContractViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderContractSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]

    filter_backends = [filters.OrderingFilter, filters.SearchFilter, DjangoFilterBackend]
    ordering_fields = ['created_at', 'approved_at']
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')

        queryset = OrderContract.objects.select_related(
            'purchase_order__supplier_user',
            'sales_order__seller_user',
            'purchase_order__fund',
            'sales_order__fund',
            'approved_by'
        ).filter(
            Q(purchase_order__fund_id=fund_id) |
            Q(sales_order__fund_id=fund_id)
        )

        if not user.is_staff:
            queryset = queryset.filter(
                Q(purchase_order__supplier_user=user) |
                Q(sales_order__seller_user=user)
            )

        return self.apply_date_filters(queryset)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request, **kwargs):
        """Lista contratos pendientes de aprobación"""
        contracts = self.get_queryset().filter(status='PENDING').order_by('-created_at')
        serializer = self.get_serializer(contracts, many=True)

        return Response({
            'success': True,
            'count': contracts.count(),
            'contracts': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None, **kwargs):
        """Aprobar o rechazar un contrato"""
        try:
            contract = self.get_queryset().get(id=pk)
        except OrderContract.DoesNotExist:
            raise NotFound("Contrato no encontrado para este fondo o sin acceso.")

        serializer = ContractApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        contract.status = new_status

        if new_status == 'APPROVED':
            contract.approved_by = request.user
            contract.approved_at = timezone.now()

        contract.save()

        return Response({
            'success': True,
            'message': f'Contrato {new_status.lower()} exitosamente',
            'contract': OrderContractSerializer(contract).data
        }, status=status.HTTP_200_OK)