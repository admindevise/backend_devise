from rest_framework.permissions import BasePermission
from typing import Set, Dict, Callable, Optional
from apps.user.models import User


class BaseEntryPermission(BasePermission):
    """
    Sistema base de permisos escalable
    """
    
    # Configuración por defecto
    required_groups: Set[str] = set()
    required_permissions: Set[str] = set()
    allow_superuser: bool = True
    allow_staff: bool = False
    
    # Hooks personalizables
    custom_check: Optional[Callable] = None
    custom_object_check: Optional[Callable] = None
    
    def has_permission(self, request, view):
        """Verificación base de permisos"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user = request.user
        
        # 1. Super usuarios
        if self.allow_superuser and user.is_superuser:
            return True
        
        # 2. Staff usuarios
        if self.allow_staff and user.is_staff:
            return True
        
        # 3. Verificar grupos requeridos
        if self.required_groups:
            user_groups = set(user.groups.values_list('name', flat=True))
            if user_groups.intersection(self.required_groups):
                return True
        
        # 4. Verificar permisos específicos
        if self.required_permissions:
            for perm in self.required_permissions:
                if user.has_perm(perm):
                    return True
        
        # 5. Hook personalizado
        if self.custom_check:
            return self.custom_check(request, view, user)
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Verificación de permisos a nivel de objeto"""
        if not self.has_permission(request, view):
            return False
        
        if self.custom_object_check:
            return self.custom_object_check(request, view, obj, request.user)
        
        return True