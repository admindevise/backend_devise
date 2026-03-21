from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.trading.views.trading_views import (
    PurchaseOrderViewSet,
    SalesOrderViewSet,
    TransactionViewSet,
    ActiveOrdersAPIView,
    CleanupExpiredReservationsAPIView,
    OrdersListAPIView
)

from apps.trading.views.find_matching_views import FindMatchesAPIView
from apps.trading.views.payment_execution_views import ExecutePaymentAPIView

from apps.trading.views.contract_views import OrderContractViewSet

from apps.trading.views.permission_views import TradingPermissionViewSet

from apps.trading.views.selection_management_views import (
    MatchSelectionViewSet,
    UserSelectionStatsAPIView
)

from apps.trading.views.negotiation_dashboard_views import NegotiationDashboardViewSet

router = DefaultRouter()
router.register(
    r'fund/(?P<fund_id>[^/.]+)/purchase-orders',
    PurchaseOrderViewSet,
    basename='purchase-order'
)
router.register(
    r'fund/(?P<fund_id>[^/.]+)/sales-orders',
    SalesOrderViewSet,
    basename='sales-order'
)
router.register(
    r'fund/(?P<fund_id>[^/.]+)/transactions',
    TransactionViewSet,
    basename='transaction'
)
router.register(
    r'fund/(?P<fund_id>[^/.]+)/contracts',
    OrderContractViewSet,
    basename='order-contract'
)
router.register(
    r'fund/(?P<fund_id>[^/.]+)/selections',
    MatchSelectionViewSet,
    basename='match-selection'
)
router.register(
    r'fund/(?P<fund_id>[^/.]+)/permissions',
    TradingPermissionViewSet,
    basename='trading-permissions'
)
router.register(
    r'fund/(?P<fund_id>[^/.]+)/negotiation-dashboard',
    NegotiationDashboardViewSet,
    basename='negotiation-dashboard'
)


urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Matching URLs (existentes)
    path("fund/<int:fund_id>/find-matches/", FindMatchesAPIView.as_view(), name="find-matches"),
    
    # Utility URLs
    path('fund/<int:fund_id>/active-orders/', ActiveOrdersAPIView.as_view(), name='active-orders'),
    
    path('fund/<int:fund_id>/cleanup-reservations/', CleanupExpiredReservationsAPIView.as_view(), name='cleanup-reservations'),

    # Estadísticas
    path('fund/<int:fund_id>/my-selection-stats/', UserSelectionStatsAPIView.as_view(), name='user_selection_stats'),
    
    path('fund/<int:fund_id>/payments/execute/<uuid:order_id>/', ExecutePaymentAPIView.as_view(), name='execute-payment'),
    
    # Listado unificado de órdenes (compra + venta)
    path('fi/<int:fi_id>/orders/', OrdersListAPIView.as_view(), name='get-orders'),
]