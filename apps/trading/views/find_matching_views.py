from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes

from apps.trading.models import PurchaseOrder, SalesOrder, Transaction
from apps.trading.order_matching import OrderMatch

# DEPRECADO: execute_match ya no se usa en el nuevo flujo
# El proceso ahora es: find_matches -> select_matches -> pay_selection
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_match(request):
    """
    DEPRECADO: Esta función ha sido reemplazada por el flujo pay_selection
    
    El nuevo flujo es:
    1. find_matches - para buscar coincidencias
    2. select_matches - para seleccionar matches específicos  
    3. pay_selection - para pagar y ejecutar automáticamente
    
    Esta función se mantiene solo para compatibilidad con código legacy
    """
    return Response({
        "error": "Esta función está deprecada",
        "message": "Usa el nuevo flujo: find_matches -> select_matches -> pay_selection",
        "deprecated": True,
        "new_endpoints": {
            "find_matches": "/api/trading/find-matches/",
            "select_matches": "/api/trading/select-matches/", 
            "pay_selection": "/api/trading/pay-selection/"
        }
    }, status=status.HTTP_410_GONE)


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
        
    # Verificar permisos (admins pueden acceder a cualquier orden)
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
    
    # NUEVO: Agregar información del siguiente paso en el flujo
    next_step_info = None
    if order_type == "purchase" and formatted_matches:
        next_step_info = {
            "action": "select_matches",
            "endpoint": "/api/trading/select-matches/",
            "description": "Selecciona qué matches quieres ejecutar",
            "required_data": {
                "purchase_order_id": order_id,
                "selected_matches": "array de objetos con sales_order_id y units"
            }
        }
    elif order_type == "sales" and formatted_matches:
        next_step_info = {
            "action": "wait_for_buyer",
            "description": "Espera a que un comprador seleccione tu orden",
            "note": "Las órdenes de venta no pueden iniciar el proceso de matching"
        }
    
    return Response({
        "order_id": order_id,
        "order_type": order_type,
        "matches_found": len(formatted_matches),
        "matches": formatted_matches,
        "next_step": next_step_info,
        "workflow_info": {
            "current_step": "find_matches",
            "next_steps": ["select_matches", "pay_selection"] if order_type == "purchase" else ["wait_for_buyer"],
            "flow": "find_matches -> select_matches -> pay_selection"
        }
    })


def _format_purchase_order_matches(matches):
    """Formatea resultados de coincidencias para órdenes de compra"""
    formatted = []
    for i, match in enumerate(matches):
        sales_order = match['sales_order']
        formatted.append({
            "match_index": i,  # NUEVO: Agregar índice para facilitar selección
            "sales_order_id": str(sales_order.id),
            "order_number": sales_order.order_number,
            "seller": sales_order.seller_user.username,
            "price_per_unit": float(match['match_price']),
            "matched_units": match['matched_units'],
            "available_units": sales_order.available_units,  # NUEVO: Mostrar unidades disponibles
            "total_amount": float(match['total_amount']),
            "fund": sales_order.fund.name,
            "match_percentage": match.get('match_percentage', 0),  # NUEVO: Porcentaje de match
            "is_partial": match.get('is_partial', False),  # NUEVO: Si es match parcial
            "expiration_date": sales_order.expiration_date.isoformat() if sales_order.expiration_date else None
        })
    return formatted


def _format_sales_order_matches(matches):
    """Formatea resultados de coincidencias para órdenes de venta"""
    formatted = []
    for i, match in enumerate(matches):
        purchase_order = match['purchase_order']
        formatted.append({
            "match_index": i,  # NUEVO: Agregar índice
            "purchase_order_id": str(purchase_order.id),
            "order_number": purchase_order.order_number,
            "buyer": purchase_order.supplier_user.username,
            "price_per_unit": float(match['match_price']),
            "matched_units": match['matched_units'],
            "available_units": purchase_order.available_units,  # NUEVO: Mostrar unidades disponibles
            "total_amount": float(match['total_amount']),
            "fund": purchase_order.fund.name,
            "match_percentage": match.get('match_percentage', 0),  # NUEVO: Porcentaje de match
            "is_partial": match.get('is_partial', False),  # NUEVO: Si es match parcial
            "expiration_date": purchase_order.expiration_date.isoformat() if purchase_order.expiration_date else None
        })
    return formatted


def _process_general_matching(user):
    """Procesa matching general (solo para administradores)"""
    matcher = OrderMatch()
    
    # ACTUALIZADO: Solo mostrar matches disponibles, no ejecutarlos automáticamente
    matches = matcher.find_matches()
    
    if not matches:
        return Response({
            "message": "No se encontraron matches disponibles en el sistema",
            "total_matches": 0,
            "matches": []
        })
    
    # Formatear matches para admin
    formatted_matches = []
    for match in matches:
        purchase_order = match['purchase_order']
        sales_order = match['sales_order']
        
        formatted_matches.append({
            "purchase_order": {
                "id": str(purchase_order.id),
                "order_number": purchase_order.order_number,
                "buyer": purchase_order.supplier_user.username,
                "available_units": purchase_order.available_units
            },
            "sales_order": {
                "id": str(sales_order.id),
                "order_number": sales_order.order_number,
                "seller": sales_order.seller_user.username,
                "available_units": sales_order.available_units
            },
            "match_details": {
                "matched_units": match['matched_units'],
                "price_per_unit": float(match['match_price']),
                "total_amount": float(match['total_amount']),
                "fund": purchase_order.fund.name,
                "compatibility_score": match.get('match_percentage', 0)
            }
        })
    
    return Response({
        "total_matches_found": len(formatted_matches),
        "matches": formatted_matches,
        "admin_note": "Como administrador, puedes ver todos los matches. Los usuarios deben usar select_matches y pay_selection para ejecutar transacciones.",
        "workflow_info": {
            "user_flow": "find_matches -> select_matches -> pay_selection",
            "admin_capabilities": "Puede ver todos los matches pero no ejecutarlos directamente"
        }
    })