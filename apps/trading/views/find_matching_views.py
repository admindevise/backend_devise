from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from django.utils import timezone

from apps.trading.models import PurchaseOrder, SalesOrder, Transaction
from apps.trading.order_matching import OrderMatch

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_match(request):
    """
    Ejecuta un matching entre órdenes de compra y venta.
    
    Parámetros:
      - purchase_order_id: ID de la orden de compra (requerido)
      - sales_order_id: (opcional) ID específico de la orden de venta para match directo
      - Si no se especifica sales_order_id, se ejecuta match automático con la mejor coincidencia
    
    Permisos:
      - Propietarios de órdenes pueden ejecutar matches
      - Administradores pueden ejecutar cualquier match
    """
    user = request.user
    purchase_order_id = request.data.get('purchase_order_id')
    sales_order_id = request.data.get('sales_order_id')
    
    # Validar que se proporcione al menos purchase_order_id
    if not purchase_order_id:
        return Response({
            "detail": "purchase_order_id es requerido"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Obtener y validar orden de compra
        purchase_order = _get_order_with_permission_check(
            PurchaseOrder, purchase_order_id, user, 'created_by',
            "No tienes permiso para ejecutar match en esta orden de compra"
        )
        
        # Verificar que la orden esté en estado válido para matching
        if purchase_order.status not in ['PAID']:
            return Response({
                "detail": f"La orden de compra debe estar en estado PAID para ejecutar match, estado actual: {purchase_order.status}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Caso 1: Match específico con orden de venta proporcionada
        if sales_order_id:
            return _execute_specific_match(purchase_order, sales_order_id, user)
        
        # Caso 2: Match automático con la mejor coincidencia
        else:
            return _execute_automatic_match_for_user(purchase_order, user)
        
    except PermissionDenied as e:
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except ObjectNotFound as e:
        return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {"detail": f"Error al ejecutar matching: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _execute_specific_match(purchase_order, sales_order_id, user):
    """Ejecuta un match específico entre dos órdenes seleccionadas por el usuario"""
    try:
        # Obtener orden de venta
        sales_order = SalesOrder.objects.get(id=sales_order_id)
    except SalesOrder.DoesNotExist:
        raise ObjectNotFound("Orden de venta no encontrada")
    
    # Verificar que la orden de venta esté disponible
    if sales_order.status != 'PENDING':
        return Response({
            "detail": f"La orden de venta debe estar en estado PENDING, estado actual: {sales_order.status}"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar que las órdenes sean compatibles
    compatibility_check = _check_orders_compatibility(purchase_order, sales_order)
    if not compatibility_check['compatible']:
        return Response({
            "detail": f"Las órdenes no son compatibles: {compatibility_check['reason']}"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar que el usuario no se esté comprando/vendiendo a sí mismo
    if purchase_order.created_by == sales_order.created_by:
        return Response({
            "detail": "No puedes ejecutar match entre tus propias órdenes"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Ejecutar el match específico
    matcher = OrderMatch()
    result = matcher.execute_specific_match(purchase_order, sales_order)
    
    if result.get('success'):
        transaction_id = result.get('transaction_id')
        transaction = Transaction.objects.get(id=transaction_id)
        
        return Response({
            "status": "success",
            "message": f"Match específico ejecutado exitosamente por {user.username}",
            "match_type": "specific",
            "transaction": {
                "id": str(transaction.id),
                "purchase_order": purchase_order.order_number,
                "sales_order": sales_order.order_number,
                "buyer": purchase_order.created_by.username,
                "seller": sales_order.created_by.username,
                "units": transaction.units,
                "price_per_unit": float(transaction.price_per_unit),
                "total_amount": float(transaction.total_amount),
                "executed_by": user.username,
                "executed_at": timezone.now().isoformat()
            }
        })
    else:
        return Response({
            "status": "error",
            "message": result.get('error', 'Error desconocido al ejecutar match específico')
        }, status=status.HTTP_400_BAD_REQUEST)


def _execute_automatic_match_for_user(purchase_order, user):
    """Ejecuta match automático con la mejor coincidencia disponible"""
    matcher = OrderMatch()
    
    # Buscar coincidencias para esta orden
    matches = matcher.find_matches_for_order(purchase_order)
    
    if not matches:
        return Response({
            "detail": "No se encontraron coincidencias disponibles para esta orden de compra"
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Tomar la mejor coincidencia (primera en la lista)
    best_match = matches[0]
    sales_order = best_match['sales_order']
    
    # Verificar que el usuario no se esté comprando a sí mismo
    if purchase_order.created_by == sales_order.created_by:
        # Buscar la siguiente mejor opción
        available_matches = [m for m in matches if m['sales_order'].created_by != purchase_order.created_by]
        
        if not available_matches:
            return Response({
                "detail": "No hay coincidencias disponibles (no puedes comprar tus propias órdenes)"
            }, status=status.HTTP_404_NOT_FOUND)
        
        best_match = available_matches[0]
        sales_order = best_match['sales_order']
    
    # Ejecutar el match automático
    result = matcher.execute_specific_match(purchase_order, sales_order)
    
    if result.get('success'):
        transaction_id = result.get('transaction_id')
        transaction = Transaction.objects.get(id=transaction_id)
        
        return Response({
            "status": "success",
            "message": f"Match automático ejecutado exitosamente por {user.username}",
            "match_type": "automatic",
            "matched_with": {
                "sales_order_id": str(sales_order.id),
                "sales_order_number": sales_order.order_number,
                "seller": sales_order.created_by.username,
                "match_score": best_match.get('match_percentage', 0)
            },
            "transaction": {
                "id": str(transaction.id),
                "purchase_order": purchase_order.order_number,
                "sales_order": sales_order.order_number,
                "buyer": purchase_order.created_by.username,
                "seller": sales_order.created_by.username,
                "units": transaction.units,
                "price_per_unit": float(transaction.price_per_unit),
                "total_amount": float(transaction.total_amount),
                "executed_by": user.username,
                "executed_at": timezone.now().isoformat()
            }
        })
    else:
        return Response({
            "status": "error",
            "message": result.get('error', 'Error desconocido al ejecutar match automático')
        }, status=status.HTTP_400_BAD_REQUEST)


def _check_orders_compatibility(purchase_order, sales_order):
    """Verifica que dos órdenes sean compatibles para matching"""
    
    # 1. Mismo fondo
    if purchase_order.fund != sales_order.fund:
        return {
            'compatible': False,
            'reason': 'Las órdenes deben ser del mismo fondo'
        }
    
    # 2. Precios compatibles
    if purchase_order.price_per_unit < sales_order.price_per_unit:
        return {
            'compatible': False,
            'reason': f'Precio de compra ({purchase_order.price_per_unit}) menor que precio de venta ({sales_order.price_per_unit})'
        }
    
    # 3. Rangos de precios aceptables (si están definidos)
    if hasattr(purchase_order, 'min_acceptable_price') and purchase_order.min_acceptable_price:
        if sales_order.price_per_unit < purchase_order.min_acceptable_price:
            return {
                'compatible': False,
                'reason': f'Precio de venta ({sales_order.price_per_unit}) menor que mínimo aceptable ({purchase_order.min_acceptable_price})'
            }
    
    if hasattr(sales_order, 'max_acceptable_price') and sales_order.max_acceptable_price:
        if purchase_order.price_per_unit > sales_order.max_acceptable_price:
            return {
                'compatible': False,
                'reason': f'Precio de compra ({purchase_order.price_per_unit}) mayor que máximo aceptable ({sales_order.max_acceptable_price})'
            }
    
    # 4. Verificar que hay unidades disponibles
    if purchase_order.units <= 0 or sales_order.units <= 0:
        return {
            'compatible': False,
            'reason': 'Una de las órdenes no tiene unidades disponibles'
        }
    
    # 5. Verificar fechas de expiración
    from django.utils import timezone
    today = timezone.now().date()
    
    if purchase_order.expiration_date and purchase_order.expiration_date < today:
        return {
            'compatible': False,
            'reason': 'La orden de compra ha expirado'
        }
    
    if sales_order.expiration_date and sales_order.expiration_date < today:
        return {
            'compatible': False,
            'reason': 'La orden de venta ha expirado'
        }
    
    # Si pasa todas las validaciones
    return {
        'compatible': True,
        'reason': 'Órdenes compatibles'
    }


# --- Clases de excepción ---
class ObjectNotFoundException(Exception):
    pass

# --- Excepciones personalizadas ---
class PermissionDenied(Exception):
    pass

class ObjectNotFound(Exception):
    pass


# --- Funciones auxiliares ---
def _validate_order_parameters(purchase_order_id, sales_order_id):
    """Valida que se proporcione solo un tipo de ID de orden"""
    return bool(purchase_order_id) != bool(sales_order_id)  # XOR lógico


def _get_order(purchase_order_id, sales_order_id):
    """Obtiene la orden y determina su tipo"""
    if purchase_order_id:
        try:
            order = PurchaseOrder.objects.get(id=purchase_order_id)
            order_type = "purchase"
        except PurchaseOrder.DoesNotExist:
            raise ObjectNotFoundException("Orden de compra no encontrada")
    else:
        try:
            order = SalesOrder.objects.get(id=sales_order_id)
            order_type = "sales"
        except SalesOrder.DoesNotExist:
            raise ObjectNotFoundException("Orden de venta no encontrada")
            
    return order, order_type


def _get_order_with_permission_check(model_class, order_id, user, user_field, error_message):
    """Obtiene una orden y verifica permisos del usuario"""
    try:
        order = model_class.objects.get(id=order_id)
    except model_class.DoesNotExist:
        raise ObjectNotFound(f"Orden {'de compra' if model_class == PurchaseOrder else 'de venta'} no encontrada")
        
    # Verificar permisos (admins pueden acceder a cualquier orden)
    if not user.is_staff and getattr(order, user_field) != user:
        raise PermissionDenied(error_message)
        
    return order


def _execute_automatic_match(order, order_type):
    """Ejecuta el match automático para la orden especificada (función original para admins)"""
    matcher = OrderMatch()
    
    # Buscar coincidencias para esta orden
    matches = matcher.find_matches_for_order(order)
    
    if not matches:
        return Response({
            "detail": f"No se encontraron coincidencias para esta orden de {order_type}"
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Tomar la mejor coincidencia (primera en la lista)
    best_match = matches[0]
    
    # Obtener la orden complementaria según el tipo
    if order_type == "purchase":
        purchase_order = order
        sales_order = best_match['sales_order']
    else:
        sales_order = order
        purchase_order = best_match['purchase_order']
    
    # Ejecutar el match automáticamente
    result = matcher.execute_specific_match(purchase_order, sales_order)
    
    if result.get('success'):
        transaction_id = result.get('transaction_id')
        transaction = Transaction.objects.get(id=transaction_id)
        
        return Response({
            "status": "success",
            "message": "Match ejecutado automáticamente",
            "transaction": {
                "id": str(transaction.id),
                "purchase_order": purchase_order.order_number,
                "sales_order": sales_order.order_number,
                "units": transaction.units,
                "price_per_unit": float(transaction.price_per_unit),
                "total_amount": float(transaction.total_amount)
            }
        })
    else:
        return Response({
            "status": "error",
            "message": result.get('error', 'Error desconocido al ejecutar match')
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def find_matches(request):
    """
    Encuentra coincidencias entre órdenes de compra y venta.
    
    - Usuarios normales: deben especificar el ID de una orden propia para la cual buscar coincidencias
    - Administradores: pueden ejecutar matching general o especificar una orden específica
    
    Parámetros:
      - purchase_order_id: (opcional) ID de la orden de compra para buscar coincidencias
      - sales_order_id: (opcional) ID de la orden de venta para buscar coincidencias
    """
    user = request.user
    purchase_order_id = request.data.get('purchase_order_id')
    sales_order_id = request.data.get('sales_order_id')
    
    # Caso 1: Ninguna orden específica - Solo admins pueden hacer matching general
    if not (purchase_order_id or sales_order_id):
        if not user.is_staff:
            return Response({
                "detail": "Debes especificar purchase_order_id o sales_order_id para buscar coincidencias"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        return _process_general_matching(user)
    
    # Caso 2: Buscar matches para una orden específica
    try:
        # Determinar tipo de orden y obtener el objeto
        if purchase_order_id:
            order_type = "purchase"
            order = _get_order_with_permission_check(
                PurchaseOrder, purchase_order_id, user, 'supplier_user',
                "No tienes permiso para ver coincidencias de esta orden de compra"
            )
        else:  # sales_order_id
            order_type = "sales"
            order = _get_order_with_permission_check(
                SalesOrder, sales_order_id, user, 'seller_user',
                "No tienes permiso para ver coincidencias de esta orden de venta"
            )
            
        # Procesar coincidencias para la orden
        return _process_order_matches(order, order_type)
        
    except PermissionDenied as e:
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except ObjectNotFound as e:
        return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {"detail": f"Error al procesar coincidencias: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# --- Funciones auxiliares ---
def _process_order_matches(order, order_type):
    """Procesa las coincidencias para una orden específica"""
    matcher = OrderMatch()
    matches = matcher.find_matches_for_order(order)
    
    # Formatear resultados según tipo de orden
    if order_type == "purchase":
        formatted_matches = _format_purchase_order_matches(matches)
        order_id = str(order.id)
    else:  # sales
        formatted_matches = _format_sales_order_matches(matches)
        order_id = str(order.id)
    
    return Response({
        "order_id": order_id,
        "order_type": order_type,
        "matches_found": len(formatted_matches),
        "matches": formatted_matches
    })


def _format_purchase_order_matches(matches):
    """Formatea resultados de coincidencias para órdenes de compra"""
    formatted = []
    for match in matches:
        sales_order = match['sales_order']
        formatted.append({
            "sales_order_id": str(sales_order.id),
            "order_number": sales_order.order_number,
            "seller": sales_order.seller_user.username,
            "price_per_unit": float(match['match_price']),
            "matched_units": match['matched_units'],
            "total_amount": float(match['total_amount']),
            "fund": sales_order.fund.name
        })
    return formatted


def _format_sales_order_matches(matches):
    """Formatea resultados de coincidencias para órdenes de venta"""
    formatted = []
    for match in matches:
        purchase_order = match['purchase_order']
        formatted.append({
            "purchase_order_id": str(purchase_order.id),
            "order_number": purchase_order.order_number,
            "buyer": purchase_order.supplier_user.username,
            "price_per_unit": float(match['match_price']),
            "matched_units": match['matched_units'],
            "total_amount": float(match['total_amount']),
            "fund": purchase_order.fund.name
        })
    return formatted


def _process_general_matching(user):
    """Procesa matching general (solo para administradores)"""
    matcher = OrderMatch()
    results = matcher.run_matching_cycle()
    successful_matches = [r for r in results if r.get('success', False)]
    failed_matches = [r for r in results if not r.get('success', False)]
    
    return Response({
        "total_matches_processed": len(results),
        "successful_matches": len(successful_matches),
        "failed_matches": len(failed_matches),
        "details": {
            "successful": successful_matches,
            "failed": failed_matches
        }
    })