from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Any
from decimal import Decimal

from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from .match_selection_core import MatchSelectionCore, SelectionServiceError

class SalesMatchSelectionService(MatchSelectionCore):
    """Servicio de selección de matches para vendedores (SalesOrder)"""
    
    # ========================================
    # MÉTODOS PRINCIPALES
    # ========================================
    
    @transaction.atomic
    def process_manual_selection(
        self,
        sales_order: SalesOrder,
        selected_matches: List[Dict[str, Any]],
        user,
        request=None
    ) -> Dict[str, Any]:
        """
        Procesa selección MANUAL de matches para una orden de venta
        El vendedor selecciona específicamente a qué compradores vender
        """
        try:
            # 1. Validaciones específicas para venta
            self._validate_sales_selection_request(sales_order, selected_matches, user)
            
            # 2. Obtener matches disponibles (órdenes de compra compatibles)
            available_matches = self._get_available_matches_for_sales(sales_order)
            
            # 3. Procesar y validar selecciones
            validated_selections = self._process_sales_selections(
                selected_matches, available_matches, sales_order
            )
            
            # 4. Crear la selección (carrito)
            selection = self._create_match_selection_base(
                main_order=sales_order,
                validated_selections=validated_selections,
                user=user,
                selection_method='manual'
            )
            
            # 5. Registrar auditoría
            self._log_selection_audit_base(
                sales_order, selection, user, 
                'SALES_MATCH_SELECTION', 'sales_match_selection', request
            )
            
            # 6. Preparar respuesta
            return self._build_sales_selection_response(sales_order, selection)
            
        except Exception as e:
            self._log_error_audit_base(sales_order, str(e), user, request)
            raise SelectionServiceError(f"Error en selección de matches para venta: {str(e)}")

    @transaction.atomic
    def process_auto_selection(
        self,
        sales_order: SalesOrder,
        user,
        force_partial=False,
        request=None
    ) -> Dict[str, Any]:
        """
        Procesa selección AUTOMÁTICA de matches para una orden de venta
        Busca automáticamente los mejores compradores (mejor precio/prioridad)
        """
        try:
            # 1. Validaciones específicas
            self._validate_sales_selection_request(sales_order, [], user)
            
            # 2. Obtener matches disponibles ordenados por mejor precio
            available_matches = self._get_available_matches_for_sales(sales_order)
            
            # 3. Generar selección automática
            auto_selection_result = self._generate_auto_sales_selection(
                sales_order, available_matches, force_partial
            )
            
            # 4. Si hay advertencia de unidades insuficientes y no se fuerza
            if auto_selection_result.get('insufficient_buyers') and not force_partial:
                return self._build_insufficient_buyers_response(
                    sales_order, auto_selection_result, user, request
                )
            
            # 5. Crear la selección
            validated_selections = auto_selection_result['validated_selections']
            selection = self._create_match_selection_base(
                main_order=sales_order,
                validated_selections=validated_selections,
                user=user,
                selection_method='automatic'
            )
            
            # 6. Registrar auditoría
            self._log_auto_sales_selection_audit(sales_order, selection, auto_selection_result, user, request)
            
            # 7. Preparar respuesta
            return self._build_auto_sales_selection_response(sales_order, selection, auto_selection_result)
            
        except Exception as e:
            self._log_error_audit_base(sales_order, str(e), user, request)
            raise SelectionServiceError(f"Error en selección automática para venta: {str(e)}")

    # ========================================
    # VALIDACIONES ESPECÍFICAS
    # ========================================
    
    def _validate_sales_selection_request(
        self,
        sales_order: SalesOrder,
        selected_matches: List[Dict[str, Any]],
        user
    ) -> None:
        """Validaciones específicas para selección de venta"""
        
        # Verificar permisos específicos de venta
        if not user.is_staff and sales_order.seller_user != user:
            raise SelectionServiceError('No tienes permisos para seleccionar matches de esta orden de venta')
        
        # Validaciones base
        self._validate_selection_request_base(sales_order, selected_matches, user)

    # ========================================
    # PROCESAMIENTO DE SELECCIONES
    # ========================================
    
    def _process_sales_selections(
        self,
        selected_matches: List[Dict[str, Any]],
        available_matches: List[Dict[str, Any]],
        sales_order: SalesOrder
    ) -> List[Dict[str, Any]]:
        """Procesa selecciones manuales para venta"""
        
        validated_selections = []
        total_selected_units = 0
        
        for selection in selected_matches:
            # Resolver orden de compra
            purchase_order = self._resolve_target_order(selection, available_matches, 'purchase')
            
            # Validar y calcular unidades
            requested_units = self._validate_and_get_units(
                selection, purchase_order, sales_order, total_selected_units
            )
            
            # Calcular ingreso de la venta
            unit_revenue = Decimal(str(requested_units)) * sales_order.price_per_unit
            total_selected_units += requested_units
            
            # Crear selección validada
            validated_selection = {
                'purchase_order': purchase_order,
                'units': requested_units,
                'price_per_unit': sales_order.price_per_unit,
                'subtotal': unit_revenue,
                'available_units': purchase_order.available_units or purchase_order.units,
                'selected_at': timezone.now(),
                'auto_selected': False
            }
            
            validated_selections.append(validated_selection)
            
            # Evitar exceder las unidades que se quieren vender
            if total_selected_units >= sales_order.units:
                break
        
        return validated_selections

    def _generate_auto_sales_selection(
        self,
        sales_order: SalesOrder,
        available_matches: List[Dict[str, Any]],
        force_partial: bool = False
    ) -> Dict[str, Any]:
        """Genera selección automática para venta basada en mejor precio/prioridad"""
        
        target_units = sales_order.available_units
        remaining_units = target_units
        validated_selections = []
        total_revenue = Decimal('0')
        
        # Iterar matches ordenados por mejor precio/prioridad
        # Los matches deberían estar ordenados por purchase orders que paguen mejor precio
        for match in available_matches:
            if remaining_units <= 0:
                break
            
            purchase_order = match['purchase_order']
            units_buyer_wants = purchase_order.available_units
            
            # Calcular unidades a vender a este comprador
            units_to_sell = min(remaining_units, units_buyer_wants)
            
            if units_to_sell <= 0:
                continue
            
            # Calcular ingreso
            unit_revenue = Decimal(str(units_to_sell)) * sales_order.price_per_unit
            total_revenue += unit_revenue
            
            # Verificar que el comprador pueda pagar
            buyer_budget = purchase_order.total_amount
            cost_for_buyer = unit_revenue
            
            if cost_for_buyer > buyer_budget:
                # Ajustar unidades que el comprador puede pagar
                max_affordable_units = int(buyer_budget / sales_order.price_per_unit)
                
                if max_affordable_units > 0:
                    units_to_sell = max_affordable_units
                    unit_revenue = Decimal(str(units_to_sell)) * sales_order.price_per_unit
                    total_revenue = (total_revenue - unit_revenue) + unit_revenue
                else:
                    continue  # Este comprador no puede pagar nada
            
            # Crear selección validada
            validated_selection = {
                'purchase_order': purchase_order,
                'units': units_to_sell,
                'price_per_unit': sales_order.price_per_unit,
                'subtotal': unit_revenue,
                'available_units': units_buyer_wants,
                'selected_at': timezone.now(),
                'auto_selected': True
            }
            
            validated_selections.append(validated_selection)
            remaining_units -= units_to_sell
        
        # Verificar completitud
        units_selected = target_units - remaining_units
        is_complete = remaining_units == 0
        insufficient_buyers = not is_complete
        
        return {
            'validated_selections': validated_selections,
            'units_selected': units_selected,
            'units_remaining': remaining_units,
            'target_units': target_units,
            'is_complete': is_complete,
            'insufficient_buyers': insufficient_buyers,
            'total_revenue': float(total_revenue),
            'buyers_used': len(validated_selections),
            'selection_method': 'automatic'
        }

    # ========================================
    # RESPUESTAS ESPECÍFICAS
    # ========================================
    
    def _build_sales_selection_response(
        self,
        sales_order: SalesOrder,
        selection
    ) -> Dict[str, Any]:
        """Construye respuesta específica para venta"""
        
        response = self._build_base_selection_response(sales_order, selection)
        
        # Agregar información específica de venta
        response.update({
            'sales_details': {
                'units_to_sell': sales_order.units,
                'price_per_unit': float(sales_order.price_per_unit),
                'total_revenue': float(selection.total_amount),
                'units_sold': selection.total_units,
                'revenue_percentage': round((selection.total_units / sales_order.units) * 100, 1) if sales_order.units > 0 else 0
            }
        })
        
        return response

    def _build_auto_sales_selection_response(
        self,
        sales_order: SalesOrder,
        selection,
        auto_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Construye respuesta de selección automática para venta"""
        
        response = self._build_sales_selection_response(sales_order, selection)
        
        # Agregar información específica de selección automática
        response.update({
            'completion_status': {
                'is_complete': auto_result['is_complete'],
                'units_selected': auto_result['units_selected'],
                'units_available': auto_result['target_units'],
                'sell_completion_percentage': round((auto_result['units_selected'] / auto_result['target_units']) * 100, 1)
            },
            'auto_selection_details': {
                'selection_strategy': 'best_price_buyers_first',
                'buyers_evaluated': len(auto_result.get('available_matches', [])),
                'buyers_selected': auto_result['buyers_used']
            }
        })
        
        return response

    def _build_insufficient_buyers_response(
        self,
        sales_order: SalesOrder,
        auto_selection_result: Dict[str, Any],
        user,
        request=None
    ) -> Dict[str, Any]:
        """Respuesta cuando no hay suficientes compradores"""
        
        units_sold = auto_selection_result['units_selected']
        units_available = auto_selection_result['target_units']
        units_unsold = auto_selection_result['units_remaining']
        
        return {
            'success': False,
            'warning_type': 'INSUFFICIENT_BUYERS',
            'message': f'Solo se pueden vender {units_sold} unidades de las {units_available} disponibles',
            'details': {
                'units_available_to_sell': units_available,
                'units_that_can_be_sold': units_sold,
                'units_remaining_unsold': units_unsold,
                'sell_percentage': round((units_sold / units_available) * 100, 1),
                'estimated_revenue': auto_selection_result['total_revenue'],
                'buyers_count': auto_selection_result['buyers_used']
            },
            'confirmation_required': {
                'message': f'¿Desea continuar vendiendo solo {units_sold} unidades?',
                'action': 'Para confirmar, envíe la misma solicitud con force_partial=true',
                'endpoint': request.build_absolute_uri() if request else '/trading/auto-select-buyers/',
                'params': {
                    'sales_order_id': str(sales_order.id),
                    'force_partial': True
                }
            }
        }

    # ========================================
    # AUDITORÍA ESPECÍFICA
    # ========================================
    
    def _log_auto_sales_selection_audit(
        self,
        sales_order: SalesOrder,
        selection,
        auto_result: Dict[str, Any],
        user,
        request=None
    ) -> None:
        """Auditoría específica para selección automática de venta"""
        
        if request:
            from apps.audit.audit_service import AuditService
            AuditService.log_action(
                request=request,
                action_code='AUTO_SALES_MATCH_SELECTION',
                obj=sales_order,
                details={
                    'order_number': sales_order.order_number,
                    'selection_id': str(selection.id),
                    'selection_method': 'automatic',
                    'buyers_selected': selection.items.count(),
                    'total_units_sold': selection.total_units,
                    'total_revenue': float(selection.total_amount),
                    'is_complete_sale': auto_result['is_complete'],
                    'sell_completion_percentage': round((auto_result['units_selected'] / auto_result['target_units']) * 100, 1),
                    'buyers_used': auto_result['buyers_used'],
                    'selected_by': user.email,
                    'operation': 'auto_sales_match_selection'
                },
                status='SUCCESS'
            )