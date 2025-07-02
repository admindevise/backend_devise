from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.db import transaction

from apps.trading.models import PurchaseOrder, SalesOrder
from apps.trading.order_matching import OrderMatch

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_matches(request):
    """
    Permite al usuario seleccionar matches específicos de la lista obtenida de find_matches
    
    Parámetros:
      - purchase_order_id: ID de la orden de compra (requerido)
      - selected_matches: Lista de matches seleccionados con formato:
        [
            {"sales_order_id": "uuid", "units": 5},
            {"match_index": 1, "units": 4}  // También acepta índice
        ]
    """
    user = request.user
    purchase_order_id = request.data.get('purchase_order_id')
    selected_matches = request.data.get('selected_matches', [])
    
    try:
        # 1. Validaciones básicas
        if not purchase_order_id:
            return Response({
                'error': 'purchase_order_id es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not selected_matches:
            return Response({
                'error': 'selected_matches es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Obtener y validar orden de compra
        try:
            purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        except PurchaseOrder.DoesNotExist:
            return Response({
                'error': 'Orden de compra no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 3. Verificar permisos
        if purchase_order.supplier_user != user:
            return Response({
                'error': 'No tienes permisos para seleccionar matches de esta orden'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 4. Verificar estado de la orden
        if purchase_order.status != 'PENDING':
            return Response({
                'error': f'La orden debe estar PENDING para seleccionar matches. Estado actual: {purchase_order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 5. Procesar selecciones
        validated_selections = []
        total_selected_units = 0
        total_amount = 0
        
        # Obtener matches disponibles para validar selecciones
        matcher = OrderMatch()
        available_matches = matcher.find_matches_for_order(purchase_order)
        
        for selection in selected_matches:
            # Resolver orden de venta (por ID o índice)
            sales_order = _resolve_sales_order(selection, available_matches, purchase_order)
            
            # Validar unidades solicitadas
            requested_units = selection.get('units')
            if not requested_units:
                requested_units = min(sales_order.units, purchase_order.units - total_selected_units)
            
            max_available = min(sales_order.units, purchase_order.units - total_selected_units)
            
            if requested_units > max_available:
                return Response({
                    'error': f'Unidades solicitadas ({requested_units}) exceden disponibles ({max_available}) para orden {sales_order.order_number}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calcular costo
            unit_cost = requested_units * sales_order.price_per_unit
            total_selected_units += requested_units
            total_amount += unit_cost
            
            validated_selections.append({
                'sales_order_id': str(sales_order.id),
                'sales_order_number': sales_order.order_number,
                'seller_username': sales_order.seller_user.username,
                'units': requested_units,
                'price_per_unit': float(sales_order.price_per_unit),
                'subtotal': float(unit_cost)
            })
            
            # Evitar exceder las unidades que quiere comprar
            if total_selected_units >= purchase_order.units:
                break
        
        # 6. Verificar que no exceda el presupuesto
        if total_amount > purchase_order.total_amount:
            return Response({
                'error': f'Total seleccionado ({total_amount}) excede presupuesto máximo ({purchase_order.total_amount})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 7. Guardar selección y cambiar estado
        with transaction.atomic():
            purchase_order.status = 'MATCHES_SELECTED'
            purchase_order.metadata = purchase_order.metadata or {}
            purchase_order.metadata.update({
                'selected_matches': validated_selections,
                'selection_summary': {
                    'total_units': total_selected_units,
                    'total_amount': float(total_amount),
                    'savings': float(purchase_order.total_amount - total_amount),
                    'selected_at': timezone.now().isoformat(),
                    'expires_at': (timezone.now() + timezone.timedelta(minutes=15)).isoformat()
                }
            })
            purchase_order.save()
        
        return Response({
            'success': True,
            'message': 'Matches seleccionados exitosamente',
            'selection_summary': {
                'total_units_selected': total_selected_units,
                'total_amount_to_pay': float(total_amount),
                'savings_vs_budget': float(purchase_order.total_amount - total_amount),
                'payment_deadline': purchase_order.metadata['selection_summary']['expires_at']
            },
            'selected_matches': validated_selections,
            'next_step': {
                'action': 'Proceder al pago',
                'endpoint': f'/trading/pay-selection/',
                'purchase_order_id': str(purchase_order.id),
                'amount_to_pay': float(total_amount)
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


def _resolve_sales_order(selection, available_matches, purchase_order):
    """Resuelve la orden de venta desde selección por ID o índice"""
    sales_order_id = selection.get('sales_order_id')
    match_index = selection.get('match_index')
    
    if not sales_order_id and match_index is None:
        raise ValueError('Cada selección debe tener sales_order_id o match_index')
    
    # Resolver por índice
    if match_index is not None:
        try:
            match = available_matches[match_index]
            return match['sales_order']
        except IndexError:
            raise ValueError(f'Índice de match inválido: {match_index}')
    
    # Resolver por ID
    try:
        sales_order = SalesOrder.objects.get(id=sales_order_id, status='PENDING')
        return sales_order
    except SalesOrder.DoesNotExist:
        raise ValueError(f'Orden de venta no encontrada o no disponible: {sales_order_id}')