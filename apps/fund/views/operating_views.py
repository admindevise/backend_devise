from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets

from apps.fund.models.operating import (
    FundOperatingExpense,
    FundOperatingIncome
)
from apps.fund.serializers.operating_serializers import (
    FundOperatingExpenseSerializer,
    FundOperatingIncomeSerializer
)

class FundOperatingExpenseViewSet(viewsets.ModelViewSet):
    queryset = FundOperatingExpense.objects.all()
    serializer_class = FundOperatingExpenseSerializer
    permission_classes = [IsAuthenticated]

class FundOperatingIncomeViewSet(viewsets.ModelViewSet):
    queryset = FundOperatingIncome.objects.all()
    serializer_class = FundOperatingIncomeSerializer
    permission_classes = [IsAuthenticated]





