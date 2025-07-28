from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit.models import AuditLog, AuditAction, AuditCategory
from apps.audit.serializers import AuditLogSerializer, AuditActionSerializer, AuditCategorySerializer
from apps.utils.views.Mixins import DateFilterMixin
from django.utils import timezone
from datetime import datetime
import pytz

class AuditLogViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action__code', 'user__id', 'content_type__model', 'transaction_id']
    search_fields = ['transaction_id', 'object_id', 'user__email', 'action__name']
    ordering_fields = ['created_at', 'action__name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = AuditLog.objects.all()
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        queryset = self.apply_date_filters(queryset)
        
        return queryset

class AuditActionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditActionSerializer
    permission_classes = [IsAuthenticated]
    queryset = AuditAction.objects.all()

class AuditCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditCategorySerializer
    permission_classes = [IsAuthenticated]
    queryset = AuditCategory.objects.all()