from django.db import transaction
from django.utils import timezone

from apps.trading.audit_helper.audit_helper_create_orders import AuditHelperCreateOrders as AuditService
from apps.trading.audit_helper.audit_helper_cancel_orders import AuditHelperCancelOrders
from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from apps.trading.security.token_validators import (
    TradingAvailabilityService,
    TokenReservationManager
)

class OrderCreationService:
    """
    Servicio para la creación segura de órdenes de trading
    Coordina validaciones, reservas y auditoría
    """
    
    def __init__(self):
        self.availability_service = TradingAvailabilityService()
        self.reservation_manager = TokenReservationManager()
    
    
    @transaction.atomic
    def create_sales_order(self, user, order_data: dict, request=None) -> dict:
        """
        Crea una orden de venta con todas las validaciones y reservas necesarias
        """
        fund = order_data['fund']
        quantity = order_data['units']
        initial_audit = None
        
        # Validar que el usuario tiene permisos para crear órdenes de venta
        seller_user = order_data['seller_user']
        
        try:
            # Iniciar auditoría
            initial_audit = AuditService.initial_audit_log(
                user=user,
                action_code='SALES_ORDER_CREATE',
                request=request
            )
            
            # 1. Validar viabilidad completa de la orden
            feasibility = self.availability_service.validate_sales_order_feasibility(
                user, fund.id, quantity=quantity, target_user=seller_user,
            )
            
            if not feasibility['feasible']:
                error_details = []
                for error in feasibility['errors']:
                    error_details.append(f"• {error}")
                
                error_msg = f"Orden no viable: " + " ".join(error_details)
                raise ValueError(error_msg)
            
            # 2. Obtener tokens seleccionados automáticamente
            selected_tokens = feasibility['validations']['auto_select']['token_ids']
            
            # 3. Reservar tokens para la venta
            reservation_result = self.reservation_manager.reserve_tokens_for_sale(
                seller_user, selected_tokens, fund.id
            )
            
            if not reservation_result['success']:
                raise ValueError(f"Error reservando tokens: {reservation_result['failed_reservations']}")
            
            # 4. Crear la orden
            sales_order = SalesOrder.objects.create(
                **order_data,
                created_by=user,
                status='PENDING',
                reserved_tokens_info={
                    'token_ids':  selected_tokens,
                    'total_tokens_reserved': len(selected_tokens),
                    'reserved_at': timezone.now().isoformat()
                }
            )
                        
            # 5. Auditoría de éxito
            AuditService.update_audit_log(initial_audit, sales_order)
            
            return {
                'success': True,
                'sales_order': sales_order,
                'reserved_tokens': selected_tokens,
                'feasibility_check': feasibility
            }
            
        except Exception as e:
            # Liberar reservas en caso de error
            if 'selected_tokens' in locals():
                self.reservation_manager.release_token_reservations(selected_tokens, fund.id)
            
            # Auditoría de error
            AuditService.update_audit_log_error(initial_audit, str(e))
            raise

    @transaction.atomic
    def create_purchase_order(self, user, order_data: dict, request=None) -> dict:
        """
        Crea una orden de compra con validaciones de liquidez
        """
        fund = order_data['fund']
        quantity = order_data['units']
        initial_audit = None
        supplier_user = order_data['supplier_user']
        
        try:
            # Iniciar auditoría
            initial_audit = AuditService.initial_audit_log(
                user=user,
                action_code='PURCHASE_ORDER_CREATE',
                request=request
            )
            
            # 1. Validar viabilidad de la orden de compra
            feasibility = self.availability_service.validate_purchase_order_feasibility(
                user, fund.id, quantity, target_user=supplier_user
            )
            
            if not feasibility['feasible']:
                raise ValueError(f"Orden no viable: {'; '.join(feasibility['errors'])}")
            
            # 2. Crear la orden (sin reservar tokens aún - se hace al pagar)
            purchase_order = PurchaseOrder.objects.create(
                **order_data,
                created_by=user,
                status='PENDING'
            )
            
            # 3. Registrar metadatos
            if hasattr(purchase_order, 'metadata'):
                # Serializar feasibility_check sin objetos complejos
                feasibility_serialized = {}
                for key, value in feasibility.items():
                    if key == 'validations':
                        # Serializar validaciones complejas
                        validations_serialized = {}
                        for val_key, val_value in value.items():
                            if val_key == 'investor_status' and 'application' in val_value:
                                # ✅ CORREGIR: Verificar el tipo de application antes de acceder
                                app = val_value['application']
                                
                                # Caso 1: Es un objeto FundApplication real
                                if hasattr(app, 'id') and hasattr(app, 'status'):
                                    validations_serialized[val_key] = {
                                        'valid': val_value['valid'],
                                        'is_staff': val_value.get('is_staff', False),
                                        'application_id': app.id,
                                        'application_status': app.status,
                                        'fund_id': app.fund.id if hasattr(app, 'fund') and app.fund else None
                                    }
                                # Caso 2: Es un boolean (staff bypass o validación simple)
                                elif isinstance(app, bool):
                                    validations_serialized[val_key] = {
                                        'valid': val_value['valid'],
                                        'is_staff': val_value.get('is_staff', False),
                                        'application_id': None,
                                        'application_status': 'staff_bypass' if app else 'no_application',
                                        'fund_id': fund.id  # Usar el fund de la orden
                                    }
                                # Caso 3: Es None u otro tipo
                                else:
                                    validations_serialized[val_key] = {
                                        'valid': val_value['valid'],
                                        'is_staff': val_value.get('is_staff', False),
                                        'application_id': None,
                                        'application_status': None,
                                        'fund_id': fund.id  # Usar el fund de la orden
                                    }
                            else:
                                # ✅ Para otros tipos de validación
                                validations_serialized[val_key] = val_value
                        
                        feasibility_serialized[key] = validations_serialized
                    else:
                        feasibility_serialized[key] = value
                
                purchase_order.metadata = {
                    'feasibility_check': feasibility_serialized,
                    'available_tokens_at_creation': feasibility.get('available_tokens', 0)
                }
                purchase_order.save(update_fields=['metadata'])
            
            # 4. Auditoría de éxito
            AuditService.update_audit_log(initial_audit, purchase_order)
            
            return {
                'success': True,
                'purchase_order': purchase_order,
                'feasibility_check': feasibility
            }
            
        except Exception as e:
            # Auditoría de error
            AuditService.update_audit_log_error(initial_audit, str(e))

            raise


class OrderManagementService:
    """
    Servicio para gestión de órdenes existentes
    """
    
    def __init__(self):
        self.reservation_manager = TokenReservationManager()
    
    
    @transaction.atomic
    def cancel_sales_order(self, sales_order, user, request=None) -> dict:
        """
        Cancela una orden de venta y libera las reservas de tokens
        """
        initial_audit = None
        
        try:
            # Iniciar auditoría
            initial_audit = AuditHelperCancelOrders.initial_audit_log(
                user=user,
                order_id=sales_order.id,
                action_code='SALES_ORDER_CANCEL',
                reason='User requested cancellation',
                request=request
            )

            # 1. Verificar que la orden se pueda cancelar
            if not sales_order.status == SalesOrder.SalesOrderStatus.PENDING:
                raise ValueError(f"Cannot cancel order with status: {sales_order.status}")
            
            # 2. Obtener tokens reservados de los metadatos
            reserved_tokens = []
            if hasattr(sales_order, 'reserved_tokens_info') and sales_order.reserved_tokens_info:
                reserved_tokens = sales_order.reserved_tokens_info.get('token_ids', [])
            
                print(f'Tokens encontrados en reserved_tokens_info: {len(reserved_tokens)}')
        
            # 3. Liberar reservas de tokens
            if reserved_tokens:
                release_result = self.reservation_manager.release_token_reservations(
                    reserved_tokens, sales_order.fund.id
                )
                
                if not release_result['success']:
                    raise ValueError(f"Error liberando tokens: {reserved_tokens}")
            
            # 4. Actualizar estado de la orden
            sales_order.status = 'CANCELLED'
            sales_order.cancelled_at = timezone.now()
            sales_order.save(update_fields=['status', 'cancelled_at'])
            
            # 5. Auditoría de éxito
            AuditHelperCancelOrders.update_audit_log(initial_audit, sales_order)
                
            return {
                'success': True,
                'released_tokens': len(reserved_tokens),
                'order_status': sales_order.status
            }
            
        except Exception as e:
            # Auditoría de error
            AuditHelperCancelOrders.update_audit_log_error(initial_audit, str(e))
            raise
    
    @transaction.atomic
    def cancel_purchase_order(self, purchase_order, user, request=None) -> dict:
        """
        Cancela una orden de compra
        """
        initial_audit = None
        
        try:
            # Iniciar auditoría
            initial_audit = AuditHelperCancelOrders.initial_audit_log(
                user=user,
                order_id=purchase_order.id,
                action_code='PURCHASE_ORDER_CANCEL',
                reason='User requested cancellation',
                request=request
            )
            
            # 1. Verificar que la orden se pueda cancelar
            if not purchase_order.status == PurchaseOrder.PurchaseOrderStatus.PENDING:
                raise ValueError(f"La orden no se puede eliminar con estado: {purchase_order.status}")
            
            # 2. Actualizar estado de la orden
            purchase_order.status = 'CANCELLED'
            purchase_order.cancelled_at = timezone.now()
            purchase_order.save(update_fields=['status', 'cancelled_at'])
            
            # 3. Auditoría de éxito
            AuditHelperCancelOrders.update_audit_log(initial_audit, purchase_order)

            return {
                'success': True,
                'order_status': purchase_order.status
            }
            
        except Exception as e:
            # Auditoría de error
            AuditHelperCancelOrders.update_audit_log_error(initial_audit, str(e))
            raise
        

