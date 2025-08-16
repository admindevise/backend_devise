from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..models_permission import UserAdminPermission
from ..models import User

class GrantAdminPermissionSerializer(serializers.Serializer):
    """Serializer para otorgar permisos a admin - ACTUALIZADO para trading"""
    
    granted_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    expires_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    admin_user_id = serializers.IntegerField(
        help_text="ID del usuario admin al que se otorga el permiso"
    )
    permission_type = serializers.ChoiceField(
        choices=[
            # ✅ NUEVOS: Permisos específicos de trading
            ('CREATE_PURCHASE_ORDER', 'Crear órdenes de compra'),
            ('CREATE_SALES_ORDER', 'Crear órdenes de venta'),
            ('CANCEL_ORDERS', 'Cancelar mis órdenes'),
            ('VIEW_ORDERS', 'Ver mis órdenes'),
            ('SELECT_MATCHES', 'Seleccionar matches para mis órdenes'),
            ('AUTO_SELECT_MATCHES', 'Permitir selección automática'),
            ('CANCEL_SELECTIONS', 'Cancelar selecciones de matches'),
            ('EXECUTE_PAYMENTS', 'Ejecutar pagos de mis órdenes'),
            ('VIEW_PAYMENT_STATUS', 'Ver estado de pagos'),
            ('TRADING_FULL_ACCESS', 'Acceso completo a trading'),
            ('FUND_SPECIFIC_ACCESS', 'Acceso específico a un fondo'),
            
            # Permisos generales (mantener compatibilidad)
            ('EDIT_PROFILE', 'Editar perfil'),
            ('VIEW_FINANCIAL_INFO', 'Ver información financiera'),
            ('MANAGE_INVESTMENTS', 'Gestionar inversiones'),
            ('FULL_ACCESS', 'Acceso completo'),
        ],
        help_text="Tipo de permiso a otorgar"
    )
    reason = serializers.CharField(
        max_length=500,
        help_text="Motivo por el cual otorgas este permiso"
    )
    duration_hours = serializers.IntegerField(
        default=24,
        min_value=1,
        max_value=168,  # Máximo 7 días
        help_text="Duración del permiso en horas (1-168)"
    )
    
    # ✅ NUEVOS: Campos específicos para trading
    fund_id = serializers.IntegerField(
        required=False,
        help_text="ID del fondo específico (opcional, null = todos los fondos)"
    )
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
    max_units_per_order = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Unidades máximas por orden"
    )
    auto_approve_under_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2,
        required=False,
        help_text="Auto-aprobar órdenes menores a este monto"
    )
    require_confirmation = serializers.BooleanField(
        default=True,
        help_text="Requiere confirmación del usuario antes de ejecutar"
    )
    max_uses = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Máximo número de usos del permiso"
    )
    
    def validate_admin_user_id(self, value):
        """Valida que el usuario admin exista y sea staff"""
        try:
            admin_user = User.objects.get(id=value)
            if not admin_user.is_staff:
                raise serializers.ValidationError(
                    "El usuario especificado no es un administrador"
                )
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No se encontró un usuario con ese ID"
            )
    
    def validate_fund_id(self, value):
        """Valida que el fondo exista si se especifica"""
        if value is not None:
            from apps.fund.models import Fund
            try:
                fund = Fund.objects.get(id=value)
                return value
            except Fund.DoesNotExist:
                raise serializers.ValidationError("Fondo no encontrado")
        return value
    
    def validate(self, attrs):
        """Validaciones adicionales y de coherencia"""
        user = self.context['request'].user
        admin_user_id = attrs['admin_user_id']
        permission_type = attrs['permission_type']
        
        # No permitir otorgar permisos a sí mismo
        if user.id == admin_user_id:
            raise serializers.ValidationError(
                "No puedes otorgarte permisos a ti mismo"
            )
        
        # ✅ VALIDACIÓN: Permisos de trading requieren límites
        trading_permissions = [
            'CREATE_PURCHASE_ORDER', 'CREATE_SALES_ORDER', 
            'EXECUTE_PAYMENTS', 'TRADING_FULL_ACCESS'
        ]
        
        if permission_type in trading_permissions:
            max_order_amount = attrs.get('max_order_amount')
            max_daily_amount = attrs.get('max_daily_amount')
            
            # Al menos uno de los límites debe estar definido para permisos de trading
            if not max_order_amount and not max_daily_amount:
                raise serializers.ValidationError(
                    f"Para permisos de trading ({permission_type}) debes especificar al menos "
                    "max_order_amount o max_daily_amount como límite de seguridad"
                )
            
            # Validar coherencia de límites
            if (max_order_amount and max_daily_amount and 
                max_order_amount > max_daily_amount):
                raise serializers.ValidationError(
                    "max_order_amount no puede ser mayor que max_daily_amount"
                )
            
            # Validar auto_approve_under
            auto_approve = attrs.get('auto_approve_under_amount')
            if auto_approve and max_order_amount and auto_approve > max_order_amount:
                raise serializers.ValidationError(
                    "auto_approve_under_amount no puede ser mayor que max_order_amount"
                )
        
        # Verificar si ya existe un permiso activo similar
        existing_permission = UserAdminPermission.objects.filter(
            user=user,
            admin_user_id=admin_user_id,
            permission_type=permission_type,
            status='ACTIVE',
            expires_at__gt=timezone.now()
        ).first()
        
        if existing_permission:
            raise serializers.ValidationError(
                f"Ya existe un permiso activo de tipo '{permission_type}' para este admin. "
                f"Expira el {existing_permission.expires_at.strftime('%Y-%m-%d %H:%M')}"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Crea el permiso temporal con todos los campos nuevos"""
        user = self.context['request'].user
        request = self.context['request']
        
        admin_user = User.objects.get(id=validated_data['admin_user_id'])
        expires_at = timezone.now() + timedelta(hours=validated_data['duration_hours'])
        
        # ✅ CREAR con todos los campos nuevos
        permission = UserAdminPermission.objects.create(
            user=user,
            admin_user=admin_user,
            permission_type=validated_data['permission_type'],
            reason=validated_data['reason'],
            expires_at=expires_at,
            
            # ✅ NUEVOS: Campos de trading
            fund_id=validated_data.get('fund_id'),
            max_order_amount=validated_data.get('max_order_amount'),
            max_daily_amount=validated_data.get('max_daily_amount'),
            max_units_per_order=validated_data.get('max_units_per_order'),
            auto_approve_under_amount=validated_data.get('auto_approve_under_amount'),
            require_confirmation=validated_data.get('require_confirmation', True),
            max_uses=validated_data.get('max_uses'),
            
            # Metadata
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return permission


class UserAdminPermissionSerializer(serializers.ModelSerializer):
    """Serializer para mostrar permisos otorgados - ACTUALIZADO"""
    
    granted_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    expires_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    admin_email = serializers.CharField(source='admin_user.email', read_only=True)
    admin_name = serializers.CharField(source='admin_user.get_full_name', read_only=True)
    permission_type_display = serializers.CharField(source='get_permission_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    time_remaining = serializers.SerializerMethodField()
    
    # ✅ NUEVOS: Campos de trading
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    usage_info = serializers.SerializerMethodField()
    limits_info = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAdminPermission
        fields = [
            'id', 'admin_email', 'admin_name', 'permission_type', 
            'permission_type_display', 'status', 'status_display', 
            'reason', 'granted_at', 'expires_at', 'revoked_at', 
            'last_used_at', 'is_valid', 'time_remaining',
            
            # ✅ NUEVOS: Campos de trading
            'fund_name', 'require_confirmation', 'usage_info', 'limits_info',
            'usage_count', 'max_uses', 'total_amount_used'
        ]
    
    def get_time_remaining(self, obj):
        """Calcula tiempo restante del permiso"""
        if obj.status != 'ACTIVE':
            return None
        
        remaining = obj.expires_at - timezone.now()
        if remaining.total_seconds() <= 0:
            return "Expirado"
        
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def get_usage_info(self, obj):
        """Información de uso del permiso"""
        return {
            'usage_count': obj.usage_count,
            'max_uses': obj.max_uses,
            'total_amount_used': float(obj.total_amount_used) if obj.total_amount_used else 0,
            'last_amount_used': float(obj.last_amount_used) if obj.last_amount_used else None,
            'uses_remaining': (obj.max_uses - obj.usage_count) if obj.max_uses else 'Ilimitado'
        }
    
    def get_limits_info(self, obj):
        """Información de límites del permiso"""
        return {
            'max_order_amount': float(obj.max_order_amount) if obj.max_order_amount else None,
            'max_daily_amount': float(obj.max_daily_amount) if obj.max_daily_amount else None,
            'max_units_per_order': obj.max_units_per_order,
            'auto_approve_under_amount': float(obj.auto_approve_under_amount) if obj.auto_approve_under_amount else None,
            'require_confirmation': obj.require_confirmation
        }


class RevokeAdminPermissionSerializer(serializers.Serializer):
    """Serializer para revocar permisos - SIN CAMBIOS"""
    
    permission_id = serializers.IntegerField()
    
    def validate_permission_id(self, value):
        """Valida que el permiso exista y pertenezca al usuario"""
        user = self.context['request'].user
        
        try:
            permission = UserAdminPermission.objects.get(
                id=value,
                user=user,
                status='ACTIVE'
            )
            return value
        except UserAdminPermission.DoesNotExist:
            raise serializers.ValidationError(
                "No se encontró un permiso activo con ese ID"
            )


# ✅ NUEVO: Serializer específico para trading permissions (simplificado)
class TradingPermissionGrantSerializer(serializers.Serializer):
    """Serializer especializado para otorgar permisos de trading"""
    
    admin_user_id = serializers.IntegerField()
    permission_type = serializers.ChoiceField(choices=[
        ('CREATE_PURCHASE_ORDER', 'Crear órdenes de compra'),
        ('CREATE_SALES_ORDER', 'Crear órdenes de venta'),
        ('TRADING_FULL_ACCESS', 'Acceso completo a trading'),
    ])
    fund_id = serializers.IntegerField(required=False)
    duration_hours = serializers.IntegerField(default=24, min_value=1, max_value=168)
    max_order_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=True)
    max_daily_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    auto_approve_under_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    require_confirmation = serializers.BooleanField(default=True)
    reason = serializers.CharField(max_length=500, required=True)
    
    def validate(self, attrs):
        # Usar las mismas validaciones que GrantAdminPermissionSerializer
        return super().validate(attrs)
    
    def create(self, validated_data):
        # Usar TradingPermissionService.grant_trading_permission()
        from apps.user.services.permission_service import TradingPermissionService
        
        user = self.context['request'].user
        admin_user = User.objects.get(id=validated_data['admin_user_id'])
        
        permission = TradingPermissionService.grant_trading_permission(
            user=user,
            admin_user=admin_user,
            permission_type=validated_data['permission_type'],
            fund_id=validated_data.get('fund_id'),
            duration_hours=validated_data['duration_hours'],
            max_order_amount=validated_data['max_order_amount'],
            max_daily_amount=validated_data.get('max_daily_amount'),
            auto_approve_under=validated_data.get('auto_approve_under_amount'),
            require_confirmation=validated_data['require_confirmation'],
            reason=validated_data['reason']
        )
        
        return permission