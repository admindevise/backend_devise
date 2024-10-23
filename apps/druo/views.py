from .models import Bank, AccountSubtype, AccountType
from .serializers.bank_serializers import BankSerializer
from .serializers.account_serializers import AccountTypeSerializer
from .serializers.accountsubtype_serializers import AccountSubtypeSerializer

from rest_framework.decorators import permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated


# =============================================================================
#                           API VIEWS RESOURCE
# =============================================================================

@permission_classes([IsAuthenticated])
class BanksListView(ListAPIView):
    serializer_class = BankSerializer
    queryset = Bank.objects.filter(status=True)
    pagination_class = None


@permission_classes([IsAuthenticated])
class AccountTypeListView(ListAPIView):
    serializer_class = AccountTypeSerializer
    queryset = AccountType.objects.filter(status=True)
    pagination_class = None

@permission_classes([IsAuthenticated])
class AccountSubtypeListView(ListAPIView):
    serializer_class = AccountSubtypeSerializer
    queryset = AccountSubtype .objects.filter(status=True)
    pagination_class = None

# =============================================================================
#                           BACKOFFICE VIEWS RESOURCE
# =============================================================================

