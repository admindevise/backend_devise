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

router = DefaultRouter()
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'sales-orders', SalesOrderViewSet, basename='salesorder')
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    # Router URLs
    path('api/', include(router.urls)),
    
    # Matching URLs (existentes)
    path('execute-match/', execute_match, name='execute-match'),
    path('find-matches/', find_matches, name='find-matches'),
    
    # Utility URLs
    path('active-orders/', ActiveOrdersAPIView.as_view(), name='active-orders'),
    
    path('api/cleanup-reservations/', cleanup_expired_reservations, name='cleanup-reservations'),
]