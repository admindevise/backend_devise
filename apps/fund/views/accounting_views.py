from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated

from apps.fund.models.accounting import AccountCategory, AccountingPeriod, AccountingEntry
from apps.fund.serializers.accounting_serializers import (
    AccountingEntrySerializer,
    AccountingEntryListSerializer,
    AccountingEntryCreateSerializer,
    
    AccountCategorySerializer,
    
    AccountingPeriodSerializer,
    AccountingPeriodListSerializer,
    AccountingPeriodCreateSerializer,
)

class AccountingEntryViewSet(viewsets.ModelViewSet):
    queryset = AccountingEntry.objects.all()
    permission_classes = []
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AccountingEntryListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AccountingEntryCreateSerializer
        return AccountingEntrySerializer
    
class AccountCategoryViewSet(viewsets.ModelViewSet):
    queryset = AccountCategory.objects.all()
    serializer_class = AccountCategorySerializer
    permission_classes = []

class AccountingPeriodViewSet(viewsets.ModelViewSet):
    queryset = AccountingPeriod.objects.all()
    permission_classes = []
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AccountingPeriodSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AccountingPeriodCreateSerializer
        return AccountingPeriodSerializer



