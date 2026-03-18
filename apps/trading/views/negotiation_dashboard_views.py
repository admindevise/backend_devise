from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from apps.trading.services.dashboard.negotiation_dashboard_service import NegotiationListService
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.fund.models.core import Fund
from apps.utils.views.global_utils_views import validate_entity_exists


class NegotiationDashboardViewSet(viewsets.GenericViewSet):
    """
    ViewSet para dashboard de negociación:
    - orders
    - status_options
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        fund_id = self.kwargs.get('fund_id')
        if fund_id:
            validate_entity_exists(Fund, 'Fideicomiso', fund_id)
        super().initial(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='orders')
    def orders(self, request, **kwargs):
        """
        GET /.../negotiations/orders/?timeline=1d&status_category=all&limit=100
        """
        try:
            fund_id_from_path = self.kwargs.get('fund_id')
            if fund_id_from_path:
                validate_entity_exists(Fund, 'Fideicomiso', fund_id_from_path)

            timeline = request.query_params.get('timeline', '1d')
            fund_id = request.query_params.get('fund_id', fund_id_from_path)
            status_category = request.query_params.get('status_category', 'all')
            limit = min(int(request.query_params.get('limit', 100)), 500)

            if timeline not in ['1d', '3d', '1w', '1m']:
                return Response(
                    {'error': 'Timeline inválido. Opciones: 1d, 3d, 1w, 1m'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if status_category not in ['open', 'closed', 'cancelled', 'all']:
                return Response(
                    {'error': 'status_category inválido. Opciones: open, closed, cancelled, all'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            filters = {}
            if fund_id:
                try:
                    filters['fund_id'] = int(fund_id)
                except ValueError:
                    return Response(
                        {'error': 'fund_id debe ser un número entero'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if not request.user.is_staff:
                filters['user_id'] = request.user.id

            service = NegotiationListService()
            data = service.get_orders_by_status_category(
                timeline=timeline,
                status_category=status_category,
                **filters
            )

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
            return Response(
                {'success': False, 'error': f'Error interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='status-options')
    def status_options(self, request, **kwargs):
        """
        GET /.../negotiations/status-options/
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
                        {'value': c[0], 'label': c[1]}
                        for c in PurchaseOrder.PurchaseOrderStatus.choices
                    ],
                    'sales_order': [
                        {'value': c[0], 'label': c[1]}
                        for c in SalesOrder.SalesOrderStatus.choices
                    ]
                },
                'order_types': [
                    {'value': 'PURCHASE_ORDER', 'label': 'Órdenes de Compra'},
                    {'value': 'SALES_ORDER', 'label': 'Órdenes de Venta'},
                ]
            }
        })