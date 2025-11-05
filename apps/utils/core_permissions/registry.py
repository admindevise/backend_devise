from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from .permissions_config import (
    VIEWSET_PERMISSION_MAP,
    PERMISSION_RULES,
)


class PermissionRegistry(BasePermission):
    """
    Sistema de permisos universal multi-tenant
    
    Soporta múltiples módulos:
    - Financial Institution
    - Fund
    - Trading
    - Y cualquier módulo futuro
    """
    
    def has_permission(self, request, view):
        """Verificar permisos base"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Obtener información del ViewSet
        viewset_name = self._get_viewset_name(view)
        action = getattr(view, 'action', 'list')
        
        # Obtener módulo y permiso requerido
        module, permission = self._get_permission_info(viewset_name, action)
        
        if not module or not permission:
            raise PermissionDenied(
                f"No hay configuración de permisos para: {viewset_name}.{action}"
            )
        
        # Verificar según tipo de usuario
        return self._check_permission(request.user, module, permission, request, view)
    
    def _get_viewset_name(self, view) -> str:
        """Obtener nombre completo del ViewSet"""
        module = view.__class__.__module__
        class_name = view.__class__.__name__
        
        if 'apps.' in module:
            parts = module.split('.')
            app_index = parts.index('apps')
            if len(parts) > app_index + 1:
                app_label = parts[app_index + 1]
                return f"{app_label}.{class_name}"
        
        return class_name
    
    def _get_permission_info(self, viewset_name: str, action: str):
        """Obtener módulo y permiso requerido"""
        viewset_config = VIEWSET_PERMISSION_MAP.get(viewset_name)
        
        if not viewset_config:
            return None, None
        
        permission_tuple = viewset_config.get(action)
        
        if not permission_tuple:
            return None, None
        
        module, permission = permission_tuple
        return module, permission
    
    def _check_permission(self, user, module: str, permission: str, request, view):
        """Verificar permiso según módulo y tipo de usuario"""
        
        # Obtener reglas del módulo
        rules = PERMISSION_RULES.get(module)
        
        if not rules:
            raise PermissionDenied(f"No hay reglas configuradas para el módulo: {module}")
        
        # 1. STAFF GLOBAL
        if user.is_staff:
            staff_groups = set(user.groups.values_list('name', flat=True))
            if staff_groups.intersection(set(rules['staff_groups'])):
                return True
        
        # 2. CLIENTES GLOBALES
        user_groups = set(user.groups.values_list('name', flat=True))
        client_groups = set(rules['client_groups'])
        
        if user_groups.intersection(client_groups):
            # Verificar si el permiso está permitido para clientes
            if permission in rules['client_allowed_actions']:
                return True
            else:
                raise PermissionDenied(
                    f"Los clientes no tienen permiso para: {permission}"
                )
        
        # 3. USUARIOS CON ROLES EN CONTEXTO (FI, Fund, etc.)
        context_obj = self._get_context_object(request, view, rules['context_field'])
        
        if context_obj:
            # Verificar permiso usando el servicio correspondiente
            if module == 'fi':
                from apps.financial_institution.services.permission_service import FIPermissionService
                
                has_perm = FIPermissionService.user_has_permission(
                    user,
                    permission,
                    context_obj
                )
                
                if has_perm:
                    return True
                
                # Mensaje de error personalizado
                user_groups_in_context = FIPermissionService.get_user_groups_in_fi(user, context_obj)
                
                if user_groups_in_context:
                    groups_str = ', '.join([g.name for g in user_groups_in_context])
                    raise PermissionDenied(
                        f"Tu rol en {context_obj.short_name} ({groups_str}) no tiene permiso para: {permission}"
                    )
                else:
                    raise PermissionDenied(
                        f"No tienes roles asignados en '{context_obj.short_name}'"
                    )
            
            elif module == 'fund':
                # TODO: Implementar FundPermissionService similar a FIPermissionService
                # Por ahora, staff tiene acceso
                if user.is_staff:
                    return True
                raise PermissionDenied(
                    f"No tienes permisos para realizar esta acción en el fondo"
                )
        
        # Si llegamos aquí, denegar
        raise PermissionDenied(
            "No tienes permisos para realizar esta acción"
        )
    
    def _get_context_object(self, request, view, context_field: str):
        """Obtener objeto de contexto (FI, Fund, etc.)"""
        if not context_field:
            return None
        
        # Mapeo de campos a modelos
        model_map = {
            'financial_institution': 'apps.financial_institution.models.FinancialInstitution',
            'fund': 'apps.fund.models.core.Fund',
        }
        
        model_path = model_map.get(context_field)
        
        if not model_path:
            return None
        
        # Importar modelo dinámicamente
        module_path, model_name = model_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[model_name])
        Model = getattr(module, model_name)
        
        # 1. Desde query params
        obj_id = request.query_params.get(context_field)
        if obj_id:
            try:
                return Model.objects.get(id=obj_id)
            except Model.DoesNotExist:
                pass
        
        # 2. Desde datos POST/PUT
        if request.method in ['POST', 'PUT', 'PATCH']:
            obj_id = request.data.get(context_field)
            if obj_id:
                try:
                    return Model.objects.get(id=obj_id)
                except Model.DoesNotExist:
                    pass
        
        # 3. Desde el objeto
        if hasattr(view, 'get_object'):
            try:
                obj = view.get_object()
                if hasattr(obj, context_field):
                    return getattr(obj, context_field)
            except:
                pass
        
        return None
    
    def has_object_permission(self, request, view, obj):
        """Verificar permisos a nivel de objeto"""
        if not self.has_permission(request, view):
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Los clientes solo ven sus propios recursos
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return True