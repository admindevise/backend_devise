from rest_framework import serializers
from apps.financial_institution.models.permissions import (
    FIPermission,
    FICustomGroup,
    FIUserGroupMembership
)
from apps.financial_institution.models import FinancialInstitution
from apps.user.models import User


# ========================================
# SERIALIZERS DE PERMISOS
# ========================================

class FIPermissionSerializer(serializers.ModelSerializer):
    """Serializer para permisos disponibles"""
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = FIPermission
        fields = [
            'id', 'codename', 'name', 'description', 
            'category', 'created_at'
        ]
        read_only_fields = ['created_at']


class FIPermissionListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar permisos"""
    
    class Meta:
        model = FIPermission
        fields = ['id', 'codename', 'name', 'category']


# ========================================
# SERIALIZERS DE GRUPOS PERSONALIZADOS
# ========================================

class FICustomGroupSerializer(serializers.ModelSerializer):
    """Serializer completo para grupos personalizados"""
    
    financial_institution_name = serializers.CharField(
        source='financial_institution.name', 
        read_only=True
    )
    permissions_detail = FIPermissionListSerializer(
        source='permissions', 
        many=True, 
        read_only=True
    )
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FICustomGroup
        fields = [
            'id', 'financial_institution', 'financial_institution_name',
            'name', 'description', 'permissions', 'permissions_detail',
            'is_active', 'members_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_members_count(self, obj):
        """Contar miembros activos del grupo"""
        return obj.user_memberships.filter(is_active=True).count()
    
    def validate(self, attrs):
        """Validar que el usuario tenga permisos en la FI"""
        request = self.context.get('request')
        
        if request and request.user:
            fi = attrs.get('financial_institution')
            
            # Solo staff de esa FI o superusers pueden crear grupos
            if not request.user.is_superuser:
                if not request.user.is_staff:
                    raise serializers.ValidationError(
                        "No tienes permisos para crear grupos"
                    )
        
        return attrs


class FICustomGroupCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear grupos con permisos"""
    
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = FICustomGroup
        fields = [
            'financial_institution', 'name', 'description', 
            'permission_ids', 'is_active'
        ]
    
    def create(self, validated_data):
        permission_ids = validated_data.pop('permission_ids', [])
        
        # Crear el grupo
        group = FICustomGroup.objects.create(**validated_data)
        
        # Asignar permisos si se proporcionaron
        if permission_ids:
            permissions = FIPermission.objects.filter(id__in=permission_ids)
            group.permissions.set(permissions)
        
        return group


class FICustomGroupUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar grupos"""
    
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = FICustomGroup
        fields = ['name', 'description', 'permission_ids', 'is_active']
    
    def update(self, instance, validated_data):
        permission_ids = validated_data.pop('permission_ids', None)
        
        # Actualizar campos básicos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar permisos si se proporcionaron
        if permission_ids is not None:
            permissions = FIPermission.objects.filter(id__in=permission_ids)
            instance.permissions.set(permissions)
        
        return instance


# ========================================
# SERIALIZERS DE MEMBRESÍAS
# ========================================

class UserBasicSerializer(serializers.ModelSerializer):
    """Serializer básico de usuario"""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email


class FIUserGroupMembershipSerializer(serializers.ModelSerializer):
    """Serializer para membresías de usuarios en grupos"""
    
    user_detail = UserBasicSerializer(source='user', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    assigned_by_email = serializers.CharField(
        source='assigned_by.email', 
        read_only=True
    )
    fi_name = serializers.CharField(
        source='group.financial_institution.short_name', 
        read_only=True
    )
    
    class Meta:
        model = FIUserGroupMembership
        fields = [
            'id', 'user', 'user_detail', 'group', 'group_name',
            'fi_name', 'assigned_at', 'assigned_by', 
            'assigned_by_email', 'is_active', 'notes'
        ]
        read_only_fields = ['assigned_at']


class AssignUserToGroupSerializer(serializers.Serializer):
    """Serializer para asignar usuario a grupo"""
    
    user_id = serializers.IntegerField()
    group_id = serializers.IntegerField()
    notes = serializers.CharField(
        max_length=500, 
        required=False, 
        allow_blank=True
    )
    
    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado")
    
    def validate_group_id(self, value):
        try:
            group = FICustomGroup.objects.get(id=value)
            return group
        except FICustomGroup.DoesNotExist:
            raise serializers.ValidationError("Grupo no encontrado")
    
    def validate(self, attrs):
        user = attrs['user_id']
        group = attrs['group_id']
        
        # Verificar si ya existe membresía activa
        existing = FIUserGroupMembership.objects.filter(
            user=user,
            group=group,
            is_active=True
        ).exists()
        
        if existing:
            raise serializers.ValidationError(
                f"El usuario ya pertenece al grupo '{group.name}'"
            )
        
        return attrs
    
    def create(self, validated_data):
        from apps.financial_institution.services.permission_service import FIPermissionService
        
        request = self.context.get('request')
        user = validated_data['user_id']
        group = validated_data['group_id']
        notes = validated_data.get('notes', '')
        
        membership = FIPermissionService.assign_user_to_group(
            user=user,
            group=group,
            assigned_by=request.user,
            notes=notes
        )
        
        return membership


class RemoveUserFromGroupSerializer(serializers.Serializer):
    """Serializer para remover usuario de grupo"""
    
    membership_id = serializers.IntegerField()
    
    def validate_membership_id(self, value):
        try:
            membership = FIUserGroupMembership.objects.get(id=value)
            return membership
        except FIUserGroupMembership.DoesNotExist:
            raise serializers.ValidationError("Membresía no encontrada")