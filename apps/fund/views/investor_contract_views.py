from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound

from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.fund.models.membership import InvestorContract
from apps.fund.models.core import Fund
from apps.fund.serializers.invester_contract_serializers import (
    InvestorContractSerializer,
    InvestorContractCreateSerializer,
    InvestorContractSignSerializer,
)

class InvestorContractViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InvestorContract.objects.all()
    serializer_class = InvestorContractSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        if self.kwargs.get('pk'):
            validate_entity_exists(InvestorContract, 'Contrato de inversor', self.kwargs.get('pk'))
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        
        queryset = self.queryset
        if fund_id:
            if not Fund.objects.filter(id=fund_id).exists():
                raise NotFound(
                    detail=f'El fideicomiso con ID {fund_id} no existe.',
                    code=404
                )
            queryset = queryset.filter(fund_id=fund_id)
        
        if not user.is_staff:
            queryset = queryset.filter(user=user)
        
        return queryset

    @action(detail=False, methods=['post'], url_path='create')
    def create_investor_contract(self, request, **kwargs):
        """Crear nuevo contrato de inversor"""
        serializer = InvestorContractCreateSerializer(
            data=request.data,
            context={
                'request': request,
                'fund_id': self.kwargs.get('fund_id')
            }
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='sign')
    def sign_investor_contract(self, request, pk=None, **kwargs):
        """
        Firmar un contrato de inversor existente
        """
        serializer = InvestorContractSignSerializer(
            data=request.data,
            context={'request': request, 'contract': pk}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)