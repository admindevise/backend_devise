from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.views.Mixins import DateFilterMixin

from apps.fund.models.membership import FundInvestment

from apps.fund.serializers.investment_serializers import (
    FundInvestmentSerializer
)

class InvestmentViewSet(DateFilterMixin, viewsets.ModelViewSet):
    serializer_class = FundInvestmentSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_methods_names = ['get', 'post']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'investor']
    search_fields = ['fund__name', 'investor__email']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        queryset = FundInvestment.objects.select_related('fund', 'investor').all()
        
        if not user.is_staff:
            queryset = queryset.filter(investor=user)
            
        return self.apply_date_filters(queryset)