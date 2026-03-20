from .models import Bank, AccountSubtype, AccountType
from .serializers.bank_serializers import BankSerializer
from .serializers.account_serializers import AccountTypeSerializer
from .serializers.accountsubtype_serializers import AccountSubtypeSerializer

from rest_framework.decorators import permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.financial_institution.models.core import FinancialInstitution


# =============================================================================
#                           API VIEWS RESOURCE
# =============================================================================

@permission_classes([IsAuthenticated, RegistryPermission])
class BanksListView(ListAPIView):
    serializer_class = BankSerializer
    queryset = Bank.objects.filter(status=True)
    pagination_class = None
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)


@permission_classes([IsAuthenticated, RegistryPermission])
class AccountTypeListView(ListAPIView):
    serializer_class = AccountTypeSerializer
    queryset = AccountType.objects.filter(status=True)
    pagination_class = None
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)

@permission_classes([IsAuthenticated, RegistryPermission])
class AccountSubtypeListView(ListAPIView):
    serializer_class = AccountSubtypeSerializer
    queryset = AccountSubtype .objects.filter(status=True)
    pagination_class = None
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)