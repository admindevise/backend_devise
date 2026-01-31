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
        print(f"Validating PermissionAwarePurchaseOrderSerializer with attrs: {attrs}")
        request = self.context.get('request')
        requesting_user = request.user if request else None
        if not requesting_user:
            raise serializers.ValidationError("Usuario no identificado")

        # supplier_user = target_user
        target_user = self._get_target_user(attrs, 'supplier_user') or requesting_user

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
                requesting_user, target_user, 'CREATE_PURCHASE_ORDER', attrs
            )
            self._permission = permission_check.get('permission')
            self._requires_confirmation = permission_check.get('requires_confirmation', False)
        else:
            self._validate_investor(
                target_user, attrs['fund'].id, "No puedes crear órdenes para este fondo"
            )

        attrs['supplier_user'] = target_user
        return super().validate(attrs)

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
                    'amount': str(validated_data.get('total_amount'))  # ✅ Decimal -> str
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

        # seller_user = target_user
        target_user = self._get_target_user(attrs, 'seller_user') or requesting_user

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
        return super().validate(attrs)

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
    fund_id = serializers.IntegerField(required=False)
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
    
    def validate_fund_id(self, value):
        if value:
            from apps.fund.models import Fund
            try:
                fund = Fund.objects.get(id=value)
                return fund
            except Fund.DoesNotExist:
                raise serializers.ValidationError("Fondo no encontrado")
        return None
    
    def create(self, validated_data):
        """Crear permiso de trading"""
        
        target_user = validated_data['target_user_id']
        admin_user = validated_data['admin_user_id']
        fund = validated_data.get('fund_id')
        
        permission = TradingPermissionService.grant_trading_permission(
            user=target_user,
            admin_user=admin_user,
            permission_type=validated_data['permission_type'],
            fund_id=fund.id if fund else None,
            duration_hours=validated_data['duration_hours'],
            max_order_amount=validated_data.get('max_order_amount'),
            max_daily_amount=validated_data.get('max_daily_amount'),
            auto_approve_under=validated_data.get('auto_approve_under'),
            require_confirmation=validated_data['require_confirmation'],
            reason=validated_data['reason']
        )
        
        return permission