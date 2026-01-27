from django.core.management.base import BaseCommand
from apps.audit.models import AuditCategory, AuditAction

class Command(BaseCommand):
    help = 'Initialize audit categories and actions'

    def handle(self, *args, **options):
        self.stdout.write('Creating audit categories and actions...')
        
        # Crear categorías
        categories = [
            {
                'name': 'Instituciones Financieras',
                'code': 'FI_MGMT',
                'description': 'Operaciones relacionadas con instituciones financieras', 
                'actions': [
                    {
                        'name': 'Crear Institución Financiera',
                        'code': 'FI_CREATE',
                        'severity': 'HIGH',
                        'description': 'Creación de una nueva institución financiera'
                    },
                    {
                        'name': 'Actualizar Institución Financiera',
                        'code': 'FI_UPDATE',
                        'severity': 'MEDIUM',
                        'description': 'Actualización de información general de una institución financiera'
                    },
                    {
                        'name': 'Eliminar Institución Financiera',
                        'code': 'FI_DELETE',
                        'severity': 'HIGH',
                        'description': 'Eliminación de una institución financiera existente'
                    },
                    {
                        'name': 'Crear Solicitud de Membresía',
                        'code': 'FI_MEMBERSHIP_REQUEST',
                        'severity': 'MEDIUM',
                        'description': 'Creación de una nueva solicitud de membresía en una institución financiera'
                    },
                    {
                        'name': 'Preaprobar Solicitud de Membresía',
                        'code': 'FI_MEMBERSHIP_PRE_APPROVAL',
                        'severity': 'MEDIUM',
                        'description': 'Preaprobación de una solicitud de membresía en una institución financiera'
                    },
                    {
                        'name': 'Enviar Contrato de Membresía',
                        'code': 'FI_MEMBERSHIP_SEND_CONTRACT',
                        'severity': 'MEDIUM',
                        'description': 'Envío del contrato de membresía a un usuario para una institución financiera'
                    },
                    {
                        'name': 'Firmar Contrato de Membresía',
                        'code': 'FI_MEMBERSHIP_SIGN_CONTRACT',
                        'severity': 'HIGH',
                        'description': 'Firma del contrato de membresía por parte de un usuario para una institución financiera'
                    },
                    {
                        'name': 'Aprobar Solicitud de Membresía',
                        'code': 'FI_MEMBERSHIP_APPROVE',
                        'severity': 'MEDIUM',
                        'description': 'Aprobación de una solicitud de membresía en una institución financiera'
                    },
                    {
                        'name': 'Rechazar Solicitud de Membresía',
                        'code': 'FI_MEMBERSHIP_REJECT',
                        'severity': 'MEDIUM',
                        'description': 'Rechazo de una solicitud de membresía en una institución financiera'  
                    }
                ]
            },
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
                        'name': 'Crear Tokens Masivos',
                        'code': 'TOKEN_BATCH_CREATE',
                        'severity': 'HIGH',
                        'description': 'Creación masiva de tokens'  
                    },
                    {
                        'name': 'Comprar Token',
                        'code': 'TOKEN_BATCH_PURCHASE',
                        'severity': 'MEDIUM',
                        'description': 'Compra de un token'
                    },
                    {
                        'name': 'Comprar Tokens Masivos',
                        'code': 'TOKEN_BATCH_PURCHASE',
                        'severity': 'MEDIUM',
                        'description': 'Compra masiva de tokens'  
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
                    },
                    {
                        'name': 'Quemar Tokens Masivos',
                        'code': 'TOKEN_BATCH_BURN',
                        'severity': 'HIGH',
                        'description': 'Eliminación masiva de tokens del sistema'
                    },
                    {
                        'name': 'Quemar Todos los Tokens',
                        'code': 'TOKEN_BATCH_BURN_ALL',
                        'severity': 'CRITICAL',
                        'description': 'Eliminación de todos los tokens del sistema'
                    }
                ]
            },
            {
                'name': 'Gestión de Fideicomisos',
                'code': 'TRUST_MGMT',
                'description': 'Operaciones de gestión de fideicomisos',
                'actions': [
                    {
                        'name': 'Crear fideicomiso',
                        'code': 'TRUST_CREATE',
                        'severity': 'HIGH',
                        'description': 'Creación de un nuevo fideicomiso'
                    },
                    {
                        'name': 'Actualizar Fideicomiso',
                        'code': 'TRUST_UPDATE',
                        'severity': 'MEDIUM',
                        'description': 'Actualización de información general de un fideicomiso'
                    },
                    {
                        'name': 'Eliminar Fideicomiso',
                        'code': 'TRUST_DELETE',
                        'severity': 'HIGH',
                        'description': 'Eliminación de un fideicomiso existente'
                    },
                    {
                        'name': 'Aprobar Fideicomiso',
                        'code': 'TRUST_APPROVE',
                        'severity': 'MEDIUM',
                        'description': 'Aprobación de un fideicomiso'
                    },
                    {
                        'name': 'Actualizar KPI',
                        'code': 'TRUST_UPDATE_KPI',
                        'severity': 'MEDIUM',
                        'description': 'Actualización de KPIs de un fideicomiso'
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
                'description': 'Operaciones de inversiones en fideicomisos',
                'actions': [
                    {
                        'name': 'Enviar Contrato de Ingreso a Fideicomiso',
                        'code': 'TRUST_MEMBERSHIP_SEND_CONTRACT',
                        'severity': 'MEDIUM',
                        'description': 'Envío del contrato de ingreso a un usuario para un fideicomiso'
                    },
                    {
                        'name': 'Firmar Contrato de Ingreso a Fideicomiso',
                        'code': 'TRUST_MEMBERSHIP_SIGN_CONTRACT',
                        'severity': 'HIGH',
                        'description': 'Firma del contrato de ingreso a un fideicomiso por parte de un usuario'
                    },
                    {
                        'name': 'Aprobar Ingreso a Fideicomiso',
                        'code': 'TRUST_MEMBERSHIP_APPROVE',
                        'severity': 'MEDIUM',
                        'description': 'Aprobación de un usuario para ingresar a un fideicomiso'
                    },
                    {
                        'name': 'Supender vinculación Fideicomiso',
                        'code': 'TRUST_MEMBERSHIP_SUSPEND',
                        'severity': 'MEDIUM',
                        'description': 'Rechazo de un usuario para ingresar a un fideicomiso'  
                    },
                    {
                        'name': 'Crear Solicitud de Inversión',
                        'code': 'INVESTMENT_APPLICATION_CREATE',
                        'severity': 'MEDIUM',
                        'description': 'Creación de una nueva solicitud de inversión en un fideicomiso'
                    },
                    {
                        'name': 'Preaprobar Solicitud de Inversión',
                        'code': 'INVESTMENT_APPLICATION_PRE_APPROVED',
                        'severity': 'MEDIUM',
                        'description': 'Preaprobación de una solicitud de inversión en un fideicomiso'
                    },
                    {
                        'name': 'En revisión Solicitud de Inversión',  
                        'code': 'INVESTMENT_APPLICATION_UNDER_REVIEW',
                        'severity': 'MEDIUM',
                        'description': 'Marcar una Solicitud de inversión como en revisión'
                    },
                    {
                        'name': 'Enviar Contrato de Sesión',
                        'code': 'INVESTMENT_APPLICATION_SEND_CONTRACT',
                        'severity': 'MEDIUM',
                        'description': 'Envío del contrato de inversión a un usuario para un fideicomiso'
                    },
                    {
                        'name': 'Firmar Contrato de Inversión',
                        'code': 'INVESTMENT_APPLICATION_SIGN_CONTRACT',
                        'severity': 'HIGH',
                        'description': 'Firma del contrato de inversión por parte de un usuario para un fideicomiso'
                    },
                    {
                        'name': 'Aprobar Solicitud de Inversión',
                        'code': 'INVESTMENT_APPLICATION_APPROVED',
                        'severity': 'MEDIUM',
                        'description': 'Aprovación de una solicitud de inversion en un fideicomiso'
                    },
                    {
                        'name': 'Rechazar Solicitud de Inversión',
                        'code': 'INVESTMENT_APPLICATION_REJECTED',
                        'severity': 'MEDIUM',
                        'description': 'Rechazo de una Solicitud de inversión en un fideicomiso'
                    },
                    {
                        'name': 'Cancelar Solicitud de Inversión',
                        'code': 'INVESTMENT_APPLICATION_CANCEL',
                        'severity': 'MEDIUM',
                        'description': 'Cancelación de una solicitud de inversión en un fideicomiso por parte del usuario'
                    },
                    
                ]
            },
            {
                'name': 'Mercado Secundario de Fideicomisos',
                'code': 'TRADING',
                'description': 'Operaciones en el mercado secundario de fideicomisos',
                'actions': [
                    {
                        'name': 'Crear Orden de Compra',
                        'code': 'PURCHASE_ORDER_CREATE',
                        'severity': 'MEDIUM',
                        'description': 'Creación de una nueva orden de compra en el mercado secundario'
                    },
                    {
                        'name': 'Cancelar Orden de Compra',
                        'code': 'PURCHASE_ORDER_CANCEL',
                        'severity': 'MEDIUM',
                        'description': 'Cancelación de una orden de compra existente'
                    },
                    {
                        'name': 'Orden de Compra Expirada',
                        'code': 'PURCHASE_ORDER_EXPIRED',
                        'severity': 'LOW',
                        'description': 'Expiración de una orden de compra en el mercado secundario'
                    },
                    {
                        'name': 'Orden de Compra Items Seleccionados',
                        'code': 'PURCHASE_MATCH_SELECTION',
                        'severity': 'MEDIUM',
                        'description': 'Selección de matches para una orden de compra en el mercado secundario'
                    },
                    {
                        'name': 'Orden de Compra Autoseleccionada',
                        'code': 'PURCHASE_AUTO_MATCH_SELECTION',
                        'severity': 'MEDIUM',
                        'description': 'Orden de compra que se autoselecciona en el mercado secundario'
                    },
                    {
                        'name': 'Orden de Compra Contrato Firmado',
                        'code': 'PURCHASE_CONTRACT_SIGNED',
                        'severity': 'HIGH',
                        'description': 'Firma del contrato para una orden de compra en el mercado secundario'
                    },
                    {
                        'name': 'Orden de Compra en Proceso de Pago',
                        'code': 'PURCHASE_PAYMENT_PROCESS',
                        'severity': 'MEDIUM',
                        'description': 'Pago de una orden de compra en proceso del mercado secundario'
                    },
                    {
                        'name': 'Orden de Compra Pagada',
                        'code': 'PURCHASE_ORDER_PAID',
                        'severity': 'MEDIUM',
                        'description': 'Pago de una orden de compra en el mercado secundario'  
                    },
                    {
                        'name': 'Orden de Compra Completada',
                        'code': 'PURCHASE_ORDER_COMPLETE',
                        'severity': 'HIGH',
                        'description': 'Finalización de una orden de compra en el mercado secundario'
                    },
                    {
                        'name': 'Crear Orden de Venta',
                        'code': 'SALES_ORDER_CREATE',
                        'severity': 'MEDIUM',
                        'description': 'Creación de una nueva orden de venta en el mercado secundario'
                    },
                    {
                        'name': 'Cancelar Orden de Venta',
                        'code': 'SALES_ORDER_CANCEL',
                        'severity': 'MEDIUM',
                        'description': 'Cancelación de una orden de venta existente'
                    },
                    {
                        'name': 'Orden de Venta Expirada',
                        'code': 'SALES_ORDER_EXPIRED',
                        'severity': 'LOW',
                        'description': 'Expiración de una orden de venta en el mercado secundario'
                    },
                    {
                        'name': 'Orden de Venta Items Seleccionados',
                        'code': 'SALES_MATCH_SELECTION',
                        'severity': 'MEDIUM',
                        'description': 'Selección de matches para una orden de venta en el mercado secundario'
                    },
                    {
                        'name': 'Orden de Venta Autoseleccionada',
                        'code': 'SALES_AUTO_MATCH_SELECTION',
                        'severity': 'MEDIUM',
                        'description': 'Orden de venta que se autoselecciona en el mercado secundario'  
                    },
                    {
                        'name': 'Orden de Venta Contrato Firmado',
                        'code': 'SALES_CONTRACT_SIGNED',
                        'severity': 'HIGH',
                        'description': 'Firma del contrato para una orden de venta en el mercado secundario'
                    },
                    {
                        'name': 'Orden de Venta Completada',
                        'code': 'SALES_ORDER_COMPLETE',
                        'severity': 'HIGH',
                        'description': 'Finalización de una orden de venta en el mercado secundario'
                    },
                    {
                        'name': 'Advertencia de Unidades Insuficientes',
                        'code': 'AUTO_SELECTION_WARNING',
                        'severity': 'LOW',
                        'description': 'Advertencia de unidades insuficientes al seleccionar matches para una orden de compra'
                    },
                ]
            },
            {
                'name': 'Distribuciones',
                'code': 'DISTRIBUTIONS',
                'description': 'Distribuciones en fideicomisos',
                'actions': [
                    {
                        'name': 'Crear distribucion',
                        'code': 'DISTRIBUTION_CREATE',
                        'severity': 'MEDIUM',
                        'description': 'Creación de un registro de distribucion según el periodo especificado'
                    },
                ]              
            },
            {
                'name': 'Activos',
                'code': 'ASSETS',
                'description': 'Activos vinculados a fideicomisos',
                'actions': [
                    {
                        'name': 'Crear activo',
                        'code': 'ASSET_CREATE',
                        'severity': 'MEDIUM',
                        'description': 'Creación de un activo'
                    }
                ]
            },
            {
                'name': 'Contabilidad',
                'code': 'ACCOUNTING',
                'description': 'Operaciones contables de fideicomisos',
                'actions': [
                    {
                        'name': 'Crear registro de factura',
                        'code': 'INVOICE_RECORD_CREATE',
                        'severity': 'MEDIUM',
                        'description': 'Creación de un nuevo registro de factura para un fideicomiso'
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