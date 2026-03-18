from django.core.management.base import BaseCommand
from django.db import transaction

from apps.financial_institution.models import FinancialInstitution
from apps.financial_institution.models.permissions import FICustomGroup, FIPermission


class Command(BaseCommand):
    help = "Crea/actualiza grupos base por FI: STAFF, ADMINISTRADOR e INVERSIONISTA"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fi-id",
            type=int,
            default=None,
            help="ID de FinancialInstitution (si no se envía, procesa todas).",
        )
        parser.add_argument(
            "--with-permissions",
            action="store_true",
            help="Asigna permisos por defecto a los grupos creados.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        fi_id = options["fi_id"]
        with_permissions = options["with_permissions"]

        fis = FinancialInstitution.objects.all()
        if fi_id:
            fis = fis.filter(id=fi_id)

        if not fis.exists():
            self.stdout.write(self.style.ERROR("No se encontraron instituciones financieras."))
            return

        created = 0
        updated = 0

        for fi in fis:
            staff_group, staff_created = FICustomGroup.objects.update_or_create(
                financial_institution=fi,
                name="STAFF",
                defaults={
                    "description": "Grupo base de staff",
                    "is_active": True,
                },
            )

            admin_group, admin_created = FICustomGroup.objects.update_or_create(
                financial_institution=fi,
                name="ADMINISTRADOR",
                defaults={
                    "description": "Grupo base de administración",
                    "is_active": True,
                },
            )

            investor_group, investor_created = FICustomGroup.objects.update_or_create(
                financial_institution=fi,
                name="INVERSIONISTA",
                defaults={
                    "description": "Grupo base de inversionistas",
                    "is_active": True,
                },
            )

            created += int(staff_created) + int(admin_created) + int(investor_created)
            updated += int(not staff_created) + int(not admin_created) + int(not investor_created)

            if with_permissions:
                self._assign_default_permissions(staff_group, admin_group, investor_group)

            self.stdout.write(
                self.style.SUCCESS(
                    f"[FI {fi.id}] STAFF={'CREATED' if staff_created else 'UPDATED'} | "
                    f"ADMINISTRADOR={'CREATED' if admin_created else 'UPDATED'} | "
                    f"INVERSIONISTA={'CREATED' if investor_created else 'UPDATED'}"
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Completado. Groups created={created}, updated={updated}"
            )
        )

    def _assign_default_permissions(self, staff_group, admin_group, investor_group):
        # STAFF: permisos operativos base
        staff_codenames = [
            "view_permissions",
            "view_members",
            "view_applications",
        ]
        staff_perms = FIPermission.objects.filter(
            module="fi",
            codename__in=staff_codenames,
            is_active=True,
        )
        staff_group.permissions.set(staff_perms)

        # ADMINISTRADOR: todos los permisos de módulo FI
        admin_perms = FIPermission.objects.filter(module="fi", is_active=True)
        admin_group.permissions.set(admin_perms)

        # INVERSIONISTA: permisos de consulta
        investor_codenames = [
            "view_permissions",
            "view_applications",
        ]
        investor_perms = FIPermission.objects.filter(
            module="fi",
            codename__in=investor_codenames,
            is_active=True,
        )
        investor_group.permissions.set(investor_perms)