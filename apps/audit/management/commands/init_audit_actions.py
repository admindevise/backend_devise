from django.core.management.base import BaseCommand
from apps.audit.models import AuditCategory, AuditAction

class Command(BaseCommand):
    help = 'Initialize audit categories and actions'

    def handle(self, *args, **options):
        self.stdout.write('Creating audit categories and actions...')
        
        # Crear categorías
        categories = [
            {
                'name': 'Transacciones Token',
                'code': 'TOKEN_TX',
                'description': 'Transacciones relacionadas con tokens',
                'actions': [
                    {
                        'name': 'Crear Token',
                        'code': 'TOKEN_CREATE',
                        'severity': 'HIGH',
                        'description': 'Creación de un nuevo token'
                    },
                    {
                        'name': 'Transferir Token',
                        'code': 'TOKEN_TRANSFER',
                        'severity': 'MEDIUM',
                        'description': 'Transferencia de un token entre carteras'
                    },
                    {
                        'name': 'Quemar Token',
                        'code': 'TOKEN_BURN',
                        'severity': 'HIGH',
                        'description': 'Eliminación de un token del sistema'
                    }
                ]
            },
            {
                'name': 'Gestión de Fondos',
                'code': 'FUND_MGMT',
                'description': 'Operaciones de gestión de fondos',
                'actions': [
                    {
                        'name': 'Crear Fondo',
                        'code': 'FUND_CREATE',
                        'severity': 'HIGH',
                        'description': 'Creación de un nuevo fondo'
                    },
                    {
                        'name': 'Actualizar Fondo',
                        'code': 'FUND_UPDATE',
                        'severity': 'MEDIUM',
                        'description': 'Actualización de información general de un fondo'
                    },
                    {
                        'name': 'Eliminar Fondo',
                        'code': 'FUND_DELETE',
                        'severity': 'HIGH',
                        'description': 'Eliminación de un fondo existente'
                    },
                    {
                        'name': 'Aprobar Fondo',
                        'code': 'FUND_APPROVE',
                        'severity': 'MEDIUM',
                        'description': 'Aprobación de un fondo'
                    },
                    {
                        'name': 'Actualizar KPI',
                        'code': 'FUND_UPDATE_KPI',
                        'severity': 'MEDIUM',
                        'description': 'Actualización de KPIs de un fondo'
                    }
                ]
            },
            {
                'name': 'Smart Contracts',
                'code': 'SMARTCONTRACT',
                'description': 'Operaciones con contratos inteligentes',
                'actions': [
                    {
                        'name': 'Crear Smart Contract',
                        'code': 'SC_CREATE',
                        'severity': 'CRITICAL',
                        'description': 'Creación de un nuevo contrato inteligente'
                    },
                    {
                        'name': 'Compilar Smart Contract',
                        'code': 'SC_COMPILE',
                        'severity': 'HIGH',
                        'description': 'Compilación de un contrato inteligente'
                    },
                    {
                        'name': 'Promover Smart Contract',
                        'code': 'SC_PROMOTE',
                        'severity': 'HIGH',
                        'description': 'Promoción de un contrato inteligente compilado a un entorno'
                    },
                ]
            },
            {
                'name': 'Inversiones',
                'code': 'INVESTMENT',
                'description': 'Operaciones de inversiones en fondos',
                'actions': [
                    {
                        'name': 'Crear Aplicación de Inversión',
                        'code': 'INVESTMENT_APPLICATION_CREATE',
                        'severity': 'MEDIUM',
                        'description': 'Creación de una nueva aplicación de inversión en un fondo'
                    },
                    {
                        'name': 'Aprobar Aplicación de Inversión',
                        'code': 'INVESTMENT_APPLICATION_APPROVED',
                        'severity': 'MEDIUM',
                        'description': 'Aprovación de una aplicacion de inversion en un fondo'
                    },
                    {
                        'name': 'Rechazar Aplicación de Inversión',
                        'code': 'INVESTMENT_APPLICATION_REJECTED',
                        'severity': 'MEDIUM',
                        'description': 'Rechazo de una aplicación de inversión en un fondo'
                    },
                    {
                        'name': 'En revisión Aplicación de Inversión',  
                        'code': 'INVESTMENT_APPLICATION_UNDER_REVIEW',
                        'severity': 'MEDIUM',
                        'description': 'Marcar una aplicación de inversión como en revisión'
                    },
                    {
                        'name': 'Crear Inversión', 
                        'code': 'INVESTMENT_CREATE',
                        'severity': 'HIGH',
                        'description': 'Creación de una nueva inversión en un fondo'
                    },
                    {
                        'name': 'Modificar Inversión',
                        'code': 'INVESTMENT_UPDATE', 
                        'severity': 'MEDIUM',
                        'description': 'Modificación de una inversión existente'
                    },
                    {
                        'name': 'Eliminar Inversión',
                        'code': 'INVESTMENT_DELETE',
                        'severity': 'HIGH', 
                        'description': 'Eliminación de una inversión en un fondo'
                    }
                ]
            }
        ]
        
        for cat_data in categories:
            actions = cat_data.pop('actions')
            category, created = AuditCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f"Created category: {category.name}")
            
            for action_data in actions:
                action, created = AuditAction.objects.get_or_create(
                    code=action_data['code'],
                    defaults={**action_data, 'category': category}
                )
                if created:
                    self.stdout.write(f"Created action: {action.name}")
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized audit data'))