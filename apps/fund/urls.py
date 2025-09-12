from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.fund.views.fund_investment_views import (
    FundInvestmentViewSet
)
from apps.fund.views.core_views import (
    FundViewSet,
    FundTokenViewSet,
    TransferReceiptViewSet,
    TokenTransactionViewSet,
    FundSemestralDocumentViewSet as FSDVS,
) 
from apps.kaleido.views.kaleido_fund import (
    TokenMintView,
    TokenMintBatchView,
    TokenBurnView,
    TokenBurnBatchView, 
    PurchaseTokenView,
    PurchaseTokenBatchView,
    batch_creation_progress_view,
    PurchaseTokenIndexToIndexView as PTIV,
)
from apps.fund.views.investor_contract_views import create_investor_contract, sign_investor_contract

from apps.fund.views.utils_views import get_token_count, ai_generate_content

router = DefaultRouter()
router.register(r'main', FundViewSet, basename='fund'),
router.register(r'semestral-document', FSDVS, basename='semestral-document'),

router.register(r'investment', FundInvestmentViewSet, basename='fund-investment'),
router.register(r'transfer_receipt', TransferReceiptViewSet, basename='transfer-receipt'),
router.register(r'token', FundTokenViewSet, basename='fund-token'),
router.register(r'transaction', TokenTransactionViewSet, basename='token-transaction')

urlpatterns = [
    path('api/', include(router.urls)),
    
    #======================================
    # KALEIDO FUND VIEWS
    #======================================
    path('api/mint_token/', TokenMintView.as_view(), name='mint-token'),
    path('api/mint_token_batch/', TokenMintBatchView.as_view(), name='mint-token-batch'),
    
    path('api/burn_token/', TokenBurnView.as_view(), name='burn-token'),
    path('api/burn_token_batch/', TokenBurnBatchView.as_view(), name='burn-token-batch'),
    
    path('api/purchase_token/', PurchaseTokenView.as_view(), name='purchase-token'),
    path('api/purchase_token_batch/', PurchaseTokenBatchView.as_view(), name='purchase-token-batch'),
    
    path('api/purchase_token_user/', PTIV.as_view(), name='purchase-token-user'),
    path('api/<int:fund_id>/batch_progress/', batch_creation_progress_view, name='batch-creation-progress'),
    
    
    # ======================================
    # INVESTOR CONTRACT VIEWS
    # ======================================
    path('api/create-investor-contract/', create_investor_contract, name='create-investor-contract'),
    path('api/sign-investor-contract/<int:contract_id>/', sign_investor_contract, name='sign-investor-contract'),
    
    # ======================================
    # FUND UTILS VIEWS
    # ======================================
    path('api/tokens_count/', get_token_count, name='get-token-count'),
    
    #======================================
    # AI GENERATE CONTENT
    #======================================
    path('api/ai/generate_content/', ai_generate_content, name='ai-generate-content'),
]