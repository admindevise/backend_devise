from django.core.management.base import BaseCommand
from apps.financial_institution.models.permissions import FIPermission


class Command(BaseCommand):
    help = 'Crear permisos iniciales para Financial Institution'

    def handle(self, *args, **options):
        self.stdout.write("🔄 Creando permisos de Financial Institution...")
        
        permissions = [
            # Permisos de aplicaciones
            {
                'codename': 'view_applications',
                'name': 'Ver Solicitudes',
                'description': 'Permite ver solicitudes de membresía',
                'category': 'applications',
                'module': 'fi'
            },
            {
                'codename': 'create_applications',
                'name': 'Crear Solicitudes',
                'description': 'Permite crear solicitudes de membresía',
                'category': 'applications',
                'module': 'fi'
            },
            {
                'codename': 'approve_applications',
                'name': 'Aprobar Solicitudes',
                'description': 'Permite aprobar solicitudes de membresía',
                'category': 'applications',
                'module': 'fi'
            },
            {
                'codename': 'reject_applications',
                'name': 'Rechazar Solicitudes',
                'description': 'Permite rechazar solicitudes de membresía',
                'category': 'applications',
                'module': 'fi'
            },
            
            # Permisos de miembros
            {
                'codename': 'view_members',
                'name': 'Ver Miembros',
                'description': 'Permite ver lista de miembros',
                'category': 'members',
                'module': 'fi'
            },
            {
                'codename': 'manage_members',
                'name': 'Gestionar Miembros',
                'description': 'Permite agregar/remover miembros',
                'category': 'members',
                'module': 'fi'
            },
            
            # Permisos de fondos
            {
                'codename': 'view_funds',
                'name': 'Ver Fondos',
                'description': 'Permite ver fondos disponibles',
                'category': 'funds',
                'module': 'fi'
            },
            {
                'codename': 'create_funds',
                'name': 'Crear Fondos',
                'description': 'Permite crear nuevos fondos',
                'category': 'funds',
                'module': 'fi'
            },
            {
                'codename': 'manage_funds',
                'name': 'Gestionar Fondos',
                'description': 'Permite editar/eliminar fondos',
                'category': 'funds',
                'module': 'fi'
            },
            
            # Permisos de contratos
            {
                'codename': 'send_contracts',
                'name': 'Enviar Contratos',
                'description': 'Permite enviar contratos a usuarios',
                'category': 'contracts',
                'module': 'fi'
            },
            {
                'codename': 'sign_contracts',
                'name': 'Firmar Contratos',
                'description': 'Permite firmar contratos',
                'category': 'contracts',
                'module': 'fi'
            },
            
            # Permisos de reportes
            {
                'codename': 'view_reports',
                'name': 'Ver Reportes',
                'description': 'Permite ver reportes y estadísticas',
                'category': 'reports',
                'module': 'fi'
            },
            {
                'codename': 'export_data',
                'name': 'Exportar Datos',
                'description': 'Permite exportar datos en Excel/PDF',
                'category': 'reports',
                'module': 'fi'
            },
            
            # Permisos administrativos
            {
                'codename': 'manage_groups',
                'name': 'Gestionar Grupos',
                'description': 'Permite crear/editar grupos',
                'category': 'admin',
                'module': 'fi'
            },
            {
                'codename': 'manage_permissions',
                'name': 'Gestionar Permisos',
                'description': 'Permite asignar permisos a grupos',
                'category': 'admin',
                'module': 'fi'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for perm_data in permissions:
            perm, created = FIPermission.objects.update_or_create(
                codename=perm_data['codename'],
                defaults=perm_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ Creado: {perm.name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"  🔄 Actualizado: {perm.name}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Proceso completado: {created_count} creados, {updated_count} actualizados"
        ))