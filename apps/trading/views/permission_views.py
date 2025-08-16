from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes

from apps.trading.serializers_flow.permission_aware_serializers import (
    PermissionAwarePurchaseOrderSerializer,
    PermissionAwareSalesOrderSerializer,
    PermissionGrantSerializer
)

from apps.user.models_permission import (
    UserAdminPermission
)

from django.utils import timezone

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_purchase_order_with_permissions(request):
    """
    Crea una orden de compra validando permisos si es necesario
    
    Para usuarios normales: Crea orden para sí mismo
    Para admins: Puede crear para otros usuarios si tiene permisos
    """
    
    serializer = PermissionAwarePurchaseOrderSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        
        # Verificar si requiere aprobación
        if isinstance(result, dict) and result.get('requires_user_approval'):
            return Response({
                'success': True,
                'requires_approval': True,
                'pending_action': result,
                'message': 'Orden creada pero requiere aprobación del usuario'
            }, status=status.HTTP_202_ACCEPTED)
        
        # Orden creada exitosamente
        from apps.trading.serializers.core_serializer import PurchaseOrderSerializer
        order_data = PurchaseOrderSerializer(result).data
        
        return Response({
            'success': True,
            'purchase_order': order_data,
            'message': 'Orden de compra creada exitosamente'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_sales_order_with_permissions(request):
    """
    Crea una orden de venta validando permisos si es necesario
    """
    
    serializer = PermissionAwareSalesOrderSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        
        # Verificar si requiere aprobación
        if isinstance(result, dict) and result.get('requires_user_approval'):
            return Response({
                'success': True,
                'requires_approval': True,
                'pending_action': result,
                'message': 'Orden creada pero requiere aprobación del usuario'
            }, status=status.HTTP_202_ACCEPTED)
        
        # Orden creada exitosamente
        from apps.trading.serializers.core_serializer import SalesOrderSerializer
        order_data = SalesOrderSerializer(result).data
        
        return Response({
            'success': True,
            'sales_order': order_data,
            'message': 'Orden de venta creada exitosamente'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])  # Solo super admins pueden otorgar permisos
def grant_trading_permission(request):
    """
    Otorga permisos de trading a un administrador para operar en nombre de un usuario
    """
    
    serializer = PermissionGrantSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        permission = serializer.save()
        
        return Response({
            'success': True,
            'permission': {
                'id': permission.id,
                'target_user': permission.user.email,
                'admin_user': permission.admin_user.email,
                'permission_type': permission.permission_type,
                'expires_at': permission.expires_at.isoformat(),
                'fund_name': permission.fund.name if permission.fund else 'Todos los fondos',
                'limits': {
                    'max_order_amount': float(permission.max_order_amount) if permission.max_order_amount else None,
                    'max_daily_amount': float(permission.max_daily_amount) if permission.max_daily_amount else None,
                    'auto_approve_under': float(permission.auto_approve_under_amount) if permission.auto_approve_under_amount else None,
                    'require_confirmation': permission.require_confirmation
                }
            },
            'message': f'Permiso otorgado exitosamente a {permission.admin_user.email}'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


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