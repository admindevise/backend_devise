from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes

from apps.trading.serializers_flow.permission_aware_serializers import (
    PermissionGrantSerializer
)

from apps.user.models_permission import (
    UserAdminPermission
)

from django.utils import timezone

@api_view(['POST'])
@permission_classes([IsAdminUser])  # Solo super admins pueden otorgar permisos
def grant_trading_permission(request):
    """
    Otorga permisos de trading a un administrador para operar en nombre de un usuario
    """
    
    serializer = PermissionGrantSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_permissions(request):
    """
    Lista los permisos activos del usuario autenticado
    """
    
    user = request.user
    
    # Permisos como usuario objetivo (otros admins pueden operar por él)
    as_target = UserAdminPermission.objects.filter(
        user=user,
        status='ACTIVE',
        expires_at__gt=timezone.now()
    ).select_related('admin_user', 'fund')
    
    # Permisos como admin (puede operar por otros)
    as_admin = UserAdminPermission.objects.filter(
        admin_user=user,
        status='ACTIVE',
        expires_at__gt=timezone.now()
    ).select_related('user', 'fund') if user.is_staff else []
    
    return Response({
        'permissions_granted_to_me': [
            {
                'id': p.id,
                'admin_user': p.admin_user.email,
                'permission_type': p.permission_type,
                'fund_name': p.fund.name if p.fund else 'Todos los fondos',
                'expires_at': p.expires_at.isoformat(),
                'usage_count': p.usage_count,
                'reason': p.reason
            } for p in as_target
        ],
        'permissions_i_can_use': [
            {
                'id': p.id,
                'target_user': p.user.email,
                'permission_type': p.permission_type,
                'fund_name': p.fund.name if p.fund else 'Todos los fondos',
                'expires_at': p.expires_at.isoformat(),
                'usage_count': p.usage_count,
                'max_uses': p.max_uses,
                'limits': {
                    'max_order_amount': float(p.max_order_amount) if p.max_order_amount else None,
                    'max_daily_amount': float(p.max_daily_amount) if p.max_daily_amount else None,
                }
            } for p in as_admin
        ]
    })