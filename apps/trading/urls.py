from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.trading.views.trading_views import (
    PurchaseOrderViewSet,
    SalesOrderViewSet,
    TransactionViewSet,
    ActiveOrdersAPIView,
    cleanup_expired_reservations,
)

from apps.trading.views.find_matching_views import execute_match, find_matches
from apps.trading.views.payment_execution_views import (
    execute_payment
    )

from apps.trading.views.order_selection_views import (
    select_matches,
    validate_match_selection,
    auto_select_matches,
)

from apps.trading.views.contract_views import list_pending_contracts, approve_contract, OrderContractListView
from apps.trading.views import permission_views

from apps.trading.views.selection_management_views import (
    MatchSelectionViewSet,
    UserSelectionStatsAPIView,
    create_match_selection,
    validate_selection_capability,
    cancel_selection,
    create_purchase_selection,
    create_sales_selection
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
    path('api/execute-match/', execute_match, name='execute-match'),
    path('api/find-matches/', find_matches, name='find-matches'),
    
    # Match Selection URLs
    path('api/select-matches/', select_matches, name='select-matches'),
    path('api/auto-select-matches/', auto_select_matches, name='auto-select-matches'),
    path('api/validate-match-selection/', validate_match_selection, name='validate-match-selection'),
    
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
    
    # APIs de conveniencia
    path('api/create-purchase-selection/', create_purchase_selection, name='create_purchase_selection'),
    path('api/create-sales-selection/', create_sales_selection, name='create_sales_selection'),
    
    # Estadísticas
    path('api/my-selection-stats/', UserSelectionStatsAPIView.as_view(), name='user_selection_stats'),
    
    path('api/execute-payment/', execute_payment, name='execute-payment'),
    
    # Endpoints con permisos
    path('api/create-purchase-order-with-permissions/', 
         permission_views.create_purchase_order_with_permissions, 
         name='create-purchase-order-permissions'),
    
    path('api/create-sales-order-with-permissions/', 
         permission_views.create_sales_order_with_permissions, 
         name='create-sales-order-permissions'),
    
    path('api/grant-trading-permission/', 
         permission_views.grant_trading_permission, 
         name='grant-trading-permission'),
    
    path('api/list-user-permissions/', 
         permission_views.list_user_permissions, 
         name='list-user-permissions'),
    
    # Negotiation Dashboard
    path('api/negotiations/dashboard/', NegotiationOrdersListAPIView.as_view(), name='negotiation-dashboard'),
    path('api/negotiations/metrics/', NegotiationStatusOptionsAPIView.as_view(), name='negotiation-metrics'),
]