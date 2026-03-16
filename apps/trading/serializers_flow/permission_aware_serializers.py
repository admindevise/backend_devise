from decimal import Decimal
from rest_framework import serializers
from django.db import transaction

from apps.trading.serializers.core_serializer import (
    PurchaseOrderSerializer,
    SalesOrderSerializer
)
from apps.user.services.permission_service import TradingPermissionService
from apps.user.models import User


class PermissionAwareBaseSerializer(serializers.Serializer):
    """
    Serializer base para validaciones de permisos en trading
    """
    def get_requesting_user(self):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return request.user
        return None

    def _get_target_user(self, attrs, field_name):
        # ✅ fallback a initial_data si attrs no lo trae
        target = attrs.get(field_name) or self.initial_data.get(field_name)
        if target is None:
            return None
        if isinstance(target, User):
            return target
        try:
            return User.objects.get(id=target)
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuario objetivo no encontrado")
    
    def _validate_staff_user(self, requesting_user, target_user):
        # Metodo para no permitir que un staff cree una orden para otro staff o si mismo
        print(f"el user es {requesting_user} y el target es {target_user}")
        if requesting_user.is_staff and target_user.id == requesting_user.id:
            raise serializers.ValidationError(
                "Los administradores no pueden crear órdenes para sí mismos"
            )

    def _validate_admin_permission(self, requesting_user, target_user, action_type, attrs):
        permission_check = TradingPermissionService.check_permission(
            admin_user=requesting_user,
            target_user=target_user,
            action_type=action_type,
            fund_id=attrs['fund'].id,
            amount=attrs.get('total_amount')
        )
        if not permission_check['allowed']:
            raise serializers.ValidationError({
                'permission_error': permission_check['reason'],
                'requires_permission_grant': permission_check.get('requires_permission', False)
            })
        return permission_check

    def _validate_investor(self, target_user, fund_id, error_message):
        from apps.kaleido.utils import is_investor_valid
        investment, error = is_investor_valid(target_user, fund_id)
        if error:
            raise serializers.ValidationError(f"{error_message}: {error}")


class PermissionAwarePurchaseOrderSerializer(PermissionAwareBaseSerializer, PurchaseOrderSerializer):
    """
    Serializer que valida permisos de admin antes de crear órdenes de compra
    """
    class Meta(PurchaseOrderSerializer.Meta):
        model = PurchaseOrderSerializer.Meta.model
        fields = PurchaseOrderSerializer.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permission = None
        self._requires_confirmation = False

    def validate(self, attrs):
        request = self.context.get('request')
        requesting_user = request.user if request else None
        if not requesting_user:
            raise serializers.ValidationError("Usuario no identificado")

        attrs = super().validate(attrs)

        target_user = self._get_target_user(attrs, 'supplier_user') or requesting_user

        self._validate_staff_user(requesting_user, target_user)

        # Validar que un admin no cree orden para otro admin o para sí mismo
        if target_user and target_user.id != requesting_user.id:
            if not requesting_user.is_staff:
                raise serializers.ValidationError(
                    "Solo administradores pueden crear órdenes para otros usuarios"
                )

            permission_check = self._validate_admin_permission(
                requesting_user, target_user, 'CREATE_PURCHASE_ORDER', attrs
            )
            self._permission = permission_check.get('permission')
            self._requires_confirmation = permission_check.get('requires_confirmation', False)
        else:
            self._validate_investor(
                target_user, attrs['fund'].id, "No puedes crear órdenes para este fondo"
            )

        attrs['supplier_user'] = target_user
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        if self._permission:
            if self._requires_confirmation:
                pending_action = TradingPermissionService.request_approval(
                    permission=self._permission,
                    action_type='CREATE_PURCHASE_ORDER',
                    action_data=validated_data,
                    amount=validated_data.get('total_amount'),
                    description=(
                        f"Crear orden de compra por ${validated_data.get('total_amount')} "
                        f"para {validated_data['supplier_user'].email}"
                    )
                )
                return {
                    'requires_user_approval': True,
                    'pending_action_id': pending_action.id,
                    'message': 'La orden requiere aprobación del usuario objetivo',
                    'approval_expires_at': pending_action.expires_at.isoformat(),
                    'amount': str(validated_data.get('total_amount'))
                }

            # ✅ crear orden normal y registrar uso
            order = super().create(validated_data)
            TradingPermissionService.log_permission_usage(
                permission=self._permission,
                action_type='CREATE_PURCHASE_ORDER',
                action_data=validated_data,
                success=True
            )
            return order

        return super().create(validated_data)
    
    def to_representation(self, instance):
        if isinstance(instance, dict):
            return instance
        return super().to_representation(instance)


class PermissionAwareSalesOrderSerializer(PermissionAwareBaseSerializer, SalesOrderSerializer):
    """
    Serializer que valida permisos de admin antes de crear órdenes de venta
    """
    class Meta(SalesOrderSerializer.Meta):
        model = SalesOrderSerializer.Meta.model
        fields = SalesOrderSerializer.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permission = None
        self._requires_confirmation = False

    def validate(self, attrs):
        request = self.context.get('request')
        requesting_user = request.user if request else None
        if not requesting_user:
            raise serializers.ValidationError("Usuario no identificado")
        
        # Resolver fund desde contexto o body
        attrs = super().validate(attrs)

        # seller_user = target_user
        target_user = self._get_target_user(attrs, 'seller_user') or requesting_user
        
        print(f"IN SERILAIZERS TARGET USER:", {target_user})
        
        # Validar que un admin no cree orden para otro admin o para sí mismo
        self._validate_staff_user(requesting_user, target_user) or requesting_user

        if target_user and target_user.id != requesting_user.id:
            if not requesting_user.is_staff:
                raise serializers.ValidationError(
                    "Solo administradores pueden crear órdenes para otros usuarios"
                )
            try:
                target_user = User.objects.get(id=target_user.id)
            except User.DoesNotExist:
                raise serializers.ValidationError("Usuario objetivo no encontrado")

            permission_check = self._validate_admin_permission(
                requesting_user, target_user, 'CREATE_SALES_ORDER', attrs
            )
            self._permission = permission_check.get('permission')
            self._requires_confirmation = permission_check.get('requires_confirmation', False)
        else:
            self._validate_investor(
                target_user, attrs['fund'].id, "No puedes crear órdenes para este fondo"
            )

        attrs['seller_user'] = target_user
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        if self._permission:
            if self._requires_confirmation:
                pending_action = TradingPermissionService.request_approval(
                    permission=self._permission,
                    action_type='CREATE_SALES_ORDER',
                    action_data=validated_data,
                    amount=validated_data.get('total_amount'),
                    description=(
                        f"Crear orden de venta por ${validated_data.get('total_amount')} "
                        f"para {validated_data['seller_user'].email}"
                    )
                )
                return {
                    'requires_user_approval': True,
                    'pending_action_id': pending_action.id,
                    'message': 'La orden requiere aprobación del usuario objetivo',
                    'approval_expires_at': pending_action.expires_at.isoformat(),
                    'amount': str(validated_data.get('total_amount'))  # ✅ Decimal -> str
                }

            order = super().create(validated_data)
            TradingPermissionService.log_permission_usage(
                permission=self._permission,
                action_type='CREATE_SALES_ORDER',
                action_data=validated_data,
                success=True
            )
            return order

        return super().create(validated_data)


class PermissionGrantSerializer(serializers.Serializer):
    """
    Serializer para otorgar permisos de trading a administradores
    """
    
    target_user_id = serializers.IntegerField(required=True)
    admin_user_id = serializers.IntegerField(required=True)
    permission_type = serializers.ChoiceField(
        choices=[
            ('CREATE_PURCHASE_ORDER', 'Crear órdenes de compra'),
            ('CREATE_SALES_ORDER', 'Crear órdenes de venta'),
            ('TRADING_FULL_ACCESS', 'Acceso completo a trading'),
        ],
        required=True
    )
    duration_hours = serializers.IntegerField(default=24, min_value=1, max_value=168)  # Máximo 1 semana
    max_order_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, 
        required=False,
        help_text="Monto máximo por orden"
    )
    max_daily_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2,
        required=False,
        help_text="Monto máximo diario"
    )
    auto_approve_under = serializers.DecimalField(
        max_digits=15, decimal_places=2,
        required=False,
        help_text="Auto-aprobar órdenes menores a este monto"
    )
    require_confirmation = serializers.BooleanField(default=True)
    reason = serializers.CharField(max_length=500, required=True)
    
    def validate_target_user_id(self, value):
        try:
            user = User.objects.get(id=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuario objetivo no encontrado")
    
    def validate_admin_user_id(self, value):
        try:
            admin = User.objects.get(id=value, is_staff=True)
            return admin
        except User.DoesNotExist:
            raise serializers.ValidationError("Administrador no encontrado o no tiene permisos de staff")
    
    def validate(self, attrs):
        target_user = attrs['target_user_id']
        admin_user = attrs['admin_user_id']
        fund_id = self.context.get('fund_id')
        
        if target_user.id == admin_user.id:
            raise serializers.ValidationError("El administrador no puede otorgarse permisos a sí mismo")
        
        # Validar que el registro no este duplicado
        existing_permissions = TradingPermissionService.get_active_permissions(
            user=target_user,
            admin_user=admin_user,
            permission_type=attrs['permission_type'],
            fund=fund_id
        )
        if existing_permissions.exists():
            raise serializers.ValidationError({
                'permission_duplicate': "Ya existe un permiso activo similar para este administrador y fondo."
            })
        return attrs
    
    def create(self, validated_data):
        """Crear permiso de trading"""
        print("CREATING PERMISSION WITH DATA:", validated_data)
        target_user = validated_data['target_user_id']
        admin_user = validated_data['admin_user_id']
        fund_id = self.context.get('fund_id')
        
        renewed_permission = TradingPermissionService.renew_if_exists(
            user=target_user,
            admin_user=admin_user,
            permission_type=validated_data['permission_type'],
            fund_id=fund_id,
            duration_hours=validated_data['duration_hours'],
            max_order_amount=validated_data.get('max_order_amount'),
            max_daily_amount=validated_data.get('max_daily_amount'),
            auto_approve_under=validated_data.get('auto_approve_under'),
            require_confirmation=validated_data['require_confirmation'],
            reason=validated_data['reason']
        )
        if renewed_permission:
            return renewed_permission

        # Si no existe histórico, crear nuevo
        return TradingPermissionService.grant_trading_permission(
            user=target_user,
            admin_user=admin_user,
            permission_type=validated_data['permission_type'],
            fund_id=fund_id,
            duration_hours=validated_data['duration_hours'],
            max_order_amount=validated_data.get('max_order_amount'),
            max_daily_amount=validated_data.get('max_daily_amount'),
            auto_approve_under=validated_data.get('auto_approve_under'),
            require_confirmation=validated_data['require_confirmation'],
            reason=validated_data['reason']
        )
    
    def to_representation(self, instance):
        """Serializa el permiso creado (UserAdminPermission)"""
        from datetime import date, datetime
        
        # Si instance es un UserAdminPermission modelo
        if hasattr(instance, 'id'):
            return {
                'id': instance.id,
                'user': instance.user.id if instance.user else None,
                'user_email': instance.user.email if instance.user else None,
                'admin_user': instance.admin_user.id if instance.admin_user else None,
                'admin_email': instance.admin_user.email if instance.admin_user else None,
                'permission_type': instance.permission_type,
                'fund': instance.fund.id if instance.fund else None,
                'fund_name': instance.fund.name if instance.fund else None,
                'status': instance.status,
                'max_order_amount': str(instance.max_order_amount) if instance.max_order_amount else None,
                'max_daily_amount': str(instance.max_daily_amount) if instance.max_daily_amount else None,
                'auto_approve_under_amount': str(instance.auto_approve_under_amount) if instance.auto_approve_under_amount else None,
                'require_confirmation': instance.require_confirmation,
                'granted_at': instance.granted_at.strftime("%Y-%m-%d %H:%M:%S") if instance.granted_at else None,
                'expires_at': instance.expires_at.strftime("%Y-%m-%d %H:%M:%S") if instance.expires_at else None,
                'reason': instance.reason,
                'message': 'Permiso otorgado exitosamente'
            }
        
        # Si es un dict, retornar tal cual
        return instance
    