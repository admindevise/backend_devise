from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets

from apps.asset.models.operating import (
    AssetOperatingExpense,
    AssetOperatingIncome
)
from apps.asset.serializers.operating_serializers import (
    AssetOperatingExpenseSerializer,
    AssetOperatingIncomeSerializer
)

class AssetOperatingExpenseViewSet(viewsets.ModelViewSet):
    queryset = AssetOperatingExpense.objects.all()
    serializer_class = AssetOperatingExpenseSerializer
    permission_classes = [IsAuthenticated]

class AssetOperatingIncomeViewSet(viewsets.ModelViewSet):
    queryset = AssetOperatingIncome.objects.all()
    serializer_class = AssetOperatingIncomeSerializer
    permission_classes = [IsAuthenticated]





