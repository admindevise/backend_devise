from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.db import transaction
from datetime import datetime
import logging

from apps.trading.models import PurchaseOrder, SalesOrder
from apps.trading.service.order_service import PaymentProcessingService

logger = logging.getLogger('trading.payment')

def _execute_individual_match(purchase_order, match_selection, user):
    """
    Ejecuta un match individual entre una orden de compra y una orden de venta
    """
    try:
        from apps.trading.models import Transaction
        
        # 1. Obtener la orden de venta
        sales_order_id = match_selection.get('sales_order_id')
        units_to_trade = match_selection.get('units')
        
        logger.info(f"=== INDIVIDUAL MATCH DEBUG ===")
        logger.info(f"Purchase order: {purchase_order.id} - Status: {purchase_order.status}")
        logger.info(f"Sales order ID: {sales_order_id}, Units to trade: {units_to_trade}")
        
        try:
            sales_order = SalesOrder.objects.get(id=sales_order_id, status='PENDING')
            logger.info(f"Sales order found: {sales_order.order_number} - Available units: {sales_order.available_units}")
        except SalesOrder.DoesNotExist:
            error_msg = f'Orden de venta {sales_order_id} no encontrada o no está disponible'
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        # 2. Verificar que la orden de venta siga teniendo unidades disponibles
        if (sales_order.available_units or 0) < units_to_trade:
            error_msg = f'La orden de venta solo tiene {sales_order.available_units} unidades disponibles, pero se solicitaron {units_to_trade}'
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        # 3. NUEVO: Ejecutar match decrementando available_units pero preservando units
        logger.info("Executing match - updating available_units while preserving original units")
        
        with transaction.atomic():
            # Decrementar unidades disponibles (no las originales)
            sales_order.available_units = (sales_order.available_units or sales_order.units) - units_to_trade
            purchase_order.available_units = (purchase_order.available_units or purchase_order.units) - units_to_trade
            
            # Si las unidades disponibles llegan a cero, marcar como COMPLETED
            if sales_order.available_units <= 0:
                sales_order.status = 'COMPLETED'
                sales_order.completed_at = timezone.now()
                sales_order.save(update_fields=['available_units', 'status', 'completed_at'])
            else:
                # Orden parcialmente ejecutada, mantener PENDING
                sales_order.save(update_fields=['available_units'])
            
            if purchase_order.available_units <= 0:
                purchase_order.status = 'COMPLETED'
                purchase_order.completed_at = timezone.now()
                purchase_order.save(update_fields=['available_units', 'status', 'completed_at'])
            else:
                purchase_order.save(update_fields=['available_units'])
            
            logger.info(f"Sales order updated - Original units: {sales_order.units}, Available: {sales_order.available_units}, Status: {sales_order.status}")
            logger.info(f"Purchase order updated - Original units: {purchase_order.units}, Available: {purchase_order.available_units}, Status: {purchase_order.status}")
            
            # Crear transacción con las unidades realmente operadas
            transaction_record = Transaction.objects.create(
                purchase_order=purchase_order,
                sales_order=sales_order,
                buyer=purchase_order.supplier_user,
                seller=sales_order.seller_user,
                fund=purchase_order.fund,
                units=units_to_trade,
                price_per_unit=sales_order.price_per_unit,
                total_amount=units_to_trade * sales_order.price_per_unit,
            )
            logger.info(f"Transaction created: {transaction_record.id} for {units_to_trade} units")
        
        # 4. Preparar datos de la transacción
        transaction_data = {
            'transaction_id': str(transaction_record.id),
            'purchase_order_id': str(purchase_order.id),
            'sales_order_id': str(sales_order.id),
            'purchase_order_number': purchase_order.order_number,
            'sales_order_number': sales_order.order_number,
            'buyer': purchase_order.supplier_user.email,
            'seller': sales_order.seller_user.email,
            'units_traded': units_to_trade,
            'original_purchase_units': purchase_order.units,  # Dato histórico
            'original_sales_units': sales_order.units,        # Dato histórico
            'remaining_purchase_units': purchase_order.available_units,  # Unidades restantes
            'remaining_sales_units': sales_order.available_units,        # Unidades restantes
            'price_per_unit': float(sales_order.price_per_unit),
            'subtotal': float(units_to_trade * sales_order.price_per_unit),
            'fund': sales_order.fund.name,
            'executed_at': timezone.now().isoformat(),
            'executed_by': user.email
        }
        
        logger.info(f"Individual match executed successfully: {transaction_data}")
        logger.info("=== INDIVIDUAL MATCH SUCCESS ===")
        
        return {
            'success': True,
            'transaction_data': transaction_data,
            'units': units_to_trade,
            'message': f'Match ejecutado exitosamente: {units_to_trade} unidades operadas'
        }
        
    except Exception as e:
        logger.error(f"Exception in _execute_individual_match: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e)
        }

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_selection(request):
    """
    Paga la selección específica de matches y ejecuta todas las transacciones automáticamente
    
    Parámetros:
      - purchase_order_id: ID de la orden de compra (requerido)
      - payment_method: Método de pago (opcional, se genera automático)
      - reference: Referencia de pago (opcional, se genera automático)
      - metadata: Metadatos adicionales (opcional)
    
    NOTA: El monto se extrae automáticamente de la selección previa
    """
    user = request.user
    purchase_order_id = request.data.get('purchase_order_id')
    
    try:
        # 1. Validaciones básicas
        if not purchase_order_id:
            return Response({
                'error': 'purchase_order_id es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Obtener y validar orden de compra
        try:
            purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        except PurchaseOrder.DoesNotExist:
            return Response({
                'error': 'Orden de compra no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 3. Verificar permisos
        if not user.is_staff and purchase_order.created_by != user:
            return Response({
                'error': 'No tienes permisos para pagar esta orden'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 4. Verificar estado
        if purchase_order.status != 'MATCHES_SELECTED':
            return Response({
                'error': f'La orden debe estar en estado MATCHES_SELECTED. Estado actual: {purchase_order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 5. Verificar que la selección no haya expirado
        expires_at_str = purchase_order.metadata.get('selection_summary', {}).get('expires_at')
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if timezone.now() > expires_at:
                # Revertir estado
                purchase_order.status = 'PENDING'
                purchase_order.save()
                return Response({
                    'error': 'La selección de matches ha expirado. Debes seleccionar nuevamente.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # 6. MODIFICADO: Extraer monto automáticamente de la selección
        try:
            expected_amount = purchase_order.metadata['selection_summary']['total_amount']
        except KeyError:
            return Response({
                'error': 'No se encontró información de monto en la selección. Debes seleccionar matches primero.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 7. MODIFICADO: Construir datos de pago automáticamente
        payment_data = {
            'amount': expected_amount,  # Usar el monto de la selección
            'method': request.data.get('payment_method', 'automatic'),
            'reference': request.data.get('reference', f'PAY-{purchase_order.order_number}'),
            'metadata': request.data.get('metadata', {})
        }
        
        # Agregar información adicional a metadata
        payment_data['metadata'].update({
            'auto_extracted_amount': True,
            'selection_summary': purchase_order.metadata.get('selection_summary', {}),
            'payment_date': timezone.now().isoformat()
        })
        
        # 8. Procesar pago y ejecutar transacciones
        with transaction.atomic():
            # Cambiar estado a MATCHED (necesario para el servicio de pago)
            purchase_order.status = 'MATCHED'
            purchase_order.matched_at = timezone.now()
            purchase_order.save()
            
            # Procesar pago
            payment_service = PaymentProcessingService()
            payment_result = payment_service.process_purchase_order_payment(
                purchase_order, payment_data, request
            )
            
            # Ejecutar todas las transacciones seleccionadas
            executed_transactions = []
            total_executed_units = 0
            
            for match_selection in purchase_order.metadata['selected_matches']:
                try:
                    # Ejecutar cada match individual
                    execution_result = _execute_individual_match(
                        purchase_order, 
                        match_selection,
                        user
                    )
                    
                    if execution_result['success']:
                        executed_transactions.append(execution_result['transaction_data'])
                        total_executed_units += execution_result['units']
                    else:
                        logger.error(f"Failed to execute match: {execution_result['error']}")
                        
                except Exception as e:
                    logger.error(f"Error executing match for selection {match_selection}: {str(e)}")
                    continue
            
            # Actualizar estado final
            if total_executed_units > 0:
                purchase_order.status = 'COMPLETED'
                purchase_order.completed_at = timezone.now()
                purchase_order.units -= total_executed_units
                purchase_order.save()
        
        return Response({
            'success': True,
            'message': f'Pago procesado automáticamente y {len(executed_transactions)} transacciones ejecutadas exitosamente',
            'payment_details': {
                'method': payment_result['payment_method'],
                'reference': payment_result['payment_reference'],
                'amount_paid': float(expected_amount),  # Mostrar el monto extraído
                'currency': 'COP',
                'processed_at': payment_result['payment_processed_at'].isoformat(),
                'auto_extracted': True  # Indicar que fue extraído automáticamente
            },
            'execution_summary': {
                'total_transactions': len(executed_transactions),
                'total_units_acquired': total_executed_units,
                'total_amount_spent': sum(t['subtotal'] for t in executed_transactions),
                'matches_executed': len([t for t in executed_transactions if t])
            },
            'transactions': executed_transactions,
            'final_order_status': purchase_order.status,
            'selection_details': {
                'original_amount': float(expected_amount),
                'matches_count': len(purchase_order.metadata.get('selected_matches', [])),
                'savings': purchase_order.metadata.get('selection_summary', {}).get('savings', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in pay_selection: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)