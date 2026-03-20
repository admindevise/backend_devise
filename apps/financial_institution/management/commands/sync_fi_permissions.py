from django.core.management.base import BaseCommand
from django.db import transaction

from apps.financial_institution.models.permissions import FIPermission
from apps.utils.core_permissions.permissions_config import VIEWSET_PERMISSION_MAP


PERMISSION_METADATA = {
    "list_view_financial_institutions": {"name": "Listar instituciones financieras", "category": "general"},
    "view_financial_institutions": {"name": "Ver instituciones financieras", "category": "general"},
    "create_financial_institution": {"name": "Crear institución financiera", "category": "general"},

    "list_view_applications": {"name": "Listar solicitudes", "category": "applications"},
    "view_applications": {"name": "Ver solicitudes", "category": "applications"},
    "create_applications": {"name": "Crear solicitudes", "category": "applications"},
    "pre_approve_applications": {"name": "Pre-aprobar solicitudes", "category": "applications"},
    "send_contract_applications": {"name": "Enviar contrato de solicitudes", "category": "applications"},
    "sign_contract_applications": {"name": "Firmar contrato de solicitudes", "category": "applications"},
    "approve_applications": {"name": "Aprobar solicitudes", "category": "applications"},
    "reject_applications": {"name": "Rechazar solicitudes", "category": "applications"},
    "pending_applications": {"name": "Ver solicitudes pendientes", "category": "applications"},
    "list_pending_applications": {"name": "Listar solicitudes pendientes", "category": "applications"},
    "list_approve_applications": {"name": "Listar solicitudes por aprobar", "category": "applications"},

    "list_view_members": {"name": "Listar miembros", "category": "members"},
    "view_members": {"name": "Ver miembros", "category": "members"},
    "list_view_memberships": {"name": "Listar membresías", "category": "members"},
    "view_memberships": {"name": "Ver membresías", "category": "members"},
    "assign_user_to_group": {"name": "Asignar usuario a grupo", "category": "members"},
    "remove_user_from_group": {"name": "Remover usuario de grupo", "category": "members"},
    "view_my_permissions": {"name": "Ver mis permisos", "category": "members"},

    "list_view_permissions": {"name": "Listar permisos", "category": "permissions"},
    "view_permissions": {"name": "Ver permisos", "category": "permissions"},
    "create_permissions": {"name": "Crear permisos", "category": "permissions"},
    "delete_permissions": {"name": "Eliminar permisos", "category": "permissions"},

    "list_view_group_permissions": {"name": "Listar grupos de permisos", "category": "groups"},
    "view_group_permissions": {"name": "Ver grupos de permisos", "category": "groups"},
    "create_group_permissions": {"name": "Crear grupos de permisos", "category": "groups"},
    "delete_group_permissions": {"name": "Eliminar grupos de permisos", "category": "groups"},

    "view_dashboard_stats": {"name": "Ver estadísticas de dashboard", "category": "dashboard"},

    "view_funds": {"name": "Ver fondos", "category": "fund"},
    "create_funds": {"name": "Crear fondos", "category": "fund"},
    "manage_funds": {"name": "Gestionar fondos", "category": "fund"},
    "view_investments": {"name": "Ver inversiones", "category": "fund"},
    "create_investment": {"name": "Crear inversión", "category": "fund"},
    "approve_investment": {"name": "Aprobar inversión", "category": "fund"},
    "reject_investment": {"name": "Rechazar inversión", "category": "fund"},
    "send_investor_contract": {"name": "Enviar contrato de inversionista", "category": "fund"},
    "sign_investor_contract": {"name": "Firmar contrato de inversionista", "category": "fund"},
    "view_fund_members": {"name": "Ver miembros del fondo", "category": "fund"},

    # TRADING
    "list_view_purchase_orders": {"name": "Listar órdenes de compra", "category": "trading"},
    "view_purchase_orders": {"name": "Ver órdenes de compra", "category": "trading"},
    "create_purchase_order": {"name": "Crear orden de compra", "category": "trading"},
    "cancel_purchase_order": {"name": "Cancelar orden de compra", "category": "trading"},

    "list_view_sales_orders": {"name": "Listar órdenes de venta", "category": "trading"},
    "view_sales_orders": {"name": "Ver órdenes de venta", "category": "trading"},
    "create_sales_order": {"name": "Crear orden de venta", "category": "trading"},
    "cancel_sales_order": {"name": "Cancelar orden de venta", "category": "trading"},
    "reserve_tokens_sales_order": {"name": "Ver tokens reservados en orden de venta", "category": "trading"},

    "list_view_transactions": {"name": "Listar transacciones", "category": "trading"},
    "view_transactions": {"name": "Ver transacciones", "category": "trading"},

    "list_view_contracts": {"name": "Listar contratos", "category": "trading"},
    "view_contracts": {"name": "Ver contratos", "category": "trading"},
    "list_pending_contracts": {"name": "Listar contratos pendientes", "category": "trading"},
    "approve_or_reject_contract": {"name": "Aprobar o rechazar contrato", "category": "trading"},

    "list_view_match_selections": {"name": "Listar selecciones de match", "category": "trading"},
    "view_match_selections": {"name": "Ver selecciones de match", "category": "trading"},
    "view_active_match_selections": {"name": "Ver selecciones activas", "category": "trading"},
    "cleanup_expired_match_selections": {"name": "Limpiar selecciones expiradas", "category": "trading"},
    "create_match_selection": {"name": "Crear selección de match", "category": "trading"},
    "validate_selection_capability": {"name": "Validar capacidad de selección", "category": "trading"},
    "cancel_match_selection": {"name": "Cancelar selección de match", "category": "trading"},

    "grant_trading_permission": {"name": "Otorgar permisos de trading", "category": "trading"},
    "list_user_permissions_trading": {"name": "Listar permisos de usuario", "category": "trading"},

    "find_order_matches": {"name": "Buscar coincidencias de órdenes", "category": "trading"},
    "execute_payment": {"name": "Ejecutar pago", "category": "trading"},
    "view_active_orders": {"name": "Ver órdenes activas", "category": "trading"},
    "cleanup_expired_reservations": {"name": "Limpiar reservas expiradas", "category": "trading"},
    "view_selection_stats": {"name": "Ver estadísticas de selecciones", "category": "trading"},
    "view_negotiation_dashboard": {"name": "Ver dashboard de negociación", "category": "trading"},
    "view_negotiation_status_options": {"name": "Ver opciones de estado de negociación", "category": "trading"},
    "list_unified_orders": {"name": "Listar órdenes unificadas", "category": "trading"},
}


def _fallback_name(codename: str) -> str:
    return codename.replace("_", " ").capitalize()


def _ensure_all_permissions_from_map():
    """
    Garantiza metadata para TODOS los permisos definidos en VIEWSET_PERMISSION_MAP.
    Si falta alguno, se crea automáticamente con nombre/categoría por defecto.
    """
    for _, actions in VIEWSET_PERMISSION_MAP.items():
        for _, perm_tuple in actions.items():
            if not isinstance(perm_tuple, (tuple, list)) or len(perm_tuple) != 2:
                continue

            module, codename = perm_tuple
            if codename not in PERMISSION_METADATA:
                PERMISSION_METADATA[codename] = {
                    "name": _fallback_name(codename),
                    "category": module,
                }


_ensure_all_permissions_from_map()


class Command(BaseCommand):
    help = "Sincroniza FIPermission desde VIEWSET_PERMISSION_MAP"

    def add_arguments(self, parser):
        parser.add_argument(
            "--modules",
            nargs="+",
            default=None,
            help="Filtrar módulos (ej: --modules fi fund trading)",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Desactiva permisos que no estén en VIEWSET_PERMISSION_MAP (según filtro de módulos).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        modules_filter = set(options["modules"]) if options["modules"] else None
        deactivate_missing = options["deactivate_missing"]

        desired = set()

        for _, actions in VIEWSET_PERMISSION_MAP.items():
            for _, perm_tuple in actions.items():
                if not isinstance(perm_tuple, (tuple, list)) or len(perm_tuple) != 2:
                    continue

                module, codename = perm_tuple
                if modules_filter and module not in modules_filter:
                    continue
                desired.add((module, codename))

        created = 0
        updated = 0

        for module, codename in sorted(desired):
            meta = PERMISSION_METADATA.get(codename, {})
            name = meta.get("name", _fallback_name(codename))
            category = meta.get("category", module)

            obj, was_created = FIPermission.objects.update_or_create(
                module=module,
                codename=codename,
                defaults={
                    "name": name,
                    "category": category,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"CREATED  [{module}] {codename}"))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(f"UPDATED  [{module}] {codename}"))

        deactivated = 0
        if deactivate_missing:
            qs = FIPermission.objects.all()
            if modules_filter:
                qs = qs.filter(module__in=modules_filter)

            for perm in qs:
                if (perm.module, perm.codename) not in desired and perm.is_active:
                    perm.is_active = False
                    perm.save(update_fields=["is_active"])
                    deactivated += 1
                    self.stdout.write(self.style.ERROR(f"DEACTIVATED [{perm.module}] {perm.codename}"))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Sincronización completada. Created={created}, Updated={updated}, Deactivated={deactivated}"
            )
        )