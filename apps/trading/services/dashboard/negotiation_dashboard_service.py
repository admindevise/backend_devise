from django.db.models import Q, Exists, OuterRef
from django.utils import timezone
from datetime import timedelta
import pytz
from typing import Dict, Any, List
from apps.trading.models.core_models import PurchaseOrder, SalesOrder, Transaction

class NegotiationListService:
    """
    Servicio para obtener lista de órdenes categorizadas por estado
    """
    
    TIMELINE_DELTAS = {
        '1d': timedelta(days=1),
        '3d': timedelta(days=3),
        '1w': timedelta(weeks=1),
        '1m': timedelta(days=30),
    }
    
    BOGOTA_TZ = pytz.timezone('America/Bogota')
    
    def _serialize_datetime_bogota(self, dt):
        """Convierte datetime a zona horaria de Bogotá"""
        if not dt:
            return None
            
        if timezone.is_aware(dt):
            bogota_dt = dt.astimezone(self.BOGOTA_TZ)
        else:
            utc_dt = pytz.utc.localize(dt)
            bogota_dt = utc_dt.astimezone(self.BOGOTA_TZ)
        
        return {
            'full_datetime': bogota_dt.isoformat(),
            'date': bogota_dt.strftime('%Y-%m-%d'),
            'time': bogota_dt.strftime('%H:%M:%S'),
            'date_display': bogota_dt.strftime('%d/%m/%Y'),
            'time_display': bogota_dt.strftime('%H:%M')
        }
    
    def get_orders_by_status_category(
        self, 
        timeline: str = '1d', 
        fund_id: int = None, 
        user_id: int = None, 
        status_category: str = None
    ) -> Dict[str, Any]:
        """
        Obtiene órdenes categorizadas por estado:
        - 'open': Órdenes abiertas (PENDING, MATCHES_SELECTED, etc.)
        - 'closed': Órdenes que completaron transacciones
        - 'cancelled': Órdenes canceladas
        - 'all': Todas las órdenes
        """
        # Calcular rango de fechas
        end_date_utc = timezone.now()
        start_date_utc = end_date_utc - self.TIMELINE_DELTAS.get(timeline, timedelta(days=1))
        
        # Filtros base
        base_filter = Q(created_at__gte=start_date_utc, created_at__lte=end_date_utc)
        
        if fund_id:
            base_filter &= Q(fund_id=fund_id)
        
        # Obtener órdenes según categoría
        if status_category == 'open':
            return self._get_open_orders(base_filter, user_id, timeline)
        elif status_category == 'closed':
            return self._get_closed_orders(base_filter, user_id, timeline)
        elif status_category == 'cancelled':
            return self._get_cancelled_orders(base_filter, user_id, timeline)
        else:
            return self._get_all_orders_categorized(base_filter, user_id, timeline)
    
    def _get_open_orders(self, base_filter: Q, user_id: int, timeline: str) -> Dict[str, Any]:
        """Órdenes abiertas (pendientes, en proceso)"""
        # Estados considerados "abiertos"
        open_statuses = [
            'PENDING', 
            'MATCHES_SELECTED', 
            'PROCESSING_PAYMENT', 
            'PAID',
            'PARTIALLY_EXECUTED'
        ]
        
        open_filter = base_filter & Q(status__in=open_statuses)
        
        return self._get_orders_with_filter(open_filter, user_id, timeline, 'open')
    
    def _get_closed_orders(self, base_filter: Q, user_id: int, timeline: str) -> Dict[str, Any]:
        """
        Órdenes cerradas - que tienen al menos una transacción exitosa
        Usa Transaction model como fuente de verdad
        """
        # Filtro para órdenes que tienen transacciones
        purchase_orders_with_transactions = PurchaseOrder.objects.filter(
            base_filter,
            # Subquery para verificar que tiene transacciones
            Exists(
                Transaction.objects.filter(
                    purchase_order=OuterRef('pk')
                )
            )
        )
        
        sales_orders_with_transactions = SalesOrder.objects.filter(
            base_filter,
            # Subquery para verificar que tiene transacciones
            Exists(
                Transaction.objects.filter(
                    sales_order=OuterRef('pk')
                )
            )
        )
        
        # Aplicar filtro de usuario si se especifica
        if user_id:
            purchase_orders_with_transactions = purchase_orders_with_transactions.filter(
                supplier_user_id=user_id
            )
            sales_orders_with_transactions = sales_orders_with_transactions.filter(
                seller_user_id=user_id
            )
        
        # Obtener órdenes con sus transacciones
        orders_list = []
        
        # Purchase Orders cerradas
        for po in purchase_orders_with_transactions.select_related('fund', 'supplier_user'):
            # Obtener transacciones relacionadas
            transactions = Transaction.objects.filter(purchase_order=po).order_by('-created_at')
            
            datetime_data = self._serialize_datetime_bogota(po.created_at)
            
            # Calcular datos de cierre basados en transacciones
            total_units_traded = sum(t.units for t in transactions)
            total_amount_traded = sum(t.total_amount for t in transactions)
            last_transaction = transactions.first()
            
            orders_list.append({
                'order_number': po.order_number,
                'order_type': 'PURCHASE_ORDER',
                'status': po.status,
                'original_status': po.status,
                'closure_status': 'COMPLETED_WITH_TRANSACTIONS',
                'price_per_unit': float(po.price_per_unit),
                
                # Datos de tiempo
                'created_at_full': datetime_data['full_datetime'],
                'created_date': datetime_data['date'],
                'created_time': datetime_data['time'],
                'created_date_display': datetime_data['date_display'],
                'created_time_display': datetime_data['time_display'],
                
                # Datos de cierre/transacción
                'closed_at': self._serialize_datetime_bogota(last_transaction.created_at) if last_transaction else None,
                'transactions_count': len(transactions),
                'total_units_traded': total_units_traded,
                'total_amount_traded': float(total_amount_traded),
                'last_transaction_id': str(last_transaction.id) if last_transaction else None,
                
                # Datos básicos
                'fund_name': po.fund.name,
                'user_email': po.supplier_user.email,
                'original_units': po.units,
                'original_total_amount': float(po.total_amount),
                
                # Indicadores de estado
                'is_fully_executed': po.status == 'FULLY_EXECUTED',
                'is_partially_executed': po.status == 'PARTIALLY_EXECUTED',
                'execution_percentage': round((total_units_traded / po.units) * 100, 2) if po.units > 0 else 0
            })
        
        # Sales Orders cerradas
        for so in sales_orders_with_transactions.select_related('fund', 'seller_user'):
            transactions = Transaction.objects.filter(sales_order=so).order_by('-created_at')
            
            datetime_data = self._serialize_datetime_bogota(so.created_at)
            
            total_units_traded = sum(t.units for t in transactions)
            total_amount_traded = sum(t.total_amount for t in transactions)
            last_transaction = transactions.first()
            
            orders_list.append({
                'order_number': so.order_number,
                'order_type': 'SALES_ORDER',
                'status': so.status,
                'original_status': so.status,
                'closure_status': 'COMPLETED_WITH_TRANSACTIONS',
                'price_per_unit': float(so.price_per_unit),
                
                'created_at_full': datetime_data['full_datetime'],
                'created_date': datetime_data['date'],
                'created_time': datetime_data['time'],
                'created_date_display': datetime_data['date_display'],
                'created_time_display': datetime_data['time_display'],
                
                'closed_at': self._serialize_datetime_bogota(last_transaction.created_at) if last_transaction else None,
                'transactions_count': len(transactions),
                'total_units_traded': total_units_traded,
                'total_amount_traded': float(total_amount_traded),
                'last_transaction_id': str(last_transaction.id) if last_transaction else None,
                
                'fund_name': so.fund.name,
                'user_email': so.seller_user.email,
                'original_units': so.units,
                'original_total_amount': float(so.total_amount),
                
                'is_fully_executed': so.status == 'FULLY_EXECUTED',
                'is_partially_executed': so.status == 'PARTIALLY_EXECUTED',
                'execution_percentage': round((total_units_traded / so.units) * 100, 2) if so.units > 0 else 0
            })
        
        # Ordenar por fecha de última transacción
        orders_list.sort(key=lambda x: x['closed_at']['full_datetime'] if x['closed_at'] else '', reverse=True)
        
        return self._build_response(orders_list, timeline, 'closed')
    
    def _get_cancelled_orders(self, base_filter: Q, user_id: int, timeline: str) -> Dict[str, Any]:
        """Órdenes canceladas"""
        cancelled_statuses = ['CANCELLED', 'EXPIRED']
        cancelled_filter = base_filter & Q(status__in=cancelled_statuses)
        
        return self._get_orders_with_filter(cancelled_filter, user_id, timeline, 'cancelled')
    
    def _get_all_orders_categorized(self, base_filter: Q, user_id: int, timeline: str) -> Dict[str, Any]:
        """Todas las órdenes categorizadas"""
        open_orders = self._get_open_orders(base_filter, user_id, timeline)
        closed_orders = self._get_closed_orders(base_filter, user_id, timeline)
        cancelled_orders = self._get_cancelled_orders(base_filter, user_id, timeline)
        
        # Combinar todas las órdenes
        all_orders = []
        all_orders.extend(open_orders['orders'])
        all_orders.extend(closed_orders['orders'])
        all_orders.extend(cancelled_orders['orders'])
        
        # Ordenar por fecha de creación
        all_orders.sort(key=lambda x: x['created_at_full'], reverse=True)
        
        return {
            **self._build_response(all_orders, timeline, 'all'),
            'categorized_summary': {
                'open_orders': len(open_orders['orders']),
                'closed_orders': len(closed_orders['orders']),
                'cancelled_orders': len(cancelled_orders['orders']),
                'total_orders': len(all_orders)
            }
        }
    
    def _get_orders_with_filter(self, filter_q: Q, user_id: int, timeline: str, category: str) -> Dict[str, Any]:
        """Helper para obtener órdenes con filtro específico"""
        orders_list = []
        
        # Purchase Orders
        po_filter = filter_q.copy()
        if user_id:
            po_filter &= Q(supplier_user_id=user_id)
        
        purchase_orders = PurchaseOrder.objects.filter(po_filter).select_related(
            'fund', 'supplier_user'
        ).order_by('-created_at')
        
        for po in purchase_orders:
            datetime_data = self._serialize_datetime_bogota(po.created_at)
            
            order_data = {
                'order_number': po.order_number,
                'order_type': 'PURCHASE_ORDER',
                'status': po.status,
                'price_per_unit': float(po.price_per_unit),
                
                'created_at_full': datetime_data['full_datetime'],
                'created_date': datetime_data['date'],
                'created_time': datetime_data['time'],
                'created_date_display': datetime_data['date_display'],
                'created_time_display': datetime_data['time_display'],
                
                'fund_name': po.fund.name,
                'user_email': po.supplier_user.email,
                'units': po.units,
                'total_amount': float(po.total_amount)
            }
            
            # Agregar datos específicos por categoría
            if category == 'cancelled':
                # Manejar tanto cancelación como expiración
                if po.status == 'CANCELLED' and hasattr(po, 'cancelled_at') and po.cancelled_at:
                    cancelled_data = self._serialize_datetime_bogota(po.cancelled_at)
                    order_data['cancelled_at'] = cancelled_data
                    order_data['cancellation_reason'] = 'MANUALLY_CANCELLED'
                elif po.status == 'EXPIRED' and hasattr(po, 'expiration_date') and po.expiration_date:
                    expired_data = self._serialize_datetime_bogota(po.expiration_date)
                    order_data['cancelled_at'] = expired_data  # Usar mismo campo para consistencia
                    order_data['cancellation_reason'] = 'EXPIRED'
                else:
                    # Fallback si no hay fecha específica
                    order_data['cancelled_at'] = None
                    order_data['cancellation_reason'] = po.status
            
            orders_list.append(order_data)
        
        # Sales Orders
        so_filter = filter_q.copy()
        if user_id:
            so_filter &= Q(seller_user_id=user_id)
        
        sales_orders = SalesOrder.objects.filter(so_filter).select_related(
            'fund', 'seller_user'
        ).order_by('-created_at')
        
        for so in sales_orders:
            datetime_data = self._serialize_datetime_bogota(so.created_at)
            
            order_data = {
                'order_number': so.order_number,
                'order_type': 'SALES_ORDER',
                'status': so.status,
                'price_per_unit': float(so.price_per_unit),
                
                'created_at_full': datetime_data['full_datetime'],
                'created_date': datetime_data['date'],
                'created_time': datetime_data['time'],
                'created_date_display': datetime_data['date_display'],
                'created_time_display': datetime_data['time_display'],
                
                'fund_name': so.fund.name,
                'user_email': so.seller_user.email,
                'units': so.units,
                'total_amount': float(so.total_amount)
            }
            
            if category == 'cancelled':
                # Manejar tanto cancelación como expiración para Sales Orders
                if so.status == 'CANCELLED' and hasattr(so, 'cancelled_at') and so.cancelled_at:
                    cancelled_data = self._serialize_datetime_bogota(so.cancelled_at)
                    order_data['cancelled_at'] = cancelled_data
                    order_data['cancellation_reason'] = 'MANUALLY_CANCELLED'
                elif so.status == 'EXPIRED' and hasattr(so, 'expiration_date') and so.expiration_date:
                    expired_data = self._serialize_datetime_bogota(so.expiration_date)
                    order_data['cancelled_at'] = expired_data
                    order_data['cancellation_reason'] = 'EXPIRED'
                else:
                    order_data['cancelled_at'] = None
                    order_data['cancellation_reason'] = so.status
            
            orders_list.append(order_data)
        
        # Ordenar por fecha de creación
        orders_list.sort(key=lambda x: x['created_at_full'], reverse=True)
        
        return self._build_response(orders_list, timeline, category)
    
    def _build_response(self, orders_list: List[Dict], timeline: str, category: str) -> Dict[str, Any]:
        """Construye la respuesta estándar"""
        end_date_utc = timezone.now()
        start_date_utc = end_date_utc - self.TIMELINE_DELTAS.get(timeline, timedelta(days=1))
        
        period_start = self._serialize_datetime_bogota(start_date_utc)
        period_end = self._serialize_datetime_bogota(end_date_utc)
        
        return {
            'period': {
                'start_full': period_start['full_datetime'],
                'start_date': period_start['date'],
                'start_time': period_start['time'],
                'end_full': period_end['full_datetime'],
                'end_date': period_end['date'],
                'end_time': period_end['time'],
                'timeline': timeline,
                'timezone': 'America/Bogota'
            },
            'category': category,
            'orders': orders_list,
            'total_orders': len(orders_list),
            'summary_by_status': self._get_status_summary(orders_list),
            'summary_by_type': self._get_type_summary(orders_list)
        }
    
    def _get_status_summary(self, orders_list: List[Dict]) -> Dict[str, int]:
        """Resumen por estado"""
        status_count = {}
        for order in orders_list:
            status = order['status']
            status_count[status] = status_count.get(status, 0) + 1
        return status_count
    
    def _get_type_summary(self, orders_list: List[Dict]) -> Dict[str, int]:
        """Resumen por tipo de orden"""
        type_count = {}
        for order in orders_list:
            order_type = order['order_type']
            type_count[order_type] = type_count.get(order_type, 0) + 1
        return type_count
    
    # ========================================
    # MÉTODO DE COMPATIBILIDAD
    # ========================================
    
    def get_orders_list(self, timeline: str = '1d', fund_id: int = None, user_id: int = None, status: str = None) -> Dict[str, Any]:
        """
        Método de compatibilidad que mantiene la interfaz original
        pero ahora soporta filtrar por categoría de estado
        """
        # Mapear status a categorías si es necesario
        if status in ['PENDING', 'MATCHES_SELECTED', 'PROCESSING_PAYMENT', 'PAID', 'PARTIALLY_EXECUTED']:
            return self.get_orders_by_status_category(timeline, fund_id, user_id, 'open')
        elif status in ['CANCELLED', 'EXPIRED']:
            return self.get_orders_by_status_category(timeline, fund_id, user_id, 'cancelled')
        elif status == 'FULLY_EXECUTED':
            return self.get_orders_by_status_category(timeline, fund_id, user_id, 'closed')
        else:
            return self.get_orders_by_status_category(timeline, fund_id, user_id, 'all')