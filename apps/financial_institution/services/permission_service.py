"""
Servicio para verificación de permisos multi-tenant
Cada FI gestiona sus propios grupos y permisos
"""
from typing import Optional, Set
from django.contrib.auth import get_user_model

User = get_user_model()


class FIPermissionService:
    """Servicio centralizado para verificar permisos en contexto de FI"""
    
    @staticmethod
    def _get_staff_groups() -> Set[str]:
        """Obtener grupos de staff desde configuración dinámica"""
        from apps.utils.core_permissions.permissions_config import PERMISSION_RULES
        fi_rules = PERMISSION_RULES.get('fi', {})
        return set(fi_rules.get('staff_groups', []))
    
    @staticmethod
    def user_has_permission(
        user,
        permission_codename: str,
        financial_institution = None
    ) -> bool:
        """
        Verificar si un usuario tiene un permiso específico
        
        Args:
            user: Usuario a verificar
            permission_codename: Código del permiso (ej: 'view_applications')
            financial_institution: FI en contexto (opcional)
        
        Returns:
            bool: True si tiene el permiso
        """
        from apps.financial_institution.models.permissions import FIUserGroupMembership
        
        if not user or not user.is_authenticated:
            return False
        
        # 1. Super admins de Devise siempre tienen acceso
        if user.is_superuser:
            return True
        
        # 2. Staff de Devise según configuración dinámica
        if user.is_staff:
            user_groups = set(user.groups.values_list('name', flat=True))
            allowed_staff_groups = FIPermissionService._get_staff_groups()
            
            if user_groups.intersection(allowed_staff_groups):
                return True
        
        # 3. Si no hay FI en contexto, denegar
        if not financial_institution:
            return False
        
        # 4. Obtener grupos del usuario en esta FI
        user_memberships = FIUserGroupMembership.objects.filter(
            user=user,
            group__financial_institution=financial_institution,
            is_active=True
        ).select_related('group').prefetch_related('group__permissions')
        
        if not user_memberships.exists():
            return False
        
        # 5. Verificar si alguno de sus grupos tiene el permiso
        for membership in user_memberships:
            if membership.group.permissions.filter(codename=permission_codename).exists():
                return True
        
        return False
    
    @staticmethod
    def get_user_permissions_in_fi(
        user,
        financial_institution
    ) -> Set[str]:
        """
        Obtener todos los permisos de un usuario en una FI específica
        
        Args:
            user: Usuario a consultar
            financial_institution: Institución financiera
        
        Returns:
            Set[str]: Conjunto de códigos de permisos
        """
        from apps.financial_institution.models.permissions import (
            FIPermission, 
            FIUserGroupMembership
        )
        
        if not user or not user.is_authenticated:
            return set()
        
        # 1️⃣ Super admins tienen todos los permisos
        if user.is_superuser:
            return set(FIPermission.objects.values_list('codename', flat=True))
        
        # 2️⃣ Staff de Devise según configuración dinámica
        if user.is_staff:
            user_groups = set(user.groups.values_list('name', flat=True))
            allowed_staff_groups = FIPermissionService._get_staff_groups()
            
            if user_groups.intersection(allowed_staff_groups):
                return set(FIPermission.objects.values_list('codename', flat=True))
        
        # 3️⃣ Obtener permisos desde grupos de la FI
        user_groups = FIUserGroupMembership.objects.filter(
            user=user,
            group__financial_institution=financial_institution,
            is_active=True
        ).values_list('group', flat=True)
        
        permissions = FIPermission.objects.filter(
            groups__id__in=user_groups
        ).distinct().values_list('codename', flat=True)
        
        return set(permissions)
    
    @staticmethod
    def get_user_groups_in_fi(user, financial_institution) -> list:
        """
        Obtener grupos de un usuario en una FI específica
        
        Args:
            user: Usuario a consultar
            financial_institution: Institución financiera
        
        Returns:
            list: Lista de objetos FICustomGroup
        """
        from apps.financial_institution.models.permissions import FIUserGroupMembership
        
        if not user or not user.is_authenticated:
            return []
        
        memberships = FIUserGroupMembership.objects.filter(
            user=user,
            group__financial_institution=financial_institution,
            is_active=True
        ).select_related('group')
        
        return [m.group for m in memberships]
    
    @staticmethod
    def assign_user_to_group(user, group, assigned_by, notes: str = ""):
        """
        Asignar un usuario a un grupo de FI
        
        Args:
            user: Usuario a asignar
            group: Grupo FI (FICustomGroup)
            assigned_by: Usuario que realiza la asignación
            notes: Notas adicionales
        
        Returns:
            FIUserGroupMembership: Objeto de membresía creado/actualizado
        """
        from apps.financial_institution.models.permissions import FIUserGroupMembership
        
        membership, created = FIUserGroupMembership.objects.get_or_create(
            user=user,
            group=group,
            defaults={
                'assigned_by': assigned_by,
                'notes': notes,
                'is_active': True
            }
        )
        
        if not created and not membership.is_active:
            membership.is_active = True
            membership.assigned_by = assigned_by
            membership.notes = notes
            membership.save()
        
        return membership
    
    @staticmethod
    def remove_user_from_group(user, group) -> bool:
        """
        Remover usuario de un grupo de FI
        
        Args:
            user: Usuario a remover
            group: Grupo FI
        
        Returns:
            bool: True si se removió exitosamente
        """
        from apps.financial_institution.models.permissions import FIUserGroupMembership
        
        try:
            membership = FIUserGroupMembership.objects.get(user=user, group=group)
            membership.is_active = False
            membership.save()
            return True
        except FIUserGroupMembership.DoesNotExist:
            return False
    
    @staticmethod
    def user_is_staff_with_permissions(user) -> bool:
        """
        Verificar si el usuario es staff con permisos según configuración
        
        Args:
            user: Usuario a verificar
        
        Returns:
            bool: True si es staff con permisos
        """
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        if not user.is_staff:
            return False
        
        user_groups = set(user.groups.values_list('name', flat=True))
        allowed_staff_groups = FIPermissionService._get_staff_groups()
        
        return bool(user_groups.intersection(allowed_staff_groups))
    
    @staticmethod
    def get_allowed_staff_groups() -> Set[str]:
        """
        Obtener lista de grupos de staff permitidos
        
        Returns:
            Set[str]: Conjunto de nombres de grupos
        """
        return FIPermissionService._get_staff_groups()