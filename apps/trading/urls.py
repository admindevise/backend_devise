from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import routers

from apps.trading.views.trading_views import (
    PurchaseOrderViewSet,
    SalesOrderViewSet,
    TransactionViewSet,
    OrderBookViewSet,
    ActiveOrdersAPIView,
)

from apps.trading.views.find_matching_views import find_matches, execute_match

routers = DefaultRouter()
routers.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
routers.register(r'sales-orders', SalesOrderViewSet, basename='sales-order')
routers.register(r'transactions', TransactionViewSet, basename='transaction')
routers.register(r'order-book', OrderBookViewSet, basename='order-book')

urlpatterns = [
    path('api/', include(routers.urls)),
    path('api/active-orders/', ActiveOrdersAPIView.as_view(), name='active-orders'),
    path('api/find-matches/', find_matches, name='find-matches'),
    path('api/execute-match/', execute_match, name='execute-match'),
]