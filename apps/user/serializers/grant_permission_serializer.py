from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from ..models_permission import UserAdminPermission
from ..models import User

class GrantAdminPermissionSerializer(serializers.Serializer):
    """Serializer para otorgar permisos a admin"""
    
    admin_user_id = serializers.IntegerField(
        help_text="ID del usuario admin al que se otorga el permiso"
    )
    permission_type = serializers.ChoiceField(
        choices=UserAdminPermission.PERMISSION_TYPES,
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
    
    def validate(self, attrs):
        """Validaciones adicionales"""
        user = self.context['request'].user
        admin_user_id = attrs['admin_user_id']
        permission_type = attrs['permission_type']
        
        # No permitir otorgar permisos a sí mismo
        if user.id == admin_user_id:
            raise serializers.ValidationError(
                "No puedes otorgarte permisos a ti mismo"
            )
        
        # Verificar si ya existe un permiso activo
        existing_permission = UserAdminPermission.objects.filter(
            user=user,
            admin_user_id=admin_user_id,
            permission_type=permission_type,
            status='ACTIVE',
            expires_at__gt=timezone.now()
        ).first()
        
        if existing_permission:
            raise serializers.ValidationError(
                f"Ya existe un permiso activo de tipo '{permission_type}' para este admin"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Crea el permiso temporal"""
        user = self.context['request'].user
        request = self.context['request']
        
        admin_user = User.objects.get(id=validated_data['admin_user_id'])
        expires_at = timezone.now() + timedelta(hours=validated_data['duration_hours'])
        
        permission = UserAdminPermission.objects.create(
            user=user,
            admin_user=admin_user,
            permission_type=validated_data['permission_type'],
            reason=validated_data['reason'],
            expires_at=expires_at,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return permission

class UserAdminPermissionSerializer(serializers.ModelSerializer):
    """Serializer para mostrar permisos otorgados"""
    
    admin_email = serializers.CharField(source='admin_user.email', read_only=True)
    admin_name = serializers.CharField(source='admin_user.get_full_name', read_only=True)
    permission_type_display = serializers.CharField(source='get_permission_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    time_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAdminPermission
        fields = [
            'id', 'admin_email', 'admin_name', 'permission_type', 
            'permission_type_display', 'status', 'status_display', 
            'reason', 'granted_at', 'expires_at', 'revoked_at', 
            'last_used_at', 'is_valid', 'time_remaining'
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

class RevokeAdminPermissionSerializer(serializers.Serializer):
    """Serializer para revocar permisos"""
    
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