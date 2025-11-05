from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.financial_institution.models.permissions import (
    FIPermission,
    FICustomGroup,
    FIUserGroupMembership
)
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
from apps.financial_institution.services.permission_service import FIPermissionService


# ========================================
# VIEWSETS PARA PERMISOS
# ========================================

class FIPermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para permisos disponibles
    
    Endpoints:
    - GET /api/permissions/ - Listar todos los permisos
    - GET /api/permissions/{id}/ - Detalle de un permiso
    - GET /api/permissions/by-category/ - Permisos agrupados por categoría
    - GET /api/permissions/by-module/ - Permisos agrupados por módulo
    - GET /api/permissions/available_for_group/ - Permisos disponibles para asignar a un grupo
    """
    queryset = FIPermission.objects.filter(is_active=True)
    serializer_class = FIPermissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'module', 'is_active']
    search_fields = ['name', 'description', 'codename']
    ordering_fields = ['module', 'category', 'name']
    ordering = ['module', 'category', 'name']
    
    @action(detail=False, methods=['get'], url_path='by-category')
    def by_category(self, request):
        """
        Agrupar permisos por categoría
        
        GET /api/permissions/by_category/
        GET /api/permissions/by_category/?module=fi
        
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
    def by_module(self, request):
        """
        Agrupar permisos por módulo
        
        GET /api/permissions/by_module/
        
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
    def available_for_group(self, request):
        """
        Obtener permisos disponibles para asignar a un grupo
        Útil para formularios de creación/edición de grupos
        
        GET /api/permissions/available-for-group/?group_id=5
        
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


# ========================================
# VIEWSETS PARA GRUPOS PERSONALIZADOS
# ========================================

class FICustomGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar grupos personalizados de FI
    
    Endpoints:
    - GET /api/fi/groups/ - Listar grupos
    - POST /api/fi/groups/ - Crear grupo
    - GET /api/fi/groups/{id}/ - Detalle de grupo
    - PUT /api/fi/groups/{id}/ - Actualizar grupo
    - DELETE /api/fi/groups/{id}/ - Eliminar grupo
    - POST /api/fi/groups/{id}/assing-permissions/ - Asignar permisos
    - GET /api/fi/groups/{id}/members/ - Ver miembros del grupo
    """
    queryset = FICustomGroup.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['financial_institution', 'is_active']
    search_fields = ['name', 'description']
    
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
    
    @action(detail=True, methods=['post'], url_path='assing-permissions')
    def assign_permissions(self, request, pk=None):
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
    def members(self, request, pk=None):
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


# ========================================
# VIEWSETS PARA MEMBRESÍAS
# ========================================

class FIUserGroupMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver membresías de usuarios en grupos
    
    Endpoints:
    - GET /api/fi/memberships/ - Listar membresías
    - GET /api/fi/memberships/{id}/ - Detalle de membresía
    """
    queryset = FIUserGroupMembership.objects.all()
    serializer_class = FIUserGroupMembershipSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user', 'group', 'is_active']
    search_fields = ['user__email', 'group__name']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser or user.is_staff:
            return FIUserGroupMembership.objects.all()
        
        # Usuarios normales solo ven sus propias membresías
        return FIUserGroupMembership.objects.filter(user=user)


# ========================================
# VISTAS PARA ASIGNAR/REMOVER USUARIOS
# ========================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_user_to_group(request):
    """
    Asignar un usuario a un grupo de FI
    
    POST /api/fi/assign-user-to-group/
    {
        "user_id": 123,
        "group_id": 5,
        "notes": "Asignado como manager"
    }
    """
    serializer = AssignUserToGroupSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        membership = serializer.save()
        
        return Response({
            'success': True,
            'message': f'Usuario asignado exitosamente al grupo',
            'membership': FIUserGroupMembershipSerializer(membership).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_user_from_group(request):
    """
    Remover un usuario de un grupo
    
    POST /api/fi/remove-user-from-group/
    {
        "membership_id": 45
    }
    """
    serializer = RemoveUserFromGroupSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        membership = serializer.validated_data['membership_id']
        
        # Verificar permisos
        if not request.user.is_staff and membership.user != request.user:
            return Response({
                'success': False,
                'error': 'No tienes permisos para remover esta membresía'
            }, status=status.HTTP_403_FORBIDDEN)
        
        membership.is_active = False
        membership.save()
        
        return Response({
            'success': True,
            'message': 'Usuario removido del grupo exitosamente'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_fi_permissions(request):
    """
    Ver permisos del usuario autenticado en todas las FI
    
    GET /api/fi/my-permissions/
    """
    user = request.user
    
    memberships = FIUserGroupMembership.objects.filter(
        user=user,
        is_active=True
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
    
    # Convertir sets a listas
    for fi_data in permissions_by_fi.values():
        fi_data['all_permissions'] = list(fi_data['all_permissions'])
    
    return Response({
        'user': request.user.email,
        'permissions_by_fi': permissions_by_fi
    })
    
