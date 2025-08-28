from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import permission_classes, authentication_classes, action

from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.views.Mixins import DateFilterMixin

from apps.fund.models import Fund, FundInvestment

from apps.fund.serializers.fund_investment_serializers import (
    FundInvestmentSerializer
)
from apps.fund.services.application_service import FundApplicationService
import requests

class FundInvestmentViewSet(DateFilterMixin, viewsets.ModelViewSet):
    serializer_class = FundInvestmentSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    queryset = FundInvestment.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'investor']
    search_fields = ['fund__name', 'investor__email']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def update(self, request, *args, **kwargs):
        """Bloquear actualizaciones PUT"""
        return Response({
            "error": "Update operations are not allowed for fund investments"
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        """Bloquear actualizaciones PATCH"""
        return Response({
            "error": "Partial update operations are not allowed for fund investments"
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def get_queryset(self):
        user = self.request.user
        queryset = FundInvestment.objects.all()
        
        if not user.is_staff:
            queryset = queryset.filter(investor=user)
            
        queryset = self.apply_date_filters(queryset)
        return queryset