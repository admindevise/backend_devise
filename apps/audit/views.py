from django.db.models import Q
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit.models import AuditLog, AuditAction, AuditCategory
from apps.audit.serializers import AuditLogSerializer, AuditActionSerializer, AuditCategorySerializer

from apps.utils.views.Mixins import DateFilterMixin
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists

from apps.financial_institution.models.core import FinancialInstitution

class AuditLogViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action__code', 'user__id', 'content_type__model', 'transaction_id', 'action__category__code']
    search_fields = ['transaction_id', 'object_id', 'user__email', 'action__name']
    ordering_fields = ['created_at', 'action__name']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        if self.kwargs.get('pk'):
            validate_entity_exists(AuditLog, 'Registro de auditoría', self.kwargs.get('pk'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        fund_id = self.request.query_params.get('fund_id')
    
        queryset = AuditLog.objects.select_related('user', 'action__category', 'content_type').filter(
            Q(fund_id=fund_id) if fund_id else Q()
        )
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        queryset = self.apply_date_filters(queryset)
        
        return queryset

class AuditActionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditActionSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        if self.kwargs.get('pk'):
            validate_entity_exists(AuditAction, 'Acción de auditoría', self.kwargs.get('pk'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = AuditAction.objects.select_related('category')
        return queryset
        

class AuditCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditCategory.objects.all()
    serializer_class = AuditCategorySerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        if self.kwargs.get('pk'):
            validate_entity_exists(AuditCategory, 'Categoría de auditoría', self.kwargs.get('pk'))
        super().initial(request, *args, **kwargs)