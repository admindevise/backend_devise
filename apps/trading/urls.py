from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.trading.views.trading_views import (
    PurchaseOrderViewSet,
    SalesOrderViewSet,
    TransactionViewSet,
    ActiveOrdersAPIView,
    cleanup_expired_reservations,
    get_orders
)

from apps.trading.views.find_matching_views import find_matches
from apps.trading.views.payment_execution_views import (
    execute_payment
    )

from apps.trading.views.contract_views import list_pending_contracts, approve_contract, OrderContractListView

from apps.trading.views.permission_views import (
    grant_trading_permission,
    list_user_permissions
)

from apps.trading.views.selection_management_views import (
    MatchSelectionViewSet,
    UserSelectionStatsAPIView,
    create_match_selection,
    validate_selection_capability,
    cancel_selection,
)

from apps.trading.views.negotiation_dashboard_views import (
    NegotiationOrdersListAPIView,
    NegotiationStatusOptionsAPIView
)

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
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(
    r'fund/(?P<fund_id>[^/.]+)/contracts',
    OrderContractListView,
    basename='order-contract'
)
router.register(r'selections', MatchSelectionViewSet, basename='matchselection')


urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Matching URLs (existentes)
    path('search-matches/', find_matches, name='find-matches'),
    
    # Utility URLs
    path('active-orders/', ActiveOrdersAPIView.as_view(), name='active-orders'),
    
    path('cleanup-reservations/', cleanup_expired_reservations, name='cleanup-reservations'),
    
    # Contract URLs
    path('fund/<int:fund_id>/contracts-pending/', list_pending_contracts, name='list-pending-contracts'),
    path('fund/<int:fund_id>/contracts-approve/<int:contract_id>/', approve_contract, name='approve-contract'),
    
    # API unificada
    path('fund/<int:fund_id>/create-selection/', create_match_selection, name='create_match_selection'),
    path('fund/<int:fund_id>/validate-selection/', validate_selection_capability, name='validate_selection_capability'),
    path('fund/<int:fund_id>/cancel-selection/<int:selection_id>/', cancel_selection, name='cancel_selection'),
    
    
    # Estadísticas
    path('my-selection-stats/', UserSelectionStatsAPIView.as_view(), name='user_selection_stats'),
    
    path('fund/<int:fund_id>/payments/execute/<uuid:order_id>/', execute_payment, name='execute-payment'),
    
    # Permission Management
    path('fund/<int:fund_id>/permissions/grant/', grant_trading_permission, name='permissions-grant'),
    path('permissions/list/', list_user_permissions, name='list-user-permissions'),
    
    # Negotiation Dashboard
    path('negotiations/dashboard/', NegotiationOrdersListAPIView.as_view(), name='negotiation-dashboard'),
    path('negotiations/metrics/', NegotiationStatusOptionsAPIView.as_view(), name='negotiation-metrics'),
    
    # Listado unificado de órdenes (compra + venta)
    path('orders/', get_orders, name='get-orders'),
]