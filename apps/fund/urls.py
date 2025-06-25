from rest_framework.routers import DefaultRouter
from django.urls import path, include

from apps.fund.views.fund_core_views import (
    FundViewSet, TransferReceiptViewSet, FundTokenViewSet, TokenTransactionViewSet
) 
from apps.fund.views.fund_application_views import (
    FundApplicationViewSet, FundApplicationPendingReviewView,
)
from apps.fund.views.fund_investment_views import (
    FundInvestmentViewSet
)

from apps.kaleido.views.kaleido_fund import (
    TokenMintView, TokenMintBatchView, TokenBurnView, PurchaseTokenView, PurchaseTokenIndexToIndexView as PTIV,
    batch_creation_progress_view
)

router = DefaultRouter()
router.register(r'main', FundViewSet, basename='fund'),
router.register(r'investment', FundInvestmentViewSet, basename='fund-investment'),
router.register(r'transfer_receipt', TransferReceiptViewSet, basename='transfer-receipt'),
router.register(r'token', FundTokenViewSet, basename='fund-token'),
router.register(r'application', FundApplicationViewSet, basename='fund-application'),
router.register(r'transaction', TokenTransactionViewSet, basename='token-transaction')

urlpatterns = [
    path('api/', include(router.urls)),
    #path('timezone/', get_timezone, name='get-timezone'),
    
    #=========== APIREST Views FundToken ===========#
    path('api/mint_token/', TokenMintView.as_view(), name='mint-token'),
    path('api/mint_token_batch/', TokenMintBatchView.as_view(), name='mint-token-batch'),
    path('api/burn_token/', TokenBurnView.as_view(), name='burn-token'),
    path('api/purchase_token/', PurchaseTokenView.as_view(), name='purchase-token'),
    path('api/purchase_token_user/', PTIV.as_view(), name='purchase-token-user'),
    path('api/<int:fund_id>/batch_progress/', batch_creation_progress_view, name='batch-creation-progress'),
    
    #=========== APIREST Views Application ===========#
    path('api/pending_review/', FundApplicationPendingReviewView.as_view(), name='fund-application-view'),
    
]