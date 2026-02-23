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
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'sales-orders', SalesOrderViewSet, basename='salesorder')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'contracts', OrderContractListView, basename='ordercontract')
router.register(r'selections', MatchSelectionViewSet, basename='matchselection')


urlpatterns = [
    # Router URLs
    path('api/', include(router.urls)),
    
    # Matching URLs (existentes)
    path('api/search-matches/', find_matches, name='find-matches'),
    
    # Utility URLs
    path('api/active-orders/', ActiveOrdersAPIView.as_view(), name='active-orders'),
    
    path('api/cleanup-reservations/', cleanup_expired_reservations, name='cleanup-reservations'),
    
    # Contract URLs
    path('api/contracts-pending/', list_pending_contracts, name='list-pending-contracts'),
    path('api/contracts-approve/<int:contract_id>/', approve_contract, name='approve-contract'),
    
    # API unificada
    path('api/create-selection/', create_match_selection, name='create_match_selection'),
    path('api/validate-selection/', validate_selection_capability, name='validate_selection_capability'),
    path('api/cancel-selection/', cancel_selection, name='cancel_selection'),
    
    # Estadísticas
    path('api/my-selection-stats/', UserSelectionStatsAPIView.as_view(), name='user_selection_stats'),
    
    path('api/payments/execute/', execute_payment, name='execute-payment'),
    
    # Permission Management
    path('api/permissions/grant/', grant_trading_permission, name='permissions-grant'),
    path('api/permissions/list/', list_user_permissions, name='list-user-permissions'),
    
    # Negotiation Dashboard
    path('api/negotiations/dashboard/', NegotiationOrdersListAPIView.as_view(), name='negotiation-dashboard'),
    path('api/negotiations/metrics/', NegotiationStatusOptionsAPIView.as_view(), name='negotiation-metrics'),
    
    # Listado unificado de órdenes (compra + venta)
    path('api/orders/', get_orders, name='get-orders'),
]