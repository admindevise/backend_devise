from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q

from apps.trading.models import PurchaseOrder, SalesOrder
from apps.trading.order_matching import OrderMatch

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_match(request):
    """
    Ejecuta automáticamente un matching entre una orden y sus posibles coincidencias.
    
    - Inicialmente solo usuarios staff: requiere order_id
    - En el futuro, usuarios normales: los datos se tomarán automáticamente
    
    Parámetros:
      - purchase_order_id: ID de la orden de compra
      - sales_order_id: ID de la orden de venta
    """
    user = request.user
    purchase_order_id = request.data.get('purchase_order_id')
    sales_order_id = request.data.get('sales_order_id')
    
    # Verificar permisos
    if not user.is_staff:
        return Response({
            "detail": "Solo administradores pueden ejecutar matching automático"
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Validar parámetros
    if not _validate_order_parameters(purchase_order_id, sales_order_id):
        return Response({
            "detail": "Se debe proporcionar exactamente un ID de orden: purchase_order_id O sales_order_id"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Determinar tipo de orden y obtener el objeto
        order, order_type = _get_order(purchase_order_id, sales_order_id)
        
        # Procesar matching automático
        return _execute_automatic_match(order, order_type)
        
    except ObjectNotFoundException as e:
        return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {"detail": f"Error al ejecutar matching automático: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# --- Clases de excepción ---
class ObjectNotFoundException(Exception):
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


def _execute_automatic_match(order, order_type):
    """Ejecuta el match automático para la orden especificada"""
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


# --- Excepciones personalizadas ---
class PermissionDenied(Exception):
    pass

class ObjectNotFound(Exception):
    pass


# --- Funciones auxiliares ---
def _get_order_with_permission_check(model_class, order_id, user, user_field, error_message):
    """Obtiene una orden y verifica permisos del usuario"""
    try:
        order = model_class.objects.get(id=order_id)
    except model_class.DoesNotExist:
        raise ObjectNotFound(f"Orden {'de compra' if model_class == PurchaseOrder else 'de venta'} no encontrada")
        
    # Verificar permisos
    if not user.is_staff and getattr(order, user_field) != user:
        raise PermissionDenied(error_message)
        
    return order


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