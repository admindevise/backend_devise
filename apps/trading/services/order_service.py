from django.db import transaction
from django.utils import timezone
from apps.trading.security.token_validators import TradingAvailabilityService, TokenReservationManager
from apps.audit.audit_service import AuditService
from apps.trading.models import PurchaseOrder, SalesOrder, Transaction
from apps.fund.models import FundToken
from apps.kaleido.utils import safe_transfer_721
from decimal import Decimal
import logging
import random
import time

logger = logging.getLogger('trading.services')

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
        
        try:
            # 1. Validar viabilidad completa de la orden
            feasibility = self.availability_service.validate_sales_order_feasibility(
                user, fund.id, quantity=quantity
            )
            
            if not feasibility['feasible']:
                raise ValueError(f"Orden no viable: {'; '.join(feasibility['errors'])}")
            
            # 2. Obtener tokens seleccionados automáticamente
            selected_tokens = feasibility['validations']['auto_select']['token_ids']
            
            # 3. Reservar tokens para la venta
            reservation_result = self.reservation_manager.reserve_tokens_for_sale(
                user, selected_tokens, fund.id
            )
            
            if not reservation_result['success']:
                raise ValueError(f"Error reservando tokens: {reservation_result['failed_reservations']}")
            
            # 4. Crear la orden
            sales_order = SalesOrder.objects.create(
                **order_data,
                created_by=user,
                status='PENDING'
            )
            
            print(f"Sales order created with ID: {sales_order.id}")
            
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
            
            logger.info(f"Sales order {sales_order.id} created successfully for user {user.id}")
            
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
            
            logger.error(f"Error creating sales order for user {user.id}: {str(e)}")
            raise
    
    @transaction.atomic
    def create_purchase_order(self, user, order_data: dict, request=None) -> dict:
        """
        Crea una orden de compra con validaciones de liquidez
        """
        fund = order_data['fund']
        quantity = order_data['units']
        
        try:
            # 1. Validar viabilidad de la orden de compra
            feasibility = self.availability_service.validate_purchase_order_feasibility(
                user, fund.id, quantity
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
                                # Serializar FundApplication object
                                app = val_value['application']
                                validations_serialized[val_key] = {
                                    'valid': val_value['valid'],
                                    'is_staff': val_value.get('is_staff', False),
                                    'application_id': app.id if app else None,
                                    'application_status': app.status if app else None,
                                    'fund_id': app.fund.id if app else None
                                }
                            else:
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
            
            logger.info(f"Purchase order {purchase_order.id} created successfully for user {user.id}")
            
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
            
            logger.error(f"Error creating purchase order for user {user.id}: {str(e)}")
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
                    logger.warning(f"Some tokens could not be released: {release_result['errors']}")
            
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
            
            logger.info(f"Sales order {sales_order.id} cancelled successfully")
            
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
            
            logger.error(f"Error cancelling sales order {sales_order.id}: {str(e)}")
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
            
            logger.info(f"Purchase order {purchase_order.id} cancelled successfully")
            
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
            
            logger.error(f"Error cancelling purchase order {purchase_order.id}: {str(e)}")
            raise

class TransactionExecutionService:
    """
    Servicio para ejecutar transacciones completas entre órdenes
    """
    
    def __init__(self):
        self.reservation_manager = TokenReservationManager()
    
    @transaction.atomic
    def execute_trade(self, purchase_order, sales_order, units_to_trade: int, request=None) -> dict:
        """
        Ejecuta una transacción completa entre una orden de compra y venta
        """
        try:
            # 1. Validaciones previas
            if purchase_order.status != 'PAID':
                raise ValueError(f"Purchase order must be PAID, current status: {purchase_order.status}")
            
            if sales_order.status not in ['APPROVED', 'PAID']:
                raise ValueError(f"Sales order must be APPROVED or PAID, current status: {sales_order.status}")
            
            if units_to_trade > min(purchase_order.units, sales_order.units):
                raise ValueError("Units to trade exceed available units in orders")
            
            # 2. Obtener tokens de ambas órdenes
            purchase_tokens = self._get_reserved_tokens_from_order(purchase_order)[:units_to_trade]
            sales_tokens = self._get_reserved_tokens_from_order(sales_order)[:units_to_trade]
            
            if len(purchase_tokens) != units_to_trade or len(sales_tokens) != units_to_trade:
                raise ValueError("Insufficient reserved tokens for trade execution")
            
            # 3. Ejecutar transferencias en blockchain
            transfer_results = []
            for purchase_token, sales_token in zip(purchase_tokens, sales_tokens):
                # Transferir token del vendedor al comprador
                transfer_result, transfer_error = safe_transfer_721(
                    sales_token.token_id,
                    sales_order.fund.id,
                    sales_order.created_by,  # from_user
                    purchase_order.created_by  # to_user
                )
                
                if transfer_error:
                    raise ValueError(f"Transfer failed for token {sales_token.token_id}: {transfer_error}")
                
                transfer_results.append({
                    'token_id': sales_token.token_id,
                    'transfer_result': transfer_result
                })
            
            # 4. Actualizar propiedad en base de datos
            for sales_token in sales_tokens:
                sales_token.owner_user = purchase_order.created_by
                sales_token.save(update_fields=['owner_user'])
            
            # 5. Crear registro de transacción
            trade_transaction = Transaction.objects.create(
                purchase_order=purchase_order,
                sales_order=sales_order,
                buyer=purchase_order.created_by,
                seller=sales_order.created_by,
                fund=purchase_order.fund,
                units=units_to_trade,
                price_per_unit=purchase_order.price_per_unit,
                total_amount=units_to_trade * purchase_order.price_per_unit
            )
            
            # 6. Actualizar estados de órdenes
            if purchase_order.units == units_to_trade:
                purchase_order.status = 'COMPLETED'
                purchase_order.completed_at = timezone.now()
                purchase_order.save(update_fields=['status', 'completed_at'])
            
            if sales_order.units == units_to_trade:
                sales_order.status = 'COMPLETED'
                sales_order.completed_at = timezone.now()
                sales_order.save(update_fields=['status', 'completed_at'])
            
            # 7. Auditoría de éxito
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='TRADE_EXECUTION',
                    obj=trade_transaction,
                    details={
                        'purchase_order_id': purchase_order.id,
                        'sales_order_id': sales_order.id,
                        'units_to_trade': units_to_trade,
                        'buyer_id': purchase_order.created_by.id,
                        'seller_id': sales_order.created_by.id,
                        'transaction_id': trade_transaction.id,
                        'transferred_tokens': [r['token_id'] for r in transfer_results],
                        'units_traded': units_to_trade,
                        'total_amount': trade_transaction.total_amount,
                        'operation': 'execute_trade'
                    },
                    status='SUCCESS'
                )
            
            logger.info(f"Trade executed successfully: Transaction {trade_transaction.id}")
            
            return {
                'success': True,
                'transaction': trade_transaction,
                'transferred_tokens': transfer_results,
                'purchase_order_status': purchase_order.status,
                'sales_order_status': sales_order.status
            }
            
        except Exception as e:
            # Auditoría de error
            if request:
                AuditService.log_action(
                    request=request,
                    action_code='TRADE_EXECUTION_ERROR',
                    obj=None,
                    details={
                        'purchase_order_id': purchase_order.id,
                        'sales_order_id': sales_order.id,
                        'units_to_trade': units_to_trade,
                        'buyer_id': purchase_order.created_by.id,
                        'seller_id': sales_order.created_by.id,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'operation': 'execute_trade'
                    },
                    status='ERROR'
                )
            
            logger.error(f"Error executing trade: {str(e)}")
            raise
    
    def _get_reserved_tokens_from_order(self, order) -> list:
        """
        Obtiene los tokens reservados de una orden desde sus metadatos
        """
        if not hasattr(order, 'metadata') or not order.metadata:
            return []
        
        reserved_token_ids = order.metadata.get('reserved_tokens', [])
        
        return list(FundToken.objects.filter(
            token_id__in=reserved_token_ids,
            fund=order.fund
        ).order_by('created_at'))