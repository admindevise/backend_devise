from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.trading.services.dashboard.negotiation_dashboard_service import NegotiationListService

class NegotiationOrdersListAPIView(APIView):
    """
    API para obtener órdenes categorizadas por estado
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.list_service = NegotiationListService()
    
    def get(self, request):
        """
        GET /api/trading/negotiations/orders/
        
        Query params:
        - timeline: '1d', '3d', '1w', '1m' (default: '1d')
        - fund_id: int (optional)
        - status_category: 'open', 'closed', 'cancelled', 'all' (default: 'all')
        - limit: int (default: 100, max: 500)
        """
        try:
            # Parámetros
            timeline = request.query_params.get('timeline', '1d')
            fund_id = request.query_params.get('fund_id')
            status_category = request.query_params.get('status_category', 'all')
            limit = min(int(request.query_params.get('limit', 100)), 500)
            
            # Validaciones
            if timeline not in ['1d', '3d', '1w', '1m']:
                return Response({
                    'error': 'Timeline inválido. Opciones: 1d, 3d, 1w, 1m'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if status_category not in ['open', 'closed', 'cancelled', 'all']:
                return Response({
                    'error': 'status_category inválido. Opciones: open, closed, cancelled, all'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Preparar filtros
            filters = {}
            if fund_id:
                try:
                    filters['fund_id'] = int(fund_id)
                except ValueError:
                    return Response({
                        'error': 'fund_id debe ser un número entero'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Añadir user_id si no es admin
            if not request.user.is_staff:
                filters['user_id'] = request.user.id
            
            # Obtener datos
            data = self.list_service.get_orders_by_status_category(
                timeline=timeline,
                status_category=status_category,
                **filters
            )
            
            # Aplicar límite
            if limit < len(data['orders']):
                data['orders'] = data['orders'][:limit]
                data['limited_results'] = True
                data['total_available'] = data['total_orders']
                data['total_orders'] = limit
            
            return Response({
                'success': True,
                'data': data,
                'filters_applied': {
                    'timeline': timeline,
                    'fund_id': fund_id,
                    'status_category': status_category,
                    'limit': limit
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NegotiationStatusOptionsAPIView(APIView):
    """
    API para obtener opciones disponibles
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/trading/negotiations/status-options/
        """
        from apps.trading.models.core_models import PurchaseOrder, SalesOrder
        
        return Response({
            'success': True,
            'data': {
                'timeline_options': [
                    {'value': '1d', 'label': '1 Día'},
                    {'value': '3d', 'label': '3 Días'},
                    {'value': '1w', 'label': '1 Semana'},
                    {'value': '1m', 'label': '1 Mes'},
                ],
                'status_options': {
                    'purchase_order': [
                        {'value': choice[0], 'label': choice[1]} 
                        for choice in PurchaseOrder.PurchaseOrderStatus.choices
                    ],
                    'sales_order': [
                        {'value': choice[0], 'label': choice[1]} 
                        for choice in SalesOrder.SalesOrderStatus.choices
                    ]
                },
                'order_types': [
                    {'value': 'PURCHASE_ORDER', 'label': 'Órdenes de Compra'},
                    {'value': 'SALES_ORDER', 'label': 'Órdenes de Venta'},
                ]
            }
        })