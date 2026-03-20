from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.utils.views.global_utils_views import validate_entity_exists
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.user.models import User
from apps.fund.models import Fund
from ..models_permission import UserAdminPermission
from ..serializers.grant_permission_serializer import (
    GrantAdminPermissionSerializer,
    UserAdminPermissionSerializer,
    RevokeAdminPermissionSerializer
)

class GrantAdminPermissionView(generics.CreateAPIView):
    """Vista para que un usuario otorgue permisos a un admin"""
    serializer_class = GrantAdminPermissionSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        return super().initial(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context = {
                'request': request,
                'fund_id': self.kwargs.get('fund_id'),
                'pk': self.kwargs.get('pk'),
            }   
        )
        serializer.is_valid(raise_exception=True)
        
        permission = serializer.save()
        
        return Response({
            'success': True,
            'message': f'Permiso otorgado exitosamente al admin {permission.admin_user.email}',
            'permission': UserAdminPermissionSerializer(permission).data
        }, status=status.HTTP_201_CREATED)


class ListUserPermissionsView(generics.ListAPIView):
    """Vista para listar permisos otorgados por el usuario"""
    serializer_class = UserAdminPermissionSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        return super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        
        # Superadmin ve TODOS los permisos
        if user.is_superuser:
            return UserAdminPermission.objects.all().select_related(
                'admin_user', 'user', 'fund'
            ).order_by('-granted_at')
        
        # Usuarios normales solo ven permisos que ellos otorgaron
        return UserAdminPermission.objects.filter(
            user=user
        ).select_related('admin_user', 'fund').order_by('-granted_at')

class RevokeAdminPermissionView(APIView):
    permission_classes = [IsAuthenticated, RegistryPermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))

    def post(self, request, *args, **kwargs):
        serializer = RevokeAdminPermissionSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

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
            }, status=status.HTTP_200_OK)

        except UserAdminPermission.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Permiso no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)


class RevokeAllPermissionsView(APIView):
    permission_classes = [IsAuthenticated, RegistryPermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))

    def post(self, request, *args, **kwargs):
        active_permissions = UserAdminPermission.objects.filter(
            user=request.user,
            status='ACTIVE',
            expires_at__gt=timezone.now()
        )

        count = active_permissions.count()

        for permission in active_permissions:
            permission.revoke()

        return Response({
            'success': True,
            'message': f'Se revocaron {count} permisos activos'
        }, status=status.HTTP_200_OK)