from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.fund.models.core import Fund

from apps.fund.models.operating import (
    FundOperatingExpense,
    FundOperatingIncome
)
from apps.fund.serializers.operating_serializers import (
    FundOperatingExpenseSerializer,
    FundOperatingIncomeSerializer
)

class FundOperatingExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = FundOperatingExpenseSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return FundOperatingExpense.objects.filter(fund_id=fund_id)

class FundOperatingIncomeViewSet(viewsets.ModelViewSet):
    serializer_class = FundOperatingIncomeSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return FundOperatingIncome.objects.filter(fund_id=fund_id)





