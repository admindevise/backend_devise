from django.db.models import Q, Count
from django.contrib.auth.models import User
from apps.trading.models import PurchaseOrder, SalesOrder

class OrderQueryService:
    """
    Servicio para consultas complejas de órdenes
    Separación de responsabilidades: lógica de negocio fuera de views
    """
    
    def __init__(self):
        self.active_statuses = ['PENDING', 'PAID', 'MATCHES_SELECTED', 'MATCHED']
    
    def get_active_orders(self, requesting_user, **filters):
        """
        Obtiene órdenes activas basado en los filtros proporcionados
        
        Args:
            requesting_user: Usuario que hace la consulta
            **filters: Filtros adicionales (user_id, all_orders, date_range, etc.)
        
        Returns:
            dict: Resultado estructurado con órdenes y metadatos
        """
        try:
            # Determinar estrategia de filtrado
            filter_strategy = self._determine_filter_strategy(requesting_user, **filters)
            
            # Obtener órdenes según la estrategia
            purchase_orders = self._get_purchase_orders(filter_strategy)
            sales_orders = self._get_sales_orders(filter_strategy)
            
            # Aplicar filtros adicionales
            purchase_orders = self._apply_additional_filters(purchase_orders, **filters)
            sales_orders = self._apply_additional_filters(sales_orders, **filters)
            
            # Compilar resultado
            result = {
                'purchase_orders': purchase_orders,
                'sales_orders': sales_orders,
                'metadata': {
                    'total_count': purchase_orders.count() + sales_orders.count(),
                    'purchase_count': purchase_orders.count(),
                    'sales_count': sales_orders.count(),
                    'filter_strategy': filter_strategy['type'],
                    'applied_filters': filter_strategy['filters']
                }
            }
            
            return result
            
        except Exception as e:
            raise Exception(f"Error en OrderQueryService: {str(e)}")
    
    def _determine_filter_strategy(self, requesting_user, **filters):
        """Determina la estrategia de filtrado basada en permisos y parámetros"""
        
        if filters.get('all_orders') and requesting_user.is_staff:
            return {
                'type': 'ALL_ORDERS',
                'filters': {'status__in': self.active_statuses}
            }
        
        elif filters.get('user_id') and requesting_user.is_staff:
            target_user_id = filters['user_id']
            return {
                'type': 'SPECIFIC_USER',
                'filters': {
                    'user_id': target_user_id,
                    'status__in': self.active_statuses
                }
            }
        
        else:
            return {
                'type': 'USER_OWNED',
                'filters': {
                    'user': requesting_user.id,
                    'status__in': self.active_statuses
                }
            }
    
    def _get_purchase_orders(self, filter_strategy):
        """Obtiene órdenes de compra según la estrategia"""
        queryset = PurchaseOrder.objects.all()
        
        if filter_strategy['type'] == 'ALL_ORDERS':
            return queryset.filter(status__in=filter_strategy['filters']['status__in'])
        
        elif filter_strategy['type'] == 'SPECIFIC_USER':
            user_id = filter_strategy['filters']['user_id']
            return queryset.filter(
                Q(supplier_user_id=user_id) | Q(created_by_id=user_id),
                status__in=filter_strategy['filters']['status__in']
            )
        
        else:  # USER_OWNED
            user = filter_strategy['filters']['user']
            return queryset.filter(
                Q(supplier_user=user) | Q(created_by=user),
                status__in=filter_strategy['filters']['status__in']
            )
    
    def _get_sales_orders(self, filter_strategy):
        """Obtiene órdenes de venta según la estrategia"""
        queryset = SalesOrder.objects.all()
        
        if filter_strategy['type'] == 'ALL_ORDERS':
            return queryset.filter(status__in=filter_strategy['filters']['status__in'])
        
        elif filter_strategy['type'] == 'SPECIFIC_USER':
            user_id = filter_strategy['filters']['user_id']
            return queryset.filter(
                Q(seller_user_id=user_id) | Q(created_by_id=user_id),
                status__in=filter_strategy['filters']['status__in']
            )
        
        else:  # USER_OWNED
            user = filter_strategy['filters']['user']
            return queryset.filter(
                Q(seller_user=user) | Q(created_by=user),
                status__in=filter_strategy['filters']['status__in']
            )
    
    def _apply_additional_filters(self, queryset, **filters):
        """Aplica filtros adicionales al queryset"""
        # Filtros de fecha
        if filters.get('date_range'):
            queryset = self._apply_date_filters(queryset, filters['date_range'])
        
        # Filtro por estado específico
        if filters.get('status'):
            queryset = self._filter_by_status(queryset, filters['status'])
        
        # Filtro por fondo
        if filters.get('fund_id'):
            queryset = self._filter_by_fund(queryset, filters['fund_id'])
            
        # Filtro por rango de precios
        if filters.get('price_range'):
            queryset = self._filter_by_price_range(queryset, filters['price_range'])
        
        return queryset
    
    def _apply_date_filters(self, queryset, date_range):
        """Aplica filtros de fecha al queryset"""
        if date_range.get('start_date'):
            queryset = queryset.filter(created_at__gte=date_range['start_date'])
        if date_range.get('end_date'):
            queryset = queryset.filter(created_at__lte=date_range['end_date'])
        return queryset
    
    def _filter_by_status(self, queryset, status):
        """Aplica filtro por estado al queryset"""
        if status:
            return queryset.filter(status=status)
        return queryset
    
    def _filter_by_fund(self, queryset, fund_id):
        """Aplica filtro por fondo al queryset"""
        if fund_id:
            return queryset.filter(fund_id=fund_id)
        return queryset
    
    def _filter_by_price_range(self, queryset, price_range):
        """Aplica filtro por rango de precios al queryset con validación"""
        
        min_price = price_range.get('min_price')
        max_price = price_range.get('max_price')
        exact_price = price_range.get('exact_price')
        
        # Validar que min_price no sea mayor que max_price
        if min_price and max_price and min_price > max_price:
            raise ValueError("El precio mínimo no puede ser mayor que el precio máximo")
        
        # Aplicar filtros
        if min_price:
            queryset = queryset.filter(price_per_unit__gte=min_price)
        
        if max_price:
            queryset = queryset.filter(price_per_unit__lte=max_price)
        
        if exact_price:
            # Si se especifica precio exacto, ignorar min/max
            queryset = queryset.filter(price_per_unit=exact_price)
        
        return queryset
    
    def get_order_statistics(self, requesting_user, **filters):
        """
        Obtiene estadísticas de órdenes para dashboards
        """
        try:
            # Usar la misma lógica de filtrado
            result = self.get_active_orders(requesting_user, **filters)
            
            # Calcular estadísticas adicionales
            purchase_orders = result['purchase_orders']
            sales_orders = result['sales_orders']
            
            # Distribución por estado
            purchase_status_dist = purchase_orders.values('status').annotate(count=Count('id'))
            sales_status_dist = sales_orders.values('status').annotate(count=Count('id'))
            
            # Estadísticas por fondo
            purchase_fund_dist = purchase_orders.values('fund__name').annotate(count=Count('id'))
            sales_fund_dist = sales_orders.values('fund__name').annotate(count=Count('id'))
            
            return {
                'basic_stats': result['metadata'],
                'status_distribution': {
                    'purchase_orders': list(purchase_status_dist),
                    'sales_orders': list(sales_status_dist)
                },
                'fund_distribution': {
                    'purchase_orders': list(purchase_fund_dist),
                    'sales_orders': list(sales_fund_dist)
                }
            }
            
        except Exception as e:
            raise Exception(f"Error obteniendo estadísticas: {str(e)}")