from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.fund.models.core import Fund

from apps.fund.models.accounting import (
    AccountCategory,
    AccountingPeriod,
    AccountingEntry,
    Accountability,
)
from apps.fund.serializers.accounting_serializers import (
    AccountingEntrySerializer,
    AccountingEntryListSerializer,
    AccountingEntryCreateSerializer,
    
    AccountCategorySerializer,
    
    AccountingPeriodSerializer,
    AccountingPeriodListSerializer,
    AccountingPeriodCreateSerializer,
    
    AccountabilitySerializer,
)

class AccountingEntryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AccountingEntryListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AccountingEntryCreateSerializer
        return AccountingEntrySerializer
    
    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return AccountingEntry.objects.select_related('category', 'accountability', 'period').filter(fund_id=fund_id)
    
class AccountCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = AccountCategorySerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return AccountCategory.objects.filter(fund_id=fund_id).order_by('name')

class AccountingPeriodViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AccountingPeriodSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AccountingPeriodCreateSerializer
        return AccountingPeriodSerializer
    
    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return AccountingPeriod.objects.filter(fund_id=fund_id).order_by('-start_date')

class AccountabilityViewSet(viewsets.ModelViewSet):
    serializer_class = AccountabilitySerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return Accountability.objects.filter(fund_id=fund_id).order_by('-created_at')





