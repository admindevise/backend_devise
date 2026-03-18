from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from apps.trading.order_matching import OrderMatch


class FindMatchesPermissionDenied(Exception):
    pass


class FindMatchesObjectNotFound(Exception):
    pass


class FindMatchesBadRequest(Exception):
    pass


class FindMatchesService:
    def execute(self, user, purchase_order_id=None, sales_order_id=None) -> dict:
        # Caso 1: matching general
        if not (purchase_order_id or sales_order_id):
            if not user.is_staff:
                raise FindMatchesBadRequest(
                    "Debes especificar purchase_order_id o sales_order_id para buscar coincidencias"
                )
            return self._process_general_matching()

        # Caso 2: matching por orden
        if purchase_order_id:
            order_type = "purchase"
            order = self._get_order_with_permission_check(
                PurchaseOrder, purchase_order_id, user, "supplier_user",
                "No tienes permiso para ver coincidencias de esta orden de compra"
            )
        else:
            order_type = "sales"
            order = self._get_order_with_permission_check(
                SalesOrder, sales_order_id, user, "seller_user",
                "No tienes permiso para ver coincidencias de esta orden de venta"
            )

        return self._process_order_matches(order, order_type)

    def _get_order_with_permission_check(self, model_class, order_id, user, user_field, error_message):
        try:
            order = model_class.objects.get(id=order_id)
        except model_class.DoesNotExist:
            raise FindMatchesObjectNotFound(
                f"Orden {'de compra' if model_class == PurchaseOrder else 'de venta'} no encontrada"
            )

        if not user.is_staff and getattr(order, user_field) != user:
            raise FindMatchesPermissionDenied(error_message)

        return order

    def _process_order_matches(self, order, order_type):
        matcher = OrderMatch()
        matches = matcher.find_matches_for_order(order)

        if order_type == "purchase":
            formatted_matches = self._format_purchase_order_matches(matches)
        else:
            formatted_matches = self._format_sales_order_matches(matches)

        order_id = str(order.id)

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

        return {
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
        }

    def _format_purchase_order_matches(self, matches):
        formatted = []
        for i, match in enumerate(matches):
            sales_order = match["sales_order"]
            formatted.append({
                "match_index": i,
                "sales_order_id": str(sales_order.id),
                "order_number": sales_order.order_number,
                "seller": sales_order.seller_user.username,
                "price_per_unit": float(match["match_price"]),
                "matched_units": match["matched_units"],
                "available_units": sales_order.available_units,
                "total_amount": float(match["total_amount"]),
                "fund": sales_order.fund.name,
                "match_percentage": match.get("match_percentage", 0),
                "is_partial": match.get("is_partial", False),
                "expiration_date": sales_order.expiration_date.isoformat() if sales_order.expiration_date else None
            })
        return formatted

    def _format_sales_order_matches(self, matches):
        formatted = []
        for i, match in enumerate(matches):
            purchase_order = match["purchase_order"]
            formatted.append({
                "match_index": i,
                "purchase_order_id": str(purchase_order.id),
                "order_number": purchase_order.order_number,
                "buyer": purchase_order.supplier_user.username,
                "price_per_unit": float(match["match_price"]),
                "matched_units": match["matched_units"],
                "available_units": purchase_order.available_units,
                "total_amount": float(match["total_amount"]),
                "fund": purchase_order.fund.name,
                "match_percentage": match.get("match_percentage", 0),
                "is_partial": match.get("is_partial", False),
                "expiration_date": purchase_order.expiration_date.isoformat() if purchase_order.expiration_date else None
            })
        return formatted

    def _process_general_matching(self):
        matcher = OrderMatch()
        matches = matcher.find_matches()

        if not matches:
            return {
                "message": "No se encontraron matches disponibles en el sistema",
                "total_matches": 0,
                "matches": []
            }

        formatted_matches = []
        for match in matches:
            purchase_order = match["purchase_order"]
            sales_order = match["sales_order"]

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
                    "matched_units": match["matched_units"],
                    "price_per_unit": float(match["match_price"]),
                    "total_amount": float(match["total_amount"]),
                    "fund": purchase_order.fund.name,
                    "compatibility_score": match.get("match_percentage", 0)
                }
            })

        return {
            "total_matches_found": len(formatted_matches),
            "matches": formatted_matches,
            "admin_note": "Como administrador, puedes ver todos los matches. Los usuarios deben usar select_matches y pay_selection para ejecutar transacciones.",
            "workflow_info": {
                "user_flow": "find_matches -> select_matches -> pay_selection",
                "admin_capabilities": "Puede ver todos los matches pero no ejecutarlos directamente"
            }
        }