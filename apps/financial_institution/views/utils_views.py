from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from rest_framework import response, status
from rest_framework.views import APIView

from apps.financial_institution.models.core import (
    FinancialInstitutionApplication,
    FinancialInstitutionApproval,
    FinancialInstitution
)

from apps.financial_institution.serializers.core_serializers import FIApplicationSerializer
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.financial_institution.serializers.utils_serializers import MembersFinancialInstitutionSerializer

from apps.financial_institution.serializers.dashboard_serializers import DashboardStatsSerializer
from apps.financial_institution.services.dashboard_stats_service import DashboardStatsService

from apps.utils.views.Mixins import DateFilterMixin
from apps.utils.views.global_utils_views import validate_entity_exists


# ============================================================
# VIEWS DE MIEMBROS DE INSTITUCIONES FINANCIERAS
# ============================================================
class MembersFinancialInstitutionViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = MembersFinancialInstitutionSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    date_field = 'approval_date'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['max_investment_amount']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['approval_date', 'max_investment_amount']
    ordering = ['-approval_date']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        fi_id = self.kwargs.get('fi_id')
        queryset = FinancialInstitutionApproval.objects.select_related(
            'application__user',
            'application__financial_institution',
        ).filter(application__financial_institution_id=fi_id, status=FinancialInstitutionApproval.ApprovalStatus.ACTIVE
        )
        
        if not user.is_staff:
            queryset = queryset.filter(application__user=user)
            
        return self.apply_date_filters(queryset)


# ============================================================
# FILTRO PARA SOLICITUDES DE INSTITUCIONES FINANCIERAS
# ============================================================
class FiApplicationFilterSet(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(
        choices=FinancialInstitutionApplication.ApplicationStatus.choices
    )
    
    class Meta:
        model = FinancialInstitutionApplication
        fields = ['status']


# ============================================================
# VIEWS DE SOLICITUDES DE INSTITUCIONES FINANCIERAS
# ============================================================
class FinancialInstitutionApplicationViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = FIApplicationSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FiApplicationFilterSet
    search_fields = ['financial_institution__name', 'user__email', 'user__first_name', 'user__last_name', 'user__phone']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        fi_id = self.kwargs.get('fi_id')
        
        if user.is_staff:
            queryset = FinancialInstitutionApplication.objects.select_related(
                'financial_institution', 'user'
            ).filter(financial_institution_id=fi_id).order_by('-created_at')
        else:
            queryset = FinancialInstitutionApplication.objects.select_related(
                    'financial_institution', 'user'
                ).filter(user=user).order_by('-created_at')
        
        return self.apply_date_filters(queryset)


# ============================================================
# VIEWS DE SOLICITUDES DE INSTITUCIONES FINANCIERAS PENDIENTES
# ============================================================
class PendingFinancialInstitutionApplicationViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = FinancialInstitutionApplication.objects.select_related('financial_institution').filter(status=FinancialInstitutionApplication.ApplicationStatus.PENDING)
    serializer_class = FIApplicationSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    date_field = 'created_at'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['requested_investment_amount']
    search_fields = ['financial_institution__name', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)
   

# ============================================================
# VIEWS DE DASHBOARD DE INSTITUCIONES FINANCIERAS
# ============================================================    
class RetrieveDashboardStatsView(APIView):
    """
    Retorna estadísticas clave para el dashboard de una institución financiera
    """
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)
        
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def get(self, request, *args, **kwargs):
        try:
            stats = DashboardStatsService.get_dashboard_stats(use_cache=True)
            serializer = DashboardStatsSerializer(stats)
            return response.Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return response.Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)