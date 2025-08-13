from typing import Dict, List, Any, Union
from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from .purchase_selection_service import PurchaseMatchSelectionService
from .sales_selection_service import SalesMatchSelectionService
from .match_selection_core import SelectionServiceError

class MatchSelectionService:
    """
    Servicio unificado que orquesta la selección de matches
    Delega a servicios específicos según el tipo de orden
    """
    
    def __init__(self):
        self.purchase_service = PurchaseMatchSelectionService()
        self.sales_service = SalesMatchSelectionService()
    
    # ========================================
    # MÉTODOS UNIFICADOS
    # ========================================
    
    def process_manual_selection(
        self,
        order: Union[PurchaseOrder, SalesOrder],
        selected_matches: List[Dict[str, Any]],
        user,
        request=None
    ) -> Dict[str, Any]:
        """
        Procesa selección manual para cualquier tipo de orden
        """
        if isinstance(order, PurchaseOrder):
            return self.purchase_service.process_manual_selection(
                order, selected_matches, user, request
            )
        elif isinstance(order, SalesOrder):
            return self.sales_service.process_manual_selection(
                order, selected_matches, user, request
            )
        else:
            raise SelectionServiceError("Tipo de orden no soportado")
    
    def process_auto_selection(
        self,
        order: Union[PurchaseOrder, SalesOrder],
        user,
        force_partial=False,
        request=None
    ) -> Dict[str, Any]:
        """
        Procesa selección automática para cualquier tipo de orden
        """
        if isinstance(order, PurchaseOrder):
            return self.purchase_service.process_auto_selection(
                order, user, force_partial, request
            )
        elif isinstance(order, SalesOrder):
            return self.sales_service.process_auto_selection(
                order, user, force_partial, request
            )
        else:
            raise SelectionServiceError("Tipo de orden no soportado")
    
    def get_active_selection(self, order: Union[PurchaseOrder, SalesOrder]):
        """Obtiene la selección activa para cualquier tipo de orden"""
        if isinstance(order, PurchaseOrder):
            return self.purchase_service.get_active_selection(order)
        elif isinstance(order, SalesOrder):
            return self.sales_service.get_active_selection(order)
        else:
            raise SelectionServiceError("Tipo de orden no soportado")
    
    def check_and_clean_expired_selections(self) -> Dict[str, int]:
        """Limpia selecciones expiradas de ambos tipos"""
        purchase_results = self.purchase_service.check_and_clean_expired_selections()
        sales_results = self.sales_service.check_and_clean_expired_selections()
        
        return {
            'total_cleaned_selections': purchase_results['cleaned_selections'] + sales_results['cleaned_selections'],
            'purchase_selections_cleaned': purchase_results['cleaned_selections'],
            'sales_selections_cleaned': sales_results['cleaned_selections'],
            'cleaned_at': purchase_results['cleaned_at']
        }
    
    # ========================================
    # MÉTODOS ESPECÍFICOS POR TIPO
    # ========================================
    
    # Para mantener compatibilidad con código existente
    def process_match_selection(
        self,
        purchase_order: PurchaseOrder,
        selected_matches: List[Dict[str, Any]],
        user,
        request=None
    ) -> Dict[str, Any]:
        """Método específico para órdenes de compra (compatibilidad)"""
        return self.purchase_service.process_manual_selection(
            purchase_order, selected_matches, user, request
        )
    
    def process_auto_match_selection(
        self,
        purchase_order: PurchaseOrder,
        user,
        force_partial=False,
        request=None
    ) -> Dict[str, Any]:
        """Método específico para selección automática de compra (compatibilidad)"""
        return self.purchase_service.process_auto_selection(
            purchase_order, user, force_partial, request
        )
    
    def process_sales_match_selection(
        self,
        sales_order: SalesOrder,
        selected_matches: List[Dict[str, Any]],
        user,
        request=None
    ) -> Dict[str, Any]:
        """Método específico para órdenes de venta"""
        return self.sales_service.process_manual_selection(
            sales_order, selected_matches, user, request
        )
    
    def process_auto_sales_match_selection(
        self,
        sales_order: SalesOrder,
        user,
        force_partial=False,
        request=None
    ) -> Dict[str, Any]:
        """Método específico para selección automática de venta"""
        return self.sales_service.process_auto_selection(
            sales_order, user, force_partial, request
        )