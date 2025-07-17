from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from ..models_permission import UserAdminPermission
from ..serializers.grant_permission_serializer import (
    GrantAdminPermissionSerializer,
    UserAdminPermissionSerializer,
    RevokeAdminPermissionSerializer
)

@permission_classes([IsAuthenticated])
class GrantAdminPermissionView(generics.CreateAPIView):
    """Vista para que un usuario otorgue permisos a un admin"""
    
    serializer_class = GrantAdminPermissionSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        permission = serializer.save()
        
        return Response({
            'success': True,
            'message': f'Permiso otorgado exitosamente al admin {permission.admin_user.email}',
            'permission': UserAdminPermissionSerializer(permission).data
        }, status=status.HTTP_201_CREATED)

@permission_classes([IsAuthenticated])
class ListUserPermissionsView(generics.ListAPIView):
    """Vista para listar permisos otorgados por el usuario"""
    
    serializer_class = UserAdminPermissionSerializer
    
    def get_queryset(self):
        return UserAdminPermission.objects.filter(
            user=self.request.user
        ).select_related('admin_user').order_by('-granted_at')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_admin_permission(request):
    """Vista para revocar un permiso específico"""
    
    serializer = RevokeAdminPermissionSerializer(
        data=request.data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        permission_id = serializer.validated_data['permission_id']
        
        try:
            permission = UserAdminPermission.objects.get(
                id=permission_id,
                user=request.user,
                status='ACTIVE'
            )
            
            permission.revoke()
            
            return Response({
                'success': True,
                'message': f'Permiso revocado exitosamente para {permission.admin_user.email}'
            })
            
        except UserAdminPermission.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Permiso no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_all_permissions(request):
    """Vista para revocar todos los permisos activos"""
    
    active_permissions = UserAdminPermission.objects.filter(
        user=request.user,
        status='ACTIVE',
        expires_at__gt=timezone.now()
    )
    
    count = active_permissions.count()
    
    # Revocar todos
    for permission in active_permissions:
        permission.revoke()
    
    return Response({
        'success': True,
        'message': f'Se revocaron {count} permisos activos'
    })