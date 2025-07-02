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
from apps.trading.order_matching import OrderMatch

logger = logging.getLogger('trading.payment')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_selection(request):
    """
    Paga la selección específica de matches y ejecuta todas las transacciones automáticamente
    
    Parámetros:
      - purchase_order_id: ID de la orden de compra (requerido)
      - amount: Monto exacto a pagar (requerido)
      - payment_method: Método de pago (opcional, se genera automático)
      - reference: Referencia de pago (opcional, se genera automático)
      - metadata: Metadatos adicionales (opcional)
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
        
        # 6. Validar datos de pago
        payment_data = {
            'amount': request.data.get('amount'),
            'method': request.data.get('payment_method'),
            'reference': request.data.get('reference', ''),
            'metadata': request.data.get('metadata', {})
        }
        
        if not payment_data['amount']:
            return Response({
                'error': 'Amount es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 7. Verificar monto contra selección
        expected_amount = purchase_order.metadata['selection_summary']['total_amount']
        if abs(float(payment_data['amount']) - expected_amount) > 0.01:
            return Response({
                'error': f'Monto incorrecto. Esperado: {expected_amount}, Recibido: {payment_data["amount"]}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
            'message': f'Pago procesado y {len(executed_transactions)} transacciones ejecutadas exitosamente',
            'payment_details': {
                'method': payment_result['payment_method'],
                'reference': payment_result['payment_reference'],
                'amount_paid': float(payment_data['amount']),
                'currency': 'COP',
                'processed_at': payment_result['payment_processed_at'].isoformat()
            },
            'execution_summary': {
                'total_transactions': len(executed_transactions),
                'total_units_acquired': total_executed_units,
                'total_amount_spent': sum(t['subtotal'] for t in executed_transactions)
            },
            'transactions': executed_transactions,
            'final_order_status': purchase_order.status
        })
        
    except Exception as e:
        logger.error(f"Error in pay_selection: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


def _execute_individual_match(purchase_order, match_selection, user):
    """Ejecuta un match individual usando el sistema existente"""
    try:
        sales_order_id = match_selection['sales_order_id']
        units_requested = match_selection['units']
        
        # Obtener orden de venta
        sales_order = SalesOrder.objects.get(id=sales_order_id, status='PENDING')
        
        # Usar OrderMatch para ejecutar
        matcher = OrderMatch()
        result = matcher.execute_specific_match(
            purchase_order, 
            sales_order, 
            units=units_requested
        )
        
        if result.get('success'):
            return {
                'success': True,
                'transaction_data': {
                    'transaction_id': str(result['transaction_id']),
                    'sales_order': sales_order.order_number,
                    'seller': sales_order.seller_user.username,
                    'units': result['units'],
                    'price_per_unit': float(result['price']),
                    'subtotal': float(result['total'])
                },
                'units': result['units']
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Unknown error')
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }