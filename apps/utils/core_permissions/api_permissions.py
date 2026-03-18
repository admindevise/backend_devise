from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from apps.utils.core_permissions.permissions_config import (
    VIEWSET_PERMISSION_MAP,
    PERMISSION_RULES
)
from apps.financial_institution.services.permission_service import FIPermissionService

class RegistryPermission(BasePermission):
    """
    Sistema de permisos multi-tenant universal
    """

    def has_permission(self, request, view):
        """Verificar permisos base"""
        if not request.user or not request.user.is_authenticated:
            print("🔒 RegistryPermission: usuario no autenticado")
            return False

        if request.user.is_superuser:
            print("✅ RegistryPermission: superuser, acceso permitido")
            return True

        # Obtener información del ViewSet y acción
        viewset_name = self._get_viewset_name(view)
        action = getattr(view, 'action', None) or request.method.lower()

        print(f"🔍 has_permission -> viewset={viewset_name}, action={action}, method={request.method}")

        # Obtener módulo y permiso requerido desde CONFIG
        module, permission = self._get_permission_info(viewset_name, action)

        if not module or not permission:
            raise PermissionDenied(
                f"No hay configuración de permisos para: {viewset_name}.{action}"
            )

        print(f"🧩 permiso requerido -> module={module}, permission={permission}")

        # Verificar permiso según módulo
        return self._check_permission(request.user, module, permission, request, view)

    def _get_viewset_name(self, view) -> str:
        """Obtener nombre completo del ViewSet (app_label.ViewSetName)"""
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
        """
        Obtener módulo y permiso requerido desde VIEWSET_PERMISSION_MAP
        """
        viewset_config = VIEWSET_PERMISSION_MAP.get(viewset_name)

        if not viewset_config:
            print(f"⚠️ No existe config para viewset: {viewset_name}")
            return None, None

        permission_tuple = viewset_config.get(action)

        if not permission_tuple:
            print(f"⚠️ No existe action '{action}' en config de {viewset_name}")
            return None, None

        module, permission = permission_tuple
        return module, permission

    def _check_permission(self, user, module: str, permission: str, request, view):
        """
        Verificar permiso según módulo y reglas definidas en PERMISSION_RULES
        """
        rules = PERMISSION_RULES.get(module)

        if not rules:
            raise PermissionDenied(
                f"No hay reglas configuradas para el módulo: {module}"
            )

        print(f"📘 rules module={module} -> context_field={rules.get('context_field')}")

        # ========================================
        # 0. CASO ESPECIAL: CREAR FI SIN CONTEXTO
        # ========================================
        if module == 'fi' and permission == 'create_financial_institution':
            global_groups = set(user.groups.values_list('name', flat=True))
            is_global_admin = 'ADMINISTRADOR' in global_groups

            from apps.financial_institution.models.permissions import FIUserGroupMembership
            is_tenant_admin = FIUserGroupMembership.objects.filter(
                user=user,
                is_active=True,
                group__is_active=True,
                group__name='ADMINISTRADOR'
            ).exists()

            print(f"🌐 global_groups={global_groups}, is_global_admin={is_global_admin}, is_tenant_admin={is_tenant_admin}")

            if is_global_admin or is_tenant_admin:
                print("✅ autorizado para crear FI")
                return True

            raise PermissionDenied(
                "Solo usuarios ADMINISTRADOR (global o tenant) pueden crear instituciones financieras"
            )

        # ========================================
        # 1. STAFF GLOBAL
        # ========================================
        if user.is_staff:
            staff_groups = set(user.groups.values_list('name', flat=True))
            allowed_staff_groups = set(rules.get('staff_groups', []))

            print(f"👤 staff_groups={staff_groups}, allowed_staff_groups={allowed_staff_groups}")

            if staff_groups.intersection(allowed_staff_groups):
                print("✅ autorizado por STAFF GLOBAL")
                return True

        # ========================================
        # 2. CLIENTES GLOBALES
        # ========================================
        user_groups = set(user.groups.values_list('name', flat=True))
        client_groups = set(rules.get('client_groups', []))

        if user_groups.intersection(client_groups) or rules.get('allow_unauthenticated_clients'):
            allowed_actions = rules.get('client_allowed_actions', [])
            
            if permission in allowed_actions:
                print("✅ autorizado por CLIENTE GLOBAL (sin validación contextual)")
                return True

            print(f"❌ cliente sin permiso global: {permission} no está en {allowed_actions}")
            raise PermissionDenied(
                f"No tienes permiso global para: {permission}"
            )

        # ========================================
        # 3. USUARIOS CON ROLES EN CONTEXTO (FI, Fund, etc.)
        # ========================================
        context_obj = self._get_context_object(request, view, rules.get('context_field'))
        print(f"🧭 context_obj={context_obj}")

        if module == 'fi' and context_obj:
            has_perm = FIPermissionService.user_has_permission(
                user,
                permission,
                context_obj
            )

            print(f"🔐 FI context permission -> {has_perm}")

            if has_perm:
                return True

            user_groups_in_context = FIPermissionService.get_user_groups_in_fi(user, context_obj)

            if user_groups_in_context:
                groups_str = ', '.join([g.name for g in user_groups_in_context])
                raise PermissionDenied(
                    f"Tu rol en {context_obj.short_name} ({groups_str}) no tiene permiso para: {permission}"
                )
            raise PermissionDenied(
                f"No tienes roles asignados en '{context_obj.short_name}'"
            )

        # trading/fund por contexto de fondo
        if module in ('fund', 'trading') and context_obj:
            fi_obj = getattr(context_obj, 'financial_institution', None)
            if not fi_obj:
                raise PermissionDenied("No se pudo resolver la institución financiera del contexto")

            has_perm = FIPermissionService.user_has_permission(user, permission, fi_obj)
            print(f"🔐 {module.upper()} via FI permission -> {has_perm}")
            if has_perm:
                return True

            raise PermissionDenied(
                f"No tienes permisos para realizar esta acción en '{context_obj.name}'"
            )   

        raise PermissionDenied(
            "No tienes permisos para realizar esta acción"
        )

    def _get_context_object(self, request, view, context_field: str):
        """
        Obtener objeto de contexto (FI, Fund, etc.) según context_field
        """
        if not context_field:
            return None

        model_map = {
            'financial_institution': 'apps.financial_institution.models.core.FinancialInstitution',
            'fund': 'apps.fund.models.core.Fund',
        }

        model_path = model_map.get(context_field)
        if not model_path:
            print(f"⚠️ context_field sin model_map: {context_field}")
            return None

        module_path, model_name = model_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[model_name])
        Model = getattr(module, model_name)

        # 0) Desde kwargs de URL (clave para /financial-institution/<fi_id>/...)
        kwargs = getattr(view, 'kwargs', {}) or {}
        obj_id = kwargs.get(context_field) or kwargs.get(f'{context_field}_id')
        if context_field == 'financial_institution' and not obj_id:
            obj_id = kwargs.get('fi_id')

        if obj_id:
            try:
                obj = Model.objects.get(id=obj_id)
                print(f"✅ context desde kwargs: {context_field}={obj_id}")
                return obj
            except Model.DoesNotExist:
                print(f"❌ context kwargs id no existe: {obj_id}")

        # 1) Desde query params
        obj_id = request.query_params.get(context_field)
        if obj_id:
            try:
                obj = Model.objects.get(id=obj_id)
                print(f"✅ context desde query: {context_field}={obj_id}")
                return obj
            except Model.DoesNotExist:
                print(f"❌ context query id no existe: {obj_id}")

        # 2) Desde datos POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            obj_id = request.data.get(context_field)
            if obj_id:
                try:
                    obj = Model.objects.get(id=obj_id)
                    print(f"✅ context desde body: {context_field}={obj_id}")
                    return obj
                except Model.DoesNotExist:
                    print(f"❌ context body id no existe: {obj_id}")

        # 3) Desde objeto de vista
        if hasattr(view, 'get_object'):
            try:
                obj = view.get_object()
                if hasattr(obj, context_field):
                    print(f"✅ context desde get_object: {context_field}")
                    return getattr(obj, context_field)
            except Exception as e:
                print(f"⚠️ get_object sin contexto: {e}")

        print("⚠️ context_obj no resuelto")
        return None

    def has_object_permission(self, request, view, obj):
        """Verificar permisos a nivel de objeto"""
        if not self.has_permission(request, view):
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(obj, 'user'):
            return obj.user == request.user

        return True