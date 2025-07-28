from django.db import transaction
from django.utils import timezone
from apps.trading.security.token_validators import TradingAvailabilityService, TokenReservationManager
from apps.audit.audit_service import AuditService
from apps.trading.models import PurchaseOrder, SalesOrder

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
        
        # Validar que el usuario tiene permisos para crear órdenes de venta
        target_user = order_data.get('seller_user', user)
        
        try:
            # 1. Validar viabilidad completa de la orden
            feasibility = self.availability_service.validate_sales_order_feasibility(
                user, fund.id, quantity=quantity, target_user=target_user,
            )
            
            if not feasibility['feasible']:
                error_details = []
                for error in feasibility['errors']:
                    error_details.append(f"• {error}")
                
                error_msg = f"Orden no viable:\n" + "\n".join(error_details)
                raise ValueError(error_msg)
            
            # 2. Obtener tokens seleccionados automáticamente
            selected_tokens = feasibility['validations']['auto_select']['token_ids']
            
            # 3. Reservar tokens para la venta
            reservation_result = self.reservation_manager.reserve_tokens_for_sale(
                target_user, selected_tokens, fund.id
            )
            
            if not reservation_result['success']:
                raise ValueError(f"Error reservando tokens: {reservation_result['failed_reservations']}")
            
            order_data['seller_user'] = target_user
            
            # 4. Crear la orden
            sales_order = SalesOrder.objects.create(
                **order_data,
                created_by=user,
                status='PENDING'
            )
            
            # 5. Registrar metadatos de la reserva
            if hasattr(sales_order, 'metadata'):
                sales_order.metadata = {
                    'total_tokens_reserved': len(selected_tokens),
                    'reserved_tokens': selected_tokens,
                    'feasibility_validated': feasibility['feasible'],
                }
                sales_order.save(update_fields=['metadata'])
                        
            # 6. Auditoría de éxito
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='SALES_ORDER_CREATE',
                    obj=sales_order,
                    details={
                        'user_id': user.id,
                        'fund_id': fund.id,
                        'quantity': quantity,
                        'price_per_unit': float(order_data.get('price_per_unit', 0)), 
                        'sales_order_id': str(sales_order.id),
                        'reserved_tokens': len(selected_tokens),
                        'selected_tokens': selected_tokens,
                        'operation': 'create_sales_order'
                    },
                    status='SUCCESS'
                )
            
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
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='SALES_ORDER_CREATE',
                    obj=fund,
                    details={
                        'user_id': user.id,
                        'fund_id': fund.id,
                        'quantity': quantity,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'operation': 'create_sales_order'
                    },
                    status='ERROR'
                )
            
            raise

    @transaction.atomic
    def create_purchase_order(self, user, order_data: dict, request=None) -> dict:
        """
        Crea una orden de compra con validaciones de liquidez
        """
        fund = order_data['fund']
        quantity = order_data['units']
        
        target_user = order_data.get('supplier_user', user)
        
        try:
            # 1. Validar viabilidad de la orden de compra
            feasibility = self.availability_service.validate_purchase_order_feasibility(
                user, fund.id, quantity, target_user=target_user
            )
            
            if not feasibility['feasible']:
                raise ValueError(f"Orden no viable: {'; '.join(feasibility['errors'])}")
            
            order_data['supplier_user'] = target_user
            
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
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='PURCHASE_ORDER_CREATE',
                    obj=purchase_order,
                    details={
                        'user_id': user.id,
                        'fund_id': fund.id,
                        'quantity': quantity,
                        'price_per_unit': float(order_data.get('price_per_unit', 0)), 
                        'purchase_order_id': str(purchase_order.id),
                        'available_tokens': feasibility.get('available_tokens', 0),
                        'operation': 'create_purchase_order'
                    },
                    status='SUCCESS'
                )
            
            return {
                'success': True,
                'purchase_order': purchase_order,
                'feasibility_check': feasibility
            }
            
        except Exception as e:
            # Auditoría de error
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='PURCHASE_ORDER_CREATE',
                    obj=fund,
                    details={
                        'user_id': user.id,
                        'fund_id': fund.id,
                        'quantity': quantity,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'operation': 'create_purchase_order'
                    },
                    status='ERROR'
                )

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
        print('entro a la funcion')
        try:
            # 1. Verificar que la orden se pueda cancelar
            if not sales_order.status == SalesOrder.SalesOrderStatus.PENDING:
                raise ValueError(f"Cannot cancel order with status: {sales_order.status}")
            
            # 2. Obtener tokens reservados de los metadatos
            reserved_tokens = []
            if hasattr(sales_order, 'metadata') and sales_order.metadata:
                reserved_tokens = sales_order.metadata.get('reserved_tokens', [])
            
            # 3. Liberar reservas de tokens
            if reserved_tokens:
                release_result = self.reservation_manager.release_token_reservations(
                    reserved_tokens, sales_order.fund.id
                )
                
                if not release_result['success']:
                    print('Error liberando reservas de tokens:', release_result['failed_releases'])
            
            # 4. Actualizar estado de la orden
            sales_order.status = 'CANCELLED'
            sales_order.cancelled_at = timezone.now()
            sales_order.save(update_fields=['status', 'cancelled_at'])
            
            # 5. Auditoría de éxito
            if request:
                print('paso por audit')
                AuditService.log_action(
                    request=request,
                    action_code='SALES_ORDER_CANCEL',
                    obj=sales_order,
                    details={
                        'order_id': str(sales_order.id),
                        'released_tokens': len(reserved_tokens),
                        'cancelled_at': sales_order.cancelled_at.isoformat(),
                        'operation': 'cancel_sales_order'
                    },
                    status='SUCCESS'
                )
                
            return {
                'success': True,
                'released_tokens': len(reserved_tokens),
                'order_status': sales_order.status
            }
            
        except Exception as e:
            # Auditoría de error
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='SALES_ORDER_CANCEL',
                    obj=sales_order,
                    details={
                        'order_id': str(sales_order.id),
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'operation': 'cancel_sales_order'
                    },
                    status='ERROR'
                )
            raise
    
    @transaction.atomic
    def cancel_purchase_order(self, purchase_order, user, request=None) -> dict:
        """
        Cancela una orden de compra
        """
        try:
            # 1. Verificar que la orden se pueda cancelar
            if not purchase_order.status == PurchaseOrder.PurchaseOrderStatus.PENDING:
                raise ValueError(f"La orden no se puede eliminar con estado: {purchase_order.status}")
            
            # 2. Actualizar estado de la orden
            purchase_order.status = 'CANCELLED'
            purchase_order.cancelled_at = timezone.now()
            purchase_order.save(update_fields=['status', 'cancelled_at'])
            
            # 3. Auditoría de éxito
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='PURCHASE_ORDER_CANCEL',
                    obj=purchase_order,
                    details={
                        'order_id': str(purchase_order.id),
                        'cancelled_by': user.id,
                        'cancelled_at': purchase_order.cancelled_at.isoformat(),
                        'operation': 'cancel_purchase_order'
                    },
                    status='SUCCESS'
                )

            return {
                'success': True,
                'order_status': purchase_order.status
            }
            
        except Exception as e:
            # Auditoría de error
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='PURCHASE_ORDER_CANCEL',
                    obj=purchase_order,
                    details={
                        'order_id': purchase_order.id,
                        'cancelled_by': user.id,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'operation': 'cancel_purchase_order'
                    },
                    status='ERROR'
                )
            raise