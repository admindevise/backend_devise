# apps/trading/services/match_selection_service.py
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Any

from apps.trading.models import PurchaseOrder, SalesOrder
from apps.trading.order_matching import OrderMatch
from apps.audit.audit_service import AuditService
import logging

logger = logging.getLogger('trading.match_selection')

class MatchSelectionError(Exception):
    """Excepción personalizada para errores de selección de matches"""
    pass

class InsufficientUnitsWarning(Exception):
    """Excepción para advertir sobre unidades insuficientes"""
    def __init__(self, message, available_units, warning_data):
        super().__init__(message)
        self.available_units = available_units
        self.warning_data = warning_data

class MatchSelectionService:
    """
    🎯 Servicio Unificado de Selección de Matches
    
    Maneja tanto la selección AUTOMÁTICA como MANUAL de matches:
    - Selección automática: Encuentra los mejores matches por precio
    - Selección manual: Procesa matches específicos seleccionados por el usuario
    - Validaciones y auditoría completa
    - Manejo de advertencias por unidades insuficientes
    """
    
    def __init__(self):
        self.matcher = OrderMatch()
        self.selection_expiry_minutes = 15  # Tiempo de expiración de selecciones
    
    # ========================================
    # MÉTODOS PRINCIPALES
    # ========================================
    
    @transaction.atomic
    def process_auto_match_selection(
        self,
        purchase_order: PurchaseOrder,
        user,
        force_partial=False,
        request=None
    ) -> Dict[str, Any]:
        """
        Procesa selección AUTOMÁTICA de matches para una orden de compra
        
        Args:
            purchase_order: Orden de compra objetivo
            user: Usuario que hace la selección
            force_partial: Si True, acepta selecciones parciales sin confirmar
            request: Request HTTP para auditoría
            
        Returns:
            Dict con resultados de la selección o advertencia de unidades insuficientes
            
        Raises:
            MatchSelectionError: Si hay errores en la selección
            InsufficientUnitsWarning: Si no hay suficientes unidades y force_partial=False
        """
        try:
            # 1. Validaciones previas
            self._validate_selection_request(purchase_order, [], user)
            
            # 2. Obtener matches disponibles ordenados por mejor precio
            available_matches = self._get_available_matches(purchase_order)
            
            # 3. Generar selección automática
            auto_selection_result = self._generate_auto_selection(
                purchase_order, available_matches, force_partial
            )
            
            # 4. Si hay advertencia de unidades insuficientes y no se fuerza
            if auto_selection_result.get('insufficient_units') and not force_partial:
                return self._build_insufficient_units_response(
                    purchase_order, auto_selection_result, user, request
                )
            
            # 5. Procesar selecciones automáticas
            validated_selections = auto_selection_result['validated_selections']
            
            # 6. Calcular totales y verificar presupuesto
            selection_summary = self._calculate_selection_summary(
                validated_selections, purchase_order
            )
            
            # 7. Guardar selección en metadatos
            self._save_selection_metadata(purchase_order, validated_selections, selection_summary)
            
            # 8. Actualizar estado de la orden
            self._update_purchase_order_status(purchase_order)
            
            # 9. Registrar auditoría
            self._log_auto_selection_audit(
                purchase_order, selection_summary, auto_selection_result, user, request
            )
            
            # 10. Preparar respuesta
            return self._build_auto_selection_response(
                purchase_order, validated_selections, selection_summary, auto_selection_result
            )
            
        except InsufficientUnitsWarning as w:
            # Registrar auditoría de advertencia
            self._log_warning_audit(purchase_order, str(w), w.warning_data, user, request)
            raise
        except Exception as e:
            # Registrar auditoría de error
            self._log_error_audit(purchase_order, str(e), user, request)
            raise MatchSelectionError(f"Error en selección automática: {str(e)}")
    
    @transaction.atomic
    def process_match_selection(
        self,
        purchase_order: PurchaseOrder,
        selected_matches: List[Dict[str, Any]],
        user,
        request=None
    ) -> Dict[str, Any]:
        """
        Procesa selección MANUAL de matches específicos para una orden de compra
        
        Args:
            purchase_order: Orden de compra objetivo
            selected_matches: Lista de matches seleccionados manualmente
            user: Usuario que hace la selección
            request: Request HTTP para auditoría
            
        Returns:
            Dict con resultados de la selección
            
        Raises:
            MatchSelectionError: Si hay errores en la selección
        """
        try:
            # 1. Validaciones previas
            self._validate_selection_request(purchase_order, selected_matches, user)
            
            # 2. Obtener matches disponibles
            available_matches = self._get_available_matches(purchase_order)
            
            # 3. Procesar y validar selecciones
            validated_selections = self._process_selections(
                selected_matches, available_matches, purchase_order
            )
            
            # 4. Calcular totales y verificar presupuesto
            selection_summary = self._calculate_selection_summary(
                validated_selections, purchase_order
            )
            
            # 5. Guardar selección en metadatos
            self._save_selection_metadata(purchase_order, validated_selections, selection_summary)
            
            # 6. Actualizar estado de la orden
            self._update_purchase_order_status(purchase_order)
            
            # 7. Registrar auditoría
            self._log_selection_audit(purchase_order, selection_summary, user, request)
            
            # 8. Preparar respuesta
            return self._build_selection_response(
                purchase_order, validated_selections, selection_summary
            )
            
        except Exception as e:
            # Registrar auditoría de error
            self._log_error_audit(purchase_order, str(e), user, request)
            raise MatchSelectionError(f"Error en selección de matches: {str(e)}")
    
    # ========================================
    # GENERACIÓN DE SELECCIÓN AUTOMÁTICA
    # ========================================
    
    def _generate_auto_selection(
        self,
        purchase_order: PurchaseOrder,
        available_matches: List[Dict[str, Any]],
        force_partial: bool = False
    ) -> Dict[str, Any]:
        """
        Genera selección automática de matches basada en mejor precio y disponibilidad
        
        Args:
            purchase_order: Orden de compra objetivo
            available_matches: Lista de matches disponibles ordenados por precio
            force_partial: Si acepta selecciones parciales
            
        Returns:
            Dict con selecciones validadas e información de disponibilidad
        """
        
        target_units = purchase_order.units
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
                    break  # No se puede comprar más con el presupuesto
            
            # Crear selección validada
            validated_selection = {
                'sales_order_id': str(sales_order.id),
                'sales_order_number': sales_order.order_number,
                'seller_email': sales_order.seller_user.email,
                'units': units_to_take,
                'price_per_unit': float(sales_order.price_per_unit),
                'subtotal': float(unit_cost),
                'available_units': available_units,
                'selected_at': timezone.now().isoformat(),
                'auto_selected': True  # Marcar como selección automática
            }
            
            validated_selections.append(validated_selection)
            remaining_units -= units_to_take
        
        # Verificar si se completó la orden o hay unidades faltantes
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
    # VALIDACIONES
    # ========================================
    
    def _validate_selection_request(
        self,
        purchase_order: PurchaseOrder,
        selected_matches: List[Dict[str, Any]],
        user
    ) -> None:
        """Valida la solicitud de selección"""
        
        # Verificar permisos
        if not user.is_staff and purchase_order.supplier_user != user:
            raise MatchSelectionError('No tienes permisos para seleccionar matches de esta orden')
        
        # ✅ CORREGIR: Usar sintaxis correcta para instancias
        if purchase_order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
            raise MatchSelectionError(
                f'La orden debe estar PENDING o PARTIALLY_EXECUTED para seleccionar matches. Estado actual: {purchase_order.status}'
            )
        
        if selected_matches is not None and isinstance(selected_matches, list) and len(selected_matches) > 0:
            # Es selección MANUAL - validar que tenga contenido válido
            for i, match in enumerate(selected_matches):
                if not isinstance(match, dict):
                    raise MatchSelectionError(f'Match {i+1} debe ser un objeto válido')
                if not (match.get('sales_order_id') or match.get('match_index') is not None):
                    raise MatchSelectionError(f'Match {i+1} debe tener sales_order_id o match_index')
    
    
    def _get_available_matches(self, purchase_order: PurchaseOrder) -> List[Dict[str, Any]]:
        """Obtiene matches disponibles para la orden"""
        
        try:
            available_matches = self.matcher.find_matches_for_order(purchase_order)
            
            if not available_matches:
                raise MatchSelectionError('No hay matches disponibles para esta orden')
            
            return available_matches
            
        except Exception as e:
            raise MatchSelectionError(f'Error obteniendo matches disponibles: {str(e)}')
    
    # ========================================
    # PROCESAMIENTO DE SELECCIONES MANUALES
    # ========================================
    
    def _process_selections(
        self,
        selected_matches: List[Dict[str, Any]],
        available_matches: List[Dict[str, Any]],
        purchase_order: PurchaseOrder
    ) -> List[Dict[str, Any]]:
        """Procesa y valida cada selección individual"""
        
        validated_selections = []
        total_selected_units = 0
        
        for selection in selected_matches:
            # Resolver orden de venta
            sales_order = self._resolve_sales_order(selection, available_matches)
            
            # Validar y calcular unidades
            requested_units = self._validate_and_get_units(
                selection, sales_order, purchase_order, total_selected_units
            )
            
            # Calcular costo
            unit_cost = Decimal(str(requested_units)) * sales_order.price_per_unit
            total_selected_units += requested_units
            
            # Crear selección validada
            validated_selection = {
                'sales_order_id': str(sales_order.id),
                'sales_order_number': sales_order.order_number,
                'seller_email': sales_order.seller_user.email,
                'units': requested_units,
                'price_per_unit': float(sales_order.price_per_unit),
                'subtotal': float(unit_cost),
                'available_units': sales_order.available_units or sales_order.units,
                'selected_at': timezone.now().isoformat(),
                'auto_selected': False  # Marcar como selección manual
            }
            
            validated_selections.append(validated_selection)
            
            # Evitar exceder las unidades que quiere comprar
            if total_selected_units >= purchase_order.units:
                break
        
        return validated_selections
    
    def _resolve_sales_order(
        self,
        selection: Dict[str, Any],
        available_matches: List[Dict[str, Any]]
    ) -> SalesOrder:
        """Resuelve la orden de venta desde selección por ID o índice"""
        
        sales_order_id = selection.get('sales_order_id')
        match_index = selection.get('match_index')
        
        if not sales_order_id and match_index is None:
            raise MatchSelectionError('Cada selección debe tener sales_order_id o match_index')
        
        # Resolver por índice
        if match_index is not None:
            try:
                match = available_matches[match_index]
                return match['sales_order']
            except (IndexError, KeyError):
                raise MatchSelectionError(f'Índice de match inválido: {match_index}')
        
        # Resolver por ID
        try:
            sales_order = SalesOrder.objects.select_for_update().get(
                id=sales_order_id,
                status__in=['PENDING', 'PARTIALLY_EXECUTED']
            )
            return sales_order
        except SalesOrder.DoesNotExist:
            raise MatchSelectionError(f'Orden de venta no encontrada o no disponible: {sales_order_id}')
    
    def _validate_and_get_units(
        self,
        selection: Dict[str, Any],
        sales_order: SalesOrder,
        purchase_order: PurchaseOrder,
        total_selected_units: int
    ) -> int:
        """Valida y obtiene las unidades a seleccionar"""
        
        requested_units = selection.get('units')
        
        # Usar automático si no se especifica
        if not requested_units:
            remaining_purchase_units = purchase_order.units - total_selected_units
            available_sales_units = sales_order.available_units or sales_order.units
            requested_units = min(available_sales_units, remaining_purchase_units)
        
        # Validar límites
        remaining_purchase_units = purchase_order.units - total_selected_units
        available_sales_units = sales_order.available_units or sales_order.units
        max_available = min(available_sales_units, remaining_purchase_units)
        
        if requested_units <= 0:
            raise MatchSelectionError('Las unidades solicitadas deben ser mayor que 0')
        
        if requested_units > max_available:
            raise MatchSelectionError(
                f'Unidades solicitadas ({requested_units}) exceden disponibles ({max_available}) para orden {sales_order.order_number}'
            )
        
        return requested_units
    
    # ========================================
    # CÁLCULOS Y VERIFICACIONES
    # ========================================
    
    def _calculate_selection_summary(
        self,
        validated_selections: List[Dict[str, Any]],
        purchase_order: PurchaseOrder
    ) -> Dict[str, Any]:
        """Calcula resumen de la selección sin restricciones de presupuesto"""
        
        total_selected_units = sum(sel['units'] for sel in validated_selections)
        total_amount = sum(Decimal(str(sel['subtotal'])) for sel in validated_selections)
        
        # Calcular ahorros (dinero que NO se gasta del presupuesto original)
        savings = float(purchase_order.total_amount - total_amount)
        
        # Solo calcular información, sin restricciones
        budget_comparison = {
            'original_budget': float(purchase_order.total_amount),
            'selected_amount': float(total_amount),
            'difference': savings,  # Usar el valor calculado
            'exceeds_original': total_amount > purchase_order.total_amount
        }
        
        expires_at = timezone.now() + timedelta(minutes=self.selection_expiry_minutes)
        
        return {
            'total_units': total_selected_units,
            'total_amount': float(total_amount),
            'savings': savings,  # ← AGREGAR este campo faltante
            'budget_comparison': budget_comparison,
            'matches_count': len(validated_selections),
            'selected_at': timezone.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'selection_valid': True
        }
    
    # ========================================
    # PERSISTENCIA
    # ========================================
    
    def _save_selection_metadata(
        self,
        purchase_order: PurchaseOrder,
        validated_selections: List[Dict[str, Any]],
        selection_summary: Dict[str, Any]
    ) -> None:
        """Guarda la selección en metadatos de la orden"""
        
        purchase_order.metadata = purchase_order.metadata or {}
        purchase_order.metadata.update({
            'selected_matches': validated_selections,
            'selection_summary': selection_summary,
            'selection_history': purchase_order.metadata.get('selection_history', []) + [{
                'selected_at': selection_summary['selected_at'],
                'matches_count': selection_summary['matches_count'],
                'total_amount': selection_summary['total_amount']
            }]
        })
        purchase_order.save(update_fields=['metadata'])
    
    def _update_purchase_order_status(self, purchase_order: PurchaseOrder) -> None:
        """Actualiza el estado de la orden a MATCHES_SELECTED"""
        
        purchase_order.status = 'MATCHES_SELECTED'
        purchase_order.matched_at = timezone.now()
        purchase_order.save(update_fields=['status', 'matched_at'])
    
    # ========================================
    # RESPUESTAS ESPECIALIZADAS
    # ========================================
    
    def _build_insufficient_units_response(
        self,
        purchase_order: PurchaseOrder,
        auto_selection_result: Dict[str, Any],
        user,
        request=None
    ) -> Dict[str, Any]:
        """Construye respuesta cuando no hay suficientes unidades disponibles"""
        
        units_available = auto_selection_result['units_selected']
        units_requested = auto_selection_result['target_units']
        units_missing = auto_selection_result['units_remaining']
        
        warning_data = {
            'purchase_order_id': str(purchase_order.id),
            'units_requested': units_requested,
            'units_available': units_available,
            'units_missing': units_missing,
            'completion_percentage': round((units_available / units_requested) * 100, 1),
            'estimated_cost': auto_selection_result['total_cost'],
            'matches_available': auto_selection_result['matches_used'],
            'potential_selections': auto_selection_result['validated_selections']
        }
        
        return {
            'success': False,
            'warning_type': 'INSUFFICIENT_UNITS',
            'message': f'Solo hay {units_available} unidades disponibles de las {units_requested} solicitadas',
            'details': {
                'units_requested': units_requested,
                'units_available': units_available,
                'units_missing': units_missing,
                'completion_percentage': warning_data['completion_percentage'],
                'estimated_cost': auto_selection_result['total_cost'],
                'matches_count': auto_selection_result['matches_used']
            },
            'available_selection': {
                'matches': auto_selection_result['validated_selections'],
                'summary': {
                    'total_units': units_available,
                    'total_cost': auto_selection_result['total_cost'],
                    'matches_count': auto_selection_result['matches_used']
                }
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
    
    def _build_auto_selection_response(
        self,
        purchase_order: PurchaseOrder,
        validated_selections: List[Dict[str, Any]],
        selection_summary: Dict[str, Any],
        auto_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Construye respuesta de selección automática exitosa"""
        
        return {
            'success': True,
            'selection_method': 'automatic',
            'message': f'Selección automática completada: {selection_summary["matches_count"]} matches seleccionados',
            'completion_status': {
                'is_complete': auto_result['is_complete'],
                'units_selected': auto_result['units_selected'],
                'units_requested': auto_result['target_units'],
                'completion_percentage': round((auto_result['units_selected'] / auto_result['target_units']) * 100, 1)
            },
            'selection_summary': {
                'total_units_selected': selection_summary['total_units'],
                'total_amount_to_pay': selection_summary['total_amount'],
                'savings_vs_budget': selection_summary['savings'],
                'payment_deadline': selection_summary['expires_at'],
                'matches_count': selection_summary['matches_count'],
                'average_price': round(selection_summary['total_amount'] / selection_summary['total_units'], 2)
            },
            'selected_matches': validated_selections,
            'order_status': purchase_order.status,
            'auto_selection_details': {
                'selection_strategy': 'best_price_first',
                'matches_evaluated': len(auto_result.get('available_matches', [])),
                'matches_selected': auto_result['matches_used'],
                'budget_utilization': round((selection_summary['total_amount'] / float(purchase_order.total_amount)) * 100, 1)
            },
            'next_step': {
                'action': 'Proceder al pago',
                'endpoint': '/trading/pay-selection/',
                'purchase_order_id': str(purchase_order.id),
                'amount_to_pay': selection_summary['total_amount'],
                'payment_deadline': selection_summary['expires_at']
            }
        }
    
    def _build_selection_response(
        self,
        purchase_order: PurchaseOrder,
        validated_selections: List[Dict[str, Any]],
        selection_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Construye la respuesta de selección manual exitosa"""
        
        return {
            'success': True,
            'selection_method': 'manual',
            'message': f'Matches seleccionados exitosamente: {selection_summary["matches_count"]} matches',
            'selection_summary': {
                'total_units_selected': selection_summary['total_units'],
                'total_amount_to_pay': selection_summary['total_amount'],
                'savings_vs_budget': selection_summary['savings'],
                'payment_deadline': selection_summary['expires_at'],
                'matches_count': selection_summary['matches_count']
            },
            'selected_matches': validated_selections,
            'order_status': purchase_order.status,
            'next_step': {
                'action': 'Proceder al pago',
                'endpoint': '/trading/pay-selection/',
                'purchase_order_id': str(purchase_order.id),
                'amount_to_pay': selection_summary['total_amount'],
                'payment_deadline': selection_summary['expires_at']
            }
        }
    
    # ========================================
    # AUDITORÍA
    # ========================================
    
    def _log_auto_selection_audit(
        self,
        purchase_order: PurchaseOrder,
        selection_summary: Dict[str, Any],
        auto_result: Dict[str, Any],
        user,
        request=None
    ) -> None:
        """Registra auditoría de selección automática exitosa"""
        
        if request:
            AuditService.log_action(
                request=request,
                action_code='AUTO_MATCH_SELECTION',
                obj=purchase_order,
                details={
                    'order_number': purchase_order.order_number,
                    'selection_method': 'automatic',
                    'matches_selected': selection_summary['matches_count'],
                    'total_units_selected': selection_summary['total_units'],
                    'total_amount_selected': selection_summary['total_amount'],
                    'savings_achieved': selection_summary['savings'],
                    'is_complete_order': auto_result['is_complete'],
                    'completion_percentage': round((auto_result['units_selected'] / auto_result['target_units']) * 100, 1),
                    'matches_used': auto_result['matches_used'],
                    'selected_by': user.email,
                    'operation': 'auto_match_selection'
                },
                status='SUCCESS'
            )
    
    def _log_selection_audit(
        self,
        purchase_order: PurchaseOrder,
        selection_summary: Dict[str, Any],
        user,
        request=None
    ) -> None:
        """Registra auditoría de selección manual exitosa"""
        
        if request:
            AuditService.log_action(
                request=request,
                action_code='MATCH_SELECTION_PROCESS',
                obj=purchase_order,
                details={
                    'order_number': purchase_order.order_number,
                    'selection_method': 'manual',
                    'matches_selected': selection_summary['matches_count'],
                    'total_units_selected': selection_summary['total_units'],
                    'total_amount_selected': selection_summary['total_amount'],
                    'savings_achieved': selection_summary['savings'],
                    'selection_expires_at': selection_summary['expires_at'],
                    'selected_by': user.email,
                    'operation': 'match_selection'
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
        """Registra auditoría de advertencia de unidades insuficientes"""
        
        if request:
            AuditService.log_action(
                request=request,
                action_code='AUTO_SELECTION_WARNING',
                obj=purchase_order,
                details={
                    'order_number': purchase_order.order_number,
                    'warning_type': 'insufficient_units',
                    'warning_message': warning_msg,
                    'units_requested': warning_data['units_requested'],
                    'units_available': warning_data['units_available'],
                    'completion_percentage': warning_data['completion_percentage'],
                    'selected_by': user.email,
                    'operation': 'auto_match_selection_warning'
                },
                status='WARNING'
            )
    
    def _log_error_audit(
        self,
        purchase_order: PurchaseOrder,
        error_msg: str,
        user,
        request=None
    ) -> None:
        """Registra auditoría de error"""
        
        if request:
            AuditService.log_action(
                request=request,
                action_code='MATCH_SELECTION_ERROR',
                obj=purchase_order,
                details={
                    'order_number': purchase_order.order_number,
                    'error': error_msg,
                    'selected_by': user.email,
                    'operation': 'match_selection_error'
                },
                status='ERROR'
            )