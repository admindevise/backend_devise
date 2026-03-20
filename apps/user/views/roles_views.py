from apps.user.models import Role
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from rest_framework.decorators import permission_classes, action
from rest_framework.generics import ListAPIView
from rest_framework import status, filters, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend

from ..serializers.role_serializer import RoleSerializer


# =============================================================================
#                           APIREST USER RESOURCE
# =============================================================================

class RoleViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar Roles.
    
    Proporciona operaciones completas de CRUD:
    - list: listar todos los roles
    - create: crear un nuevo rol
    - retrieve: obtener detalle de un rol específico
    - update: actualizar un rol existente
    - destroy: eliminar un rol
    
    También incluye acciones adicionales:
    - assign_groups: asignar grupos a un rol
    - deactivate: desactivar un rol sin eliminarlo
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """
        Por defecto muestra solo roles activos, a menos que 
        se especifique el parámetro show_all=true
        """
        queryset = Role.objects.all()
        
        # Obtener el parámetro show_all de la URL
        show_all = self.request.query_params.get('show_all', 'false').lower() == 'true'
        
        # Si no se solicita mostrar todos, filtrar solo los activos
        if not show_all:
            queryset = queryset.filter(status=True)
            
        return queryset

    @action(detail=True, methods=['post'])
    def assign_groups(self, request, pk=None):
        """
        Asignar grupos a un rol específico
        POST /api/roles/{id}/assign_groups/
        """
        role = self.get_object()
        groups_ids = request.data.get('groups', [])
        
        try:
            groups = Group.objects.filter(id__in=groups_ids)
            role.groups.set(groups)
            
            return Response({
                'status': 'success',
                'message': f'Grupos asignados correctamente al rol {role.name}'
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Desactivar un rol sin eliminarlo
        POST /api/role/{id}/deactivate/
        """
        role = self.get_object()
        role.status = False
        role.save()
        
        return Response({
            'status': 'success',
            'message': f'Rol {role.name} desactivado correctamente'
        })

@permission_classes([IsAuthenticated])
class RoleApiListView(ListAPIView):
    serializer_class = RoleSerializer
    queryset = Role.objects.all()
    pagination_class = None
