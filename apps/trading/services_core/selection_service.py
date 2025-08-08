from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Any
from decimal import Decimal

from apps.trading.models.selection_models import MatchSelection, MatchSelectionItem
from apps.trading.models.core_models import PurchaseOrder, SalesOrder

from apps.trading.order_matching import OrderMatch

class SelectionServiceError(Exception):
    """Excepción personalizada para errores en SelectionService"""
    pass

class MatchSelectionService:
    """Servicio dedicado para manejo de selecciones de matches"""
    
    def __init__(self):
        self.matcher = OrderMatch()
    
    @transaction.atomic
    def create_selection(
        self,
        purchase_order: PurchaseOrder,
        sales_order: SalesOrder,
        validated_matches: List[Dict],
        user,
        expires_in_minutes: int = 15
    ) -> MatchSelection:
        """Crea una nueva seleccion de matches"""

        # 1. Limpiar seleccion anterior si existe
        self._clean_existing_selection(purchase_order, sales_order)
        
        # 2. Obtener matches disponibles
        available_matches = self._get_available_matches(purchase_order)    
        
        # 3. Calcular totales
        total_amount = sum(Decimal(str(match['total_amount'])) for match in validated_matches)
        total_units = sum(match['units'] for match in validated_matches)
        total_savings = sum(Decimal(str(match.get('buyer_savings', 0))) for match in validated_matches)
        
        # 4. Crear la selección principal
        selection = MatchSelection.objects.create(
            purchase_order=purchase_order,
            sales_order=sales_order,
            total_amount=total_amount,
            total_units=total_units,
            expected_savings=total_savings,
            expires_at=timezone.now() + timezone.timedelta(minutes=expires_in_minutes),
            created_by=user,
            metadata={
                'validated_matches': validated_matches,
                'original_matches_count': len(validated_matches)
            }
        )
        
        # 5. Crear items individuales
        for match in validated_matches:
            sales_order = SalesOrder.objects.get(id=match['sales_order_id'])
            purchase_order = PurchaseOrder.objects.get(id=match['purchase_order_id'])
            
            MatchSelectionItem.objects.create(
                selection=selection,
                sales_order=sales_order,
                purchase_order=purchase_order,
                units=match['units'],
                price_per_unit=Decimal(str(match['price_per_unit'])),
                buyer_savings=Decimal(str(match.get('buyer_savings', 0))),
                seller_gain=Decimal(str(match.get('seller_gain', 0))),
                metadata={
                    'match_quality': match.get('quality_score'),
                    'original_match_data': match
                }
            )
        
        # 6. Actualizar estado de purchase order
        purchase_order.status = PurchaseOrder.PurchaseOrderStatus.MATCHES_SELECTED
        purchase_order.matched_at = timezone.now()
        
        # 7. Mantener metadata como backup/cache
        purchase_order.metadata = purchase_order.metadata or {}
        purchase_order.metadata.update({
            'selection_id': selection.id,
            'selection_summary': {
                'total_amount': str(total_amount),
                'expires_at': selection.expires_at.isoformat(),
                'items_count': len(validated_matches)
            }
        })
        purchase_order.save(update_fields=['status', 'matched_at', 'metadata'])
        
        return selection
    
    
    # =========================================
    # Métodos privados
    # =========================================
    
    def get_active_selection(self, purchase_order: PurchaseOrder) -> MatchSelection:
        """Obtiene la selección activa de una orden"""
        
        try:
            selection = purchase_order.match_selection
            if selection.is_expired:
                self._mark_selection_as_expired(selection)
                return None
            return selection
        except MatchSelection.DoesNotExist:
            return None
    
    def check_and_clean_expired_selections(self) -> Dict[str, int]:
        """Limpia todas las selecciones expiradas del sistema"""
        
        expired_selections = MatchSelection.objects.filter(
            expires_at__lt=timezone.now(),
            status='ACTIVE'
        ).select_related('purchase_order')
        
        cleaned_count = 0
        for selection in expired_selections:
            self._mark_selection_as_expired(selection)
            cleaned_count += 1
        
        return {
            'cleaned_selections': cleaned_count,
            'cleaned_at': timezone.now().isoformat()
        }
        
    
    def _get_available_matches(self, purchase_order: PurchaseOrder) -> List[Dict[str, Any]]:
        """Obtiene matches disponibles para la orden"""
        
        try:
            available_matches = self.matcher.find_matches_for_order(purchase_order)
            
            if not available_matches:
                raise SelectionServiceError('No hay matches disponibles para esta orden')
            
            return available_matches
            
        except Exception as e:
            raise SelectionServiceError(f'Error obteniendo matches disponibles: {str(e)}')
        
    @transaction.atomic
    def _clean_existing_selection(self, purchase_order: PurchaseOrder) -> None:
        """Limpia selección existente si hay una"""
        
        try:
            existing_selection = purchase_order.match_selection
            existing_selection.delete()  # Cascade elimina items
        except MatchSelection.DoesNotExist:
            pass
    
    @transaction.atomic
    def _mark_selection_as_expired(self, selection: MatchSelection) -> None:
        """Marca una selección como expirada y limpia el estado"""
        
        selection.status = 'EXPIRED'
        selection.save(update_fields=['status'])
        
        # Limpiar estado de purchase order
        purchase_order = selection.purchase_order
        purchase_order.status = 'PENDING'
        purchase_order.matched_at = None
        purchase_order.metadata = {
            'selection_expired_at': timezone.now().isoformat(),
            'expired_selection_id': selection.id
        }
        purchase_order.save(update_fields=['status', 'matched_at', 'metadata'])