from apps.audit.audit_service import AuditService
from apps.trading.models.core_models import PurchaseOrder
from typing import Dict, Any

class AuditHelperSelectMatchOrders:
    """
    Helper para auditoría al seleccionar y emparejar órdenes de venta
    """
    
    @staticmethod
    def _log_auto_selection_audit(
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
                action_code='SALES_AUTO_MATCH_SELECTION',
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
                },
                status='SUCCESS'
            )


    @staticmethod
    def _log_selection_audit(
        purchase_order: PurchaseOrder,
        selection_summary: Dict[str, Any],
        user,
        request=None
    ) -> None:
        """Registra auditoría de selección manual exitosa"""
        
        if request:
            AuditService.log_action(
                request=request,
                action_code='SALES_MATCH_SELECTION',
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
            

    @staticmethod
    def _log_warning_audit(
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
            
    
    @staticmethod
    def _log_error_audit(
        purchase_order: PurchaseOrder,
        error_msg: str,
        user,
        request=None
    ) -> None:
        """Registra auditoría de error"""
        
        if request:
            AuditService.log_action(
                request=request,
                action_code='AUTO_MATCH_SELECTION',
                obj=purchase_order,
                details={
                    'order_number': purchase_order.order_number,
                    'error': error_msg,
                    'selected_by': user.email,
                    'operation': 'match_selection_error'
                },
                status='ERROR'
            )