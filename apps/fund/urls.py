from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import FundViewSet, FundInvestmentViewSet, TransferReceiptViewSet, FundTokenViewSet, FundApplicationView, FundInvestmentView
from apps.kaleido.views.kaleido_fund import (
    TokenMintView, TokenBurnView, PurchaseTokenView, PurchaseTokenIndexToIndexView as PTIV,
)

router = DefaultRouter()
router.register(r'main', FundViewSet, basename='fund'),
router.register(r'fund_investment', FundInvestmentViewSet, basename='fund-investment'),
router.register(r'transfer_receipt', TransferReceiptViewSet, basename='transfer-receipt'),
router.register(r'token', FundTokenViewSet, basename='fund-token')

urlpatterns = [
    path('api/', include(router.urls)),
    #path('timezone/', get_timezone, name='get-timezone'),
    
    #=========== APIREST Views FundToken ===========#
    path('api/mint_token/', TokenMintView.as_view(), name='mint-token'),
    path('api/burn_token/', TokenBurnView.as_view(), name='burn-token'),
    path('api/purchase_token/', PurchaseTokenView.as_view(), name='purchase-token'),
    path('api/purchase_token_user/', PTIV.as_view(), name='purchase-token-user'),
    
    #=========== APIREST Views Fund-Link ===========#
    path('api/fund_application/', FundApplicationView.as_view(), name='fund-application'),
    path('api/fund_inves/', FundInvestmentView.as_view(), name='fund-investment-view'),
]