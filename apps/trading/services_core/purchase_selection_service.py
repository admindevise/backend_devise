from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Any
from decimal import Decimal

from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from .match_selection_core import MatchSelectionCore, SelectionServiceError, InsufficientUnitsWarning

class PurchaseMatchSelectionService(MatchSelectionCore):
    """Servicio de selección de matches para compradores (PurchaseOrder)"""
    
    # ========================================
    # MÉTODOS PRINCIPALES
    # ========================================
    
    @transaction.atomic
    def process_manual_selection(
        self,
        purchase_order: PurchaseOrder,
        selected_matches: List[Dict[str, Any]],
        user,
        request=None
    ) -> Dict[str, Any]:
        """
        Procesa selección MANUAL de matches para una orden de compra
        """
        try:
            # 1. Validaciones específicas para compra
            self._validate_purchase_selection_request(purchase_order, selected_matches, user)
            
            # 2. Obtener matches disponibles
            available_matches = self._get_available_matches_for_purchase(purchase_order)
            
            # 3. Procesar y validar selecciones
            validated_selections = self._process_purchase_selections(
                selected_matches, available_matches, purchase_order
            )
            
            # 4. Crear la selección (carrito)
            selection = self._create_match_selection_base(
                main_order=purchase_order,
                validated_selections=validated_selections,
                user=user,
                selection_method='manual'
            )
            
            # 5. Registrar auditoría
            self._log_selection_audit_base(
                purchase_order, selection, user, 
                'PURCHASE_MATCH_SELECTION', 'purchase_match_selection', request
            )
            
            # 6. Preparar respuesta
            return self._build_purchase_selection_response(purchase_order, selection)
            
        except Exception as e:
            self._log_error_audit_base(purchase_order, str(e), user, request)
            raise SelectionServiceError(f"Error en selección de matches: {str(e)}")

    @transaction.atomic
    def process_auto_selection(
        self,
        purchase_order: PurchaseOrder,
        user,
        force_partial=False,
        request=None
    ) -> Dict[str, Any]:
        """
        Procesa selección AUTOMÁTICA de matches para una orden de compra
        """
        try:
            # 1. Validaciones específicas
            self._validate_purchase_selection_request(purchase_order, [], user)
            
            # 2. Obtener matches disponibles ordenados por mejor precio
            available_matches = self._get_available_matches_for_purchase(purchase_order)
            
            # 3. Generar selección automática
            auto_selection_result = self._generate_auto_purchase_selection(
                purchase_order, available_matches, force_partial
            )
            
            # 4. Si hay advertencia de unidades insuficientes y no se fuerza
            if auto_selection_result.get('insufficient_units') and not force_partial:
                return self._build_insufficient_units_response(
                    purchase_order, auto_selection_result, user, request
                )
            
            # 5. Crear la selección
            validated_selections = auto_selection_result['validated_selections']
            selection = self._create_match_selection_base(
                main_order=purchase_order,
                validated_selections=validated_selections,
                user=user,
                selection_method='automatic'
            )
            
            # 6. Registrar auditoría
            self._log_auto_selection_audit(purchase_order, selection, auto_selection_result, user, request)
            
            # 7. Preparar respuesta
            return self._build_auto_purchase_selection_response(purchase_order, selection, auto_selection_result)
            
        except InsufficientUnitsWarning as w:
            self._log_warning_audit(purchase_order, str(w), w.warning_data, user, request)
            raise
        except Exception as e:
            self._log_error_audit_base(purchase_order, str(e), user, request)
            raise SelectionServiceError(f"Error en selección automática: {str(e)}")

    # ========================================
    # VALIDACIONES ESPECÍFICAS
    # ========================================
    
    def _validate_purchase_selection_request(
        self,
        purchase_order: PurchaseOrder,
        selected_matches: List[Dict[str, Any]],
        user
    ) -> None:
        """Validaciones específicas para selección de compra"""
        
        # Verificar permisos específicos de compra
        if not user.is_staff and purchase_order.supplier_user != user:
            raise SelectionServiceError('No tienes permisos para seleccionar matches de esta orden de compra')
        
        # Validaciones base
        self._validate_selection_request_base(purchase_order, selected_matches, user)

    # ========================================
    # PROCESAMIENTO DE SELECCIONES
    # ========================================
    
    def _process_purchase_selections(
        self,
        selected_matches: List[Dict[str, Any]],
        available_matches: List[Dict[str, Any]],
        purchase_order: PurchaseOrder
    ) -> List[Dict[str, Any]]:
        """Procesa selecciones manuales para compra"""
        
        validated_selections = []
        total_selected_units = 0
        
        for selection in selected_matches:
            # Resolver orden de venta
            sales_order = self._resolve_target_order(selection, available_matches, 'sales')
            
            # Validar y calcular unidades
            requested_units = self._validate_and_get_units(
                selection, sales_order, purchase_order, total_selected_units
            )
            
            # Calcular costo
            unit_cost = Decimal(str(requested_units)) * sales_order.price_per_unit
            total_selected_units += requested_units
            
            # Crear selección validada
            validated_selection = {
                'sales_order': sales_order,
                'units': requested_units,
                'price_per_unit': sales_order.price_per_unit,
                'subtotal': unit_cost,
                'available_units': sales_order.available_units or sales_order.units,
                'selected_at': timezone.now(),
                'auto_selected': False
                }
            
            validated_selections.append(validated_selection)
            
            # Evitar exceder las unidades que quiere comprar
            if total_selected_units >= purchase_order.units:
                break
        
        return validated_selections

    def _generate_auto_purchase_selection(
        self,
        purchase_order: PurchaseOrder,
        available_matches: List[Dict[str, Any]],
        force_partial: bool = False
    ) -> Dict[str, Any]:
        """Genera selección automática para compra basada en mejor precio"""
        
        target_units = purchase_order.available_units
        remaining_units = target_units
        validated_selections = []
        total_cost = Decimal('0')
        
        # Iterar matches en orden de mejor precio
        for match in available_matches:
            if remaining_units <= 0:
                break
            
            sales_order = match['sales_order']
            available_units = sales_order.available_units or sales_order.units
            
            # Calcular unidades a tomar de esta orden
            units_to_take = min(remaining_units, available_units)
            
            if units_to_take <= 0:
                continue
            
            # Calcular costo
            unit_cost = Decimal(str(units_to_take)) * sales_order.price_per_unit
            total_cost += unit_cost
            
            # Verificar que no exceda presupuesto
            if total_cost > purchase_order.total_amount:
                # Si excede presupuesto, ajustar unidades
                remaining_budget = purchase_order.total_amount - (total_cost - unit_cost)
                max_affordable_units = int(remaining_budget / sales_order.price_per_unit)
                
                if max_affordable_units > 0:
                    units_to_take = max_affordable_units
                    unit_cost = Decimal(str(units_to_take)) * sales_order.price_per_unit
                    total_cost = (total_cost - unit_cost) + unit_cost
                else:
                    break
            
            # Crear selección validada
            validated_selection = {
                'sales_order': sales_order,
                'units': units_to_take,
                'price_per_unit': sales_order.price_per_unit,
                'subtotal': unit_cost,
                'available_units': available_units,
                'selected_at': timezone.now(),
                'auto_selected': True
            }
            
            validated_selections.append(validated_selection)
            remaining_units -= units_to_take
        
        # Verificar completitud
        units_selected = target_units - remaining_units
        is_complete = remaining_units == 0
        insufficient_units = not is_complete
        
        return {
            'validated_selections': validated_selections,
            'units_selected': units_selected,
            'units_remaining': remaining_units,
            'target_units': target_units,
            'is_complete': is_complete,
            'insufficient_units': insufficient_units,
            'total_cost': float(total_cost),
            'matches_used': len(validated_selections),
            'selection_method': 'automatic'
        }

    # ========================================
    # RESPUESTAS ESPECÍFICAS
    # ========================================
    
    def _build_purchase_selection_response(
        self,
        purchase_order: PurchaseOrder,
        selection
    ) -> Dict[str, Any]:
        """Construye respuesta específica para compra"""
        
        response = self._build_base_selection_response(purchase_order, selection)
        
        # Agregar información específica de compra
        response.update({
            'purchase_details': {
                'original_budget': float(purchase_order.total_amount),
                'amount_to_pay': float(selection.total_amount),
                'savings_achieved': float(selection.expected_savings),
                'budget_utilization': round((float(selection.total_amount) / float(purchase_order.total_amount)) * 100, 1)
            }
        })
        
        return response

    def _build_auto_purchase_selection_response(
        self,
        purchase_order: PurchaseOrder,
        selection,
        auto_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Construye respuesta de selección automática para compra"""
        
        response = self._build_purchase_selection_response(purchase_order, selection)
        
        # Agregar información específica de selección automática
        response.update({
            'completion_status': {
                'is_complete': auto_result['is_complete'],
                'units_selected': auto_result['units_selected'],
                'units_requested': auto_result['target_units'],
                'completion_percentage': round((auto_result['units_selected'] / auto_result['target_units']) * 100, 1)
            },
            'auto_selection_details': {
                'selection_strategy': 'best_price_first',
                'matches_evaluated': len(auto_result.get('available_matches', [])),
                'matches_selected': auto_result['matches_used']
            }
        })
        
        return response

    def _build_insufficient_units_response(
        self,
        purchase_order: PurchaseOrder,
        auto_selection_result: Dict[str, Any],
        user,
        request=None
    ) -> Dict[str, Any]:
        """Respuesta cuando no hay suficientes unidades para compra"""
        
        units_available = auto_selection_result['units_selected']
        units_requested = auto_selection_result['target_units']
        units_missing = auto_selection_result['units_remaining']
        
        return {
            'success': False,
            'warning_type': 'INSUFFICIENT_UNITS',
            'message': f'Solo hay {units_available} unidades disponibles de las {units_requested} solicitadas',
            'details': {
                'units_requested': units_requested,
                'units_available': units_available,
                'units_missing': units_missing,
                'completion_percentage': round((units_available / units_requested) * 100, 1),
                'estimated_cost': auto_selection_result['total_cost'],
                'matches_count': auto_selection_result['matches_used']
            },
            'confirmation_required': {
                'message': f'¿Desea continuar comprando solo {units_available} unidades?',
                'action': 'Para confirmar, envíe la misma solicitud con force_partial=true',
                'endpoint': request.build_absolute_uri() if request else '/trading/auto-select-matches/',
                'params': {
                    'purchase_order_id': str(purchase_order.id),
                    'force_partial': True
                }
            }
        }

    # ========================================
    # AUDITORÍA ESPECÍFICA
    # ========================================
    
    def _log_auto_selection_audit(
        self,
        purchase_order: PurchaseOrder,
        selection,
        auto_result: Dict[str, Any],
        user,
        request=None
    ) -> None:
        """Auditoría específica para selección automática de compra"""
        
        if request:
            from apps.audit.audit_service import AuditService
            AuditService.log_action(
                request=request,
                action_code='AUTO_PURCHASE_MATCH_SELECTION',
                obj=purchase_order,
                details={
                    'order_number': purchase_order.order_number,
                    'selection_id': str(selection.id),
                    'selection_method': 'automatic',
                    'matches_selected': selection.items.count(),
                    'total_units_selected': selection.total_units,
                    'total_amount_selected': float(selection.total_amount),
                    'savings_achieved': float(selection.expected_savings),
                    'is_complete_order': auto_result['is_complete'],
                    'completion_percentage': round((auto_result['units_selected'] / auto_result['target_units']) * 100, 1),
                    'matches_used': auto_result['matches_used'],
                    'selected_by': user.email,
                    'operation': 'auto_purchase_match_selection'
                },
                status='SUCCESS'
            )

    def _log_warning_audit(
        self,
        purchase_order: PurchaseOrder,
        warning_msg: str,
        warning_data: Dict[str, Any],
        user,
        request=None
    ) -> None:
        """Auditoría de advertencia para compra"""
        
        if request:
            from apps.audit.audit_service import AuditService
            AuditService.log_action(
                request=request,
                action_code='AUTO_PURCHASE_SELECTION_WARNING',
                obj=purchase_order,
                details={
                    'order_number': purchase_order.order_number,
                    'warning_type': 'insufficient_units',
                    'warning_message': warning_msg,
                    'units_requested': warning_data.get('units_requested', 0),
                    'units_available': warning_data.get('units_available', 0),
                    'completion_percentage': warning_data.get('completion_percentage', 0),
                    'selected_by': user.email,
                    'operation': 'auto_purchase_selection_warning'
                },
                status='WARNING'
            )