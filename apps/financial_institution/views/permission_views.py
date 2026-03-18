from rest_framework import viewsets, status, filters, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.utils.core_permissions.api_permissions import RegistryPermission
from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.views.global_utils_views import validate_entity_exists

from apps.financial_institution.models.permissions import (
    FIPermission,
    FICustomGroup,
    FIUserGroupMembership
)
from apps.financial_institution.models.core import FinancialInstitution
from apps.financial_institution.serializers.permission_serializers import (
    FIPermissionSerializer,
    FIPermissionListSerializer,
    FICustomGroupSerializer,
    FICustomGroupCreateSerializer,
    FICustomGroupUpdateSerializer,
    FIUserGroupMembershipSerializer,
    AssignUserToGroupSerializer,
    RemoveUserFromGroupSerializer
)


# ===================================================
# VIEWSETS PARA PERMISOS
# ===================================================
class FIPermissionViewSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    """
    ViewSet de solo lectura para permisos disponibles
    
    Endpoints:
    - GET /permissions/ - Listar todos los permisos
    - GET /permissions/{id}/ - Detalle de un permiso
    - GET /permissions/by-category/ - Permisos agrupados por categoría
    - GET /permissions/by-module/ - Permisos agrupados por módulo
    - GET /permissions/available_for_group/ - Permisos disponibles para asignar a un grupo
    """
    queryset = FIPermission.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, RegistryPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'module', 'is_active']
    search_fields = ['name', 'description', 'codename']
    ordering_fields = ['module', 'category', 'name']
    ordering = ['module', 'category', 'name']
    
    def initial(self, request, *args, **kwargs):
        fi_id = self.kwargs.get('fi_id')
        pk = self.kwargs.get('pk')

        if fi_id:
            validate_entity_exists(FinancialInstitution, 'Institución financiera', fi_id)

        # Solo validar permiso cuando la URL trae pk (acciones detail=True)
        if pk is not None:
            validate_entity_exists(FIPermission, 'Permiso', pk)

        super().initial(request, *args, **kwargs)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            'request': self.request,
            'fi_id': self.kwargs.get('fi_id')
        })
        return context
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FIPermissionSerializer
        return FIPermissionListSerializer
    
    @action(detail=False, methods=['get'], url_path='by-category')
    def by_category(self, request, **kwargs):
        """
        Agrupar permisos por categoría
        
        GET /permissions/by_category/
        GET /permissions/by_category/?module=fi
        
        Response:
        {
            "applications": [
                {"id": 1, "codename": "view_applications", "name": "Ver Solicitudes"},
                ...
            ],
            "members": [...],
            ...
        }
        """
        module = request.query_params.get('module', 'fi')
        
        permissions = FIPermission.objects.filter(
            module=module,
            is_active=True
        ).order_by('category', 'name')
        
        grouped = {}
        for perm in permissions:
            category = perm.category
            if category not in grouped:
                grouped[category] = []
            
            grouped[category].append({
                'id': perm.id,
                'codename': perm.codename,
                'name': perm.name,
                'description': perm.description
            })
        
        return Response(grouped)
    
    @action(detail=False, methods=['get'], url_path='by-module')
    def by_module(self, request, **kwargs):
        """
        Agrupar permisos por módulo
        
        GET /permissions/by_module/
        
        Response:
        {
            "fi": [
                {"id": 1, "codename": "view_applications", "name": "Ver Solicitudes"},
                ...
            ],
            "fund": [...],
            ...
        }
        """
        permissions = FIPermission.objects.filter(is_active=True).order_by('module', 'name')
        
        grouped = {}
        for perm in permissions:
            module = perm.module
            if module not in grouped:
                grouped[module] = []
            
            grouped[module].append({
                'id': perm.id,
                'codename': perm.codename,
                'name': perm.name,
                'category': perm.category,
                'description': perm.description
            })
        
        return Response(grouped)
    
    @action(detail=False, methods=['get'], url_path='available-for-group')
    def available_for_group(self, request, **kwargs):
        """
        Obtener permisos disponibles para asignar a un grupo
        Útil para formularios de creación/edición de grupos
        
        GET /permissions/available-for-group/?group_id=5
        
        Response:
        {
            "total_available": 14,
            "permissions_by_category": {
                "applications": [...],
                "members": [...]
            },
            "already_assigned": [1, 2, 3]  # IDs de permisos ya asignados al grupo
        }
        """
        group_id = request.query_params.get('group_id')
        module = request.query_params.get('module', 'fi')
        
        # Obtener todos los permisos disponibles
        available_permissions = FIPermission.objects.filter(
            module=module,
            is_active=True
        ).order_by('category', 'name')
        
        # Agrupar por categoría
        grouped = {}
        for perm in available_permissions:
            category = perm.category
            if category not in grouped:
                grouped[category] = []
            
            grouped[category].append({
                'id': perm.id,
                'codename': perm.codename,
                'name': perm.name,
                'description': perm.description
            })
        
        # Si se proporciona group_id, incluir permisos ya asignados
        already_assigned = []
        if group_id:
            try:
                group = FICustomGroup.objects.get(id=group_id)
                already_assigned = list(group.permissions.values_list('id', flat=True))
            except FICustomGroup.DoesNotExist:
                pass
        
        return Response({
            'total_available': available_permissions.count(),
            'permissions_by_category': grouped,
            'already_assigned': already_assigned
        })


# ===================================================
# VIEWSETS PARA GRUPOS PERSONALIZADOS
# ===================================================
class FICustomGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar grupos personalizados de FI
    
    Endpoints:
    - GET /fi/groups/ - Listar grupos
    - POST /fi/groups/ - Crear grupo
    - GET /fi/groups/{id}/ - Detalle de grupo
    - PUT /fi/groups/{id}/ - Actualizar grupo
    - DELETE /fi/groups/{id}/ - Eliminar grupo
    - POST /fi/groups/{id}/assing-permissions/ - Asignar permisos
    - GET /fi/groups/{id}/members/ - Ver miembros del grupo
    """
    queryset = FICustomGroup.objects.all()
    permission_classes = [IsAuthenticated, RegistryPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['financial_institution', 'is_active']
    search_fields = ['name', 'description']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        if self.kwargs.get('pk'):
            validate_entity_exists(FICustomGroup, 'Grupo personalizado', self.kwargs.get('pk'))
        super().initial(request, *args, **kwargs)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FICustomGroupCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FICustomGroupUpdateSerializer
        return FICustomGroupSerializer
    
    def get_queryset(self):
        """Filtrar según permisos del usuario"""
        user = self.request.user
        
        if user.is_superuser:
            return FICustomGroup.objects.all()
        
        if user.is_staff:
            # Staff ve grupos de todas las FI
            return FICustomGroup.objects.all()
        
        # Usuarios normales ven grupos de las FI donde son miembros
        user_fi_ids = FIUserGroupMembership.objects.filter(
            user=user,
            is_active=True
        ).values_list('group__financial_institution', flat=True)
        
        return FICustomGroup.objects.filter(
            financial_institution__in=user_fi_ids
        )
    
    @action(detail=True, methods=['post'], url_path='assign-permissions')
    def assign_permissions(self, request, **kwargs):
        """Asignar permisos a un grupo"""
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        
        if not isinstance(permission_ids, list):
            return Response({
                'error': 'permission_ids debe ser una lista'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        permissions = FIPermission.objects.filter(id__in=permission_ids)
        
        if len(permissions) != len(permission_ids):
            return Response({
                'error': 'Algunos permisos no fueron encontrados'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        group.permissions.set(permissions)
        
        return Response({
            'success': True,
            'message': f'{len(permissions)} permisos asignados correctamente',
            'permissions': FIPermissionListSerializer(permissions, many=True).data
        })
    
    @action(detail=True, methods=['get'])
    def members(self, request, **kwargs):
        """Listar miembros del grupo"""
        group = self.get_object()
        memberships = FIUserGroupMembership.objects.filter(
            group=group,
            is_active=True
        ).select_related('user', 'assigned_by')
        
        serializer = FIUserGroupMembershipSerializer(memberships, many=True)
        
        return Response({
            'group_name': group.name,
            'total_members': memberships.count(),
            'members': serializer.data
        })


# ===================================================
# VIEWSETS PARA MEMBRESÍAS
# ===================================================
class FIUserGroupMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver membresías de usuarios en grupos
    
    Endpoints:
    - GET /fi/memberships/ - Listar membresías
    - GET /fi/memberships/{id}/ - Detalle de membresía
    """
    queryset = FIUserGroupMembership.objects.all()
    serializer_class = FIUserGroupMembershipSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user', 'group', 'is_active']
    search_fields = ['user__email', 'group__name']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        fi_id = self.kwargs.get('fi_id')
        
        if user.is_superuser or user.is_staff:
            return FIUserGroupMembership.objects.select_related('group__financial_institution').filter(
                group__financial_institution_id=fi_id,
                is_active=True
            )
        
        # Usuarios normales solo ven sus propias membresías
        return FIUserGroupMembership.objects.filter(user=user)


# ===================================================
# VISTAS PARA ASIGNAR/REMOVER USUARIOS
# ===================================================
class FIGroupMembershipActionsViewSet(viewsets.GenericViewSet):
    """
    Acciones de membresía FI en formato class-based para compatibilidad con RegistryPermission
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        fi_id = kwargs.get('fi_id')
        if fi_id:
            validate_entity_exists(FinancialInstitution, 'Institución financiera', fi_id)
        super().initial(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='assign-user-to-group')
    def assign_user_to_group(self, request, fi_id=None):  
        serializer = AssignUserToGroupSerializer(
            data=request.data,
            context={
                'request': request,
                'fi_id': fi_id
            }
        )

        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        membership = serializer.save()
        return Response({
            'success': True,
            'message': 'Usuario asignado exitosamente al grupo',
            'membership': FIUserGroupMembershipSerializer(membership).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='remove-user-from-group')
    def remove_user_from_group(self, request, fi_id=None):
        serializer = RemoveUserFromGroupSerializer(
            data=request.data,
            context={
                'request': request,
                'fi_id': fi_id
            }
        )

        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        membership = serializer.validated_data['membership']

        if not request.user.is_staff and membership.user != request.user:
            return Response({
                'success': False,
                'error': 'No tienes permisos para remover esta membresía'
            }, status=status.HTTP_403_FORBIDDEN)

        membership.is_active = False
        membership.save(update_fields=['is_active'])

        return Response({
            'success': True,
            'message': 'Usuario removido del grupo exitosamente'
        })

    @action(detail=False, methods=['get'], url_path='my-permissions')
    def my_fi_permissions(self, request, fi_id=None):
        user = request.user
            
        memberships = FIUserGroupMembership.objects.filter(
            user=user,
            is_active=True,
            group__financial_institution_id=fi_id
        ).select_related('group__financial_institution').prefetch_related('group__permissions')

        permissions_by_fi = {}

        for membership in memberships:
            fi_name = membership.group.financial_institution.short_name

            if fi_name not in permissions_by_fi:
                permissions_by_fi[fi_name] = {
                    'fi_id': membership.group.financial_institution.id,
                    'groups': [],
                    'all_permissions': set()
                }

            group_perms = list(membership.group.permissions.values_list('codename', flat=True))
            permissions_by_fi[fi_name]['groups'].append({
                'group_name': membership.group.name,
                'permissions': group_perms
            })
            permissions_by_fi[fi_name]['all_permissions'].update(group_perms)

        for fi_data in permissions_by_fi.values():
            fi_data['all_permissions'] = list(fi_data['all_permissions'])

        return Response({
            'user': request.user.email,
            'fi_id': fi_id,
            'permissions_by_fi': permissions_by_fi
        })

