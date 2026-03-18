from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.fund.models.core import Fund
from apps.trading.serializers_flow.permission_aware_serializers import PermissionGrantSerializer
from apps.trading.views.utils_views import validate_entity_exists
from apps.user.models_permission import UserAdminPermission


class TradingPermissionViewSet(viewsets.GenericViewSet):
    serializer_class = PermissionGrantSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='grant')
    def grant_trading_permission(self, request, **kwargs):
        """
        Otorga permisos de trading a un administrador para operar en nombre de un usuario.
        """
        serializer = self.get_serializer(
            data=request.data,
            context={
                'request': request,
                'fund_id': self.kwargs.get('fund_id')
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='list')
    def list_user_permissions(self, request, **kwargs):
        """
        Lista los permisos activos del usuario autenticado.
        """
        user = request.user
        now = timezone.now()

        as_target = UserAdminPermission.objects.filter(
            user=user,
            status='ACTIVE',
            expires_at__gt=now
        ).select_related('admin_user', 'fund')

        as_admin = UserAdminPermission.objects.filter(
            admin_user=user,
            status='ACTIVE',
            expires_at__gt=now
        ).select_related('user', 'fund') if user.is_staff else []

        return Response({
            'permissions_granted_to_me': [
                {
                    'id': p.id,
                    'admin_user': p.admin_user.email,
                    'permission_type': p.permission_type,
                    'fund_name': p.fund.name if p.fund else 'Todos los fondos',
                    'expires_at': p.expires_at.strftime("%Y-%m-%d %H:%M:%S") if p.expires_at else None,
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
                    'expires_at': p.expires_at.strftime("%Y-%m-%d %H:%M:%S") if p.expires_at else None,
                    'usage_count': p.usage_count,
                    'max_uses': p.max_uses,
                    'limits': {
                        'max_order_amount': float(p.max_order_amount) if p.max_order_amount else None,
                        'max_daily_amount': float(p.max_daily_amount) if p.max_daily_amount else None,
                    }
                } for p in as_admin
            ]
        })