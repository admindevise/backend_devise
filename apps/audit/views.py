from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit.models import AuditLog, AuditAction, AuditCategory
from apps.audit.serializers import AuditLogSerializer, AuditActionSerializer, AuditCategorySerializer
from django.utils import timezone
from datetime import datetime
import pytz

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action__code', 'user__id', 'status', 'content_type__model']
    search_fields = ['transaction_id', 'blockchain_tx_hash', 'object_id']
    ordering_fields = ['created_at', 'action__name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = AuditLog.objects.all()
        
        # Filtrar por rango de fechas si se proporciona
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            # Convertir la cadena a datetime con timezone
            try:
                # Intentar parsear con formato completo (con hora)
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Si falla, intentar solo con fecha
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            
            # Aplicar la zona horaria del proyecto (America/Bogota)
            current_tz = timezone.get_current_timezone()
            start_date_aware = timezone.make_aware(start_date_obj, timezone=current_tz)
            print(f"Filtrado con start_date: {start_date_aware} ({current_tz})")
            queryset = queryset.filter(created_at__gte=start_date_aware)
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                # Si solo se proporciona fecha, establecer la hora al final del día
                end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
                
            # Aplicar la zona horaria del proyecto
            current_tz = timezone.get_current_timezone()
            end_date_aware = timezone.make_aware(end_date_obj, timezone=current_tz)
            print(f"Filtrado con end_date: {end_date_aware} ({current_tz})")
            queryset = queryset.filter(created_at__lte=end_date_aware)
            
        return queryset

class AuditActionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditActionSerializer
    permission_classes = [IsAuthenticated]
    queryset = AuditAction.objects.all()

class AuditCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditCategorySerializer
    permission_classes = [IsAuthenticated]
    queryset = AuditCategory.objects.all()