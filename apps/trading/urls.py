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
from apps.trading.views.payment_execution_views import pay_selection, validate_payment
from apps.trading.views.order_selection_views import select_matches, validate_match_selection, auto_select_matches

router = DefaultRouter()
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'sales-orders', SalesOrderViewSet, basename='salesorder')
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    # Router URLs
    path('api/', include(router.urls)),
    
    # Matching URLs (existentes)
    path('api/execute-match/', execute_match, name='execute-match'),
    path('api/find-matches/', find_matches, name='find-matches'),
    
    # Order Selection URLs
    path('api/pay-selection/', pay_selection, name='pay-selection'),
    path('api/validate-payment/', validate_payment, name='validate-payment'),

    # Match Selection URLs
    path('api/select-matches/', select_matches, name='select-matches'),
    path('api/auto-select-matches/', auto_select_matches, name='auto-select-matches'),
    path('api/validate-match-selection/', validate_match_selection, name='validate-match-selection'),
    
    # Utility URLs
    path('api/active-orders/', ActiveOrdersAPIView.as_view(), name='active-orders'),
    
    path('api/cleanup-reservations/', cleanup_expired_reservations, name='cleanup-reservations'),
]