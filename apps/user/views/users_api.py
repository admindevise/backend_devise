from rest_framework import generics, status, viewsets, mixins, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import permission_classes
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateFromToRangeFilter
import django_filters

from apps.utils.views.global_utils_views import validate_entity_exists
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.user.models import User
from apps.user.serializers.user_detail import UserDetailedSerializer
from apps.user.models import User


# Filtro personalizado para usuarios
class UserFilter(FilterSet):
    # Filtros de fecha con rango
    date_joined_from = django_filters.DateTimeFilter(field_name='date_joined', lookup_expr='gte')
    date_joined_to = django_filters.DateTimeFilter(field_name='date_joined', lookup_expr='lte')
    
    # Filtros de campos específicos
    is_active = django_filters.BooleanFilter()
    is_staff = django_filters.BooleanFilter()
    has_document = django_filters.BooleanFilter(field_name='document_number', lookup_expr='isnull', exclude=True)
    
    # Filtros de texto más avanzados
    email_contains = django_filters.CharFilter(field_name='email', lookup_expr='icontains')
    document_number_exact = django_filters.CharFilter(field_name='document_number', lookup_expr='exact')
    
    class Meta:
        model = User
        fields = {
            'id': ['exact'],
            'email': ['exact', 'icontains'],
            'first_name': ['exact', 'icontains', 'istartswith'],
            'last_name': ['exact', 'icontains', 'istartswith'],
            'document_number': ['exact', 'icontains'],
            'phone': ['exact', 'icontains'],
            'is_active': ['exact'],
            'is_staff': ['exact'],
            'groups': ['exact'],
            'role': ['exact'],
            'local_id_type': ['exact'],
        }


class ListUsersAPIView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailedSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    # Configuración de filtros
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['first_name', 'last_name', 'email', 'document_number', 'phone']
    ordering_fields = ['id', 'email', 'first_name', 'last_name', 'date_joined', 'last_login']
    ordering = ['-date_joined']  # Orden predeterminado
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        return super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        """Obtiene el queryset basado en los permisos del usuario"""
        queryset = User.objects.filter(is_staff=False)
        
        # Aplica filtros adicionales si es necesario
        if self.request.query_params.get('active_only') == 'true':
            queryset = queryset.filter(is_active=True)
        
        if self.request.query_params.get('include_staff') == 'true':
            queryset = User.objects.all()
            
        return queryset