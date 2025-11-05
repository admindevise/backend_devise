from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.financial_institution.models.core import (
    FinancialInstitutionApplication,
    FinancialInstitutionApproval
)
from apps.financial_institution.serializers.core_serializers import FIApplicationSerializer
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.financial_institution.serializers.utils_serializers import MembersFinancialInstitutionSerializer

from apps.utils.views.Mixins import DateFilterMixin


class MembersFinancialInstitutionViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = MembersFinancialInstitutionSerializer
    permission_classes = [RegistryPermission]
    date_field = 'approval_date'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['max_investment_amount']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['approval_date', 'max_investment_amount']
    ordering = ['-approval_date']
    
    def get_queryset(self):
        user = self.request.user
        queryset = FinancialInstitutionApproval.objects.select_related(
            'application__user',
            'application__financial_institution'
        )
        
        if not user.is_staff:
            queryset = queryset.filter(application__user=user)
            
        return self.apply_date_filters(queryset)


class FinancialInstitutionApplicationViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = FIApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['requested_investment_amount']
    search_fields = ['financial_institution__name', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            return FinancialInstitutionApplication.objects.select_related(
                'financial_institution', 'user'
            ).order_by('-created_at')
        
        return FinancialInstitutionApplication.objects.select_related(
                'financial_institution', 'user'
            ).filter(user=user).order_by('-created_at')

class PendingFinancialInstitutionApplicationViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = FinancialInstitutionApplication.objects.select_related('financial_institution').filter(status='pending')
    serializer_class = FIApplicationSerializer
    permission_classes = [IsAuthenticated]
    date_field = 'created_at'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['requested_investment_amount']
    search_fields = ['financial_institution__name', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    