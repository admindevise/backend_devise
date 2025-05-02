from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FundViewSet, FundInvestmentViewSet, TransferReceiptViewSet

router = DefaultRouter()
router.register(r'main', FundViewSet, basename='fund'),
router.register(r'fund_investment', FundInvestmentViewSet, basename='fund-investment'),
router.register(r'transfer_receipt', TransferReceiptViewSet, basename='transfer-receipt'),

urlpatterns = [
    path('', include(router.urls)),
    #path('timezone/', get_timezone, name='get-timezone'),
]