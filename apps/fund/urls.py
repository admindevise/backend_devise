from django.urls import path, include
from rest_framework.routers import DefaultRouter

# ====================== INVESTMENT ======================
from apps.fund.views.investment_views import (
    InvestmentViewSet,
    InvestmentApplicationViewSet,
    InvestmentDashboardViewSet,
    PendingApplicationViewSet,
    submit_investment_application,
    under_review_investment_application,
    send_contrat_investment_application,
    sign_contract_investment_application,
)

# ==================== DISTRIBUTIONS ====================
from apps.fund.views.distributions_views import (
    InvestmentDistributionRecordViewSet as IDRVS,
    create_distribution_period,
    distributions_records
)

# ========================= KPIs =========================
from apps.fund.views.KPIs_views import (
    calculate_token_value_change,
    get_fund_distributions_12m,
    calculate_yield_from_distributions,
    user_price_change,
    user_rent_12m_per_unit,
    user_cash_on_cash,
    user_current_value,
    user_simple_total_return,
    user_total_portfolio,
    user_total_distributions_all_funds,
    user_total_cash_received_all_funds,
    user_total_simple_return_all_funds,
    user_weighted_average_return_all_funds,
    user_weighted_average_cash_on_cash_all_funds,
)

# ========================= FUND =========================
from apps.fund.views.core_views import (
    FundViewSet,
    FundMembersViewSet,
    FundTokenViewSet,
    TransferReceiptViewSet,
    TokenTransactionViewSet,
    FundSemestralDocumentViewSet as FSDVS,
) 

# ======================= KALEIDO =======================
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

from apps.fund.views.utils_views import get_token_count, ai_generate_content, testing

router = DefaultRouter()
router.register(r'main', FundViewSet, basename='fund'),
router.register(r'members', FundMembersViewSet, basename='fund-members')
router.register(r'semestral-document', FSDVS, basename='semestral-document'),

router.register(r'application-pending', PendingApplicationViewSet, basename='investment-application-pending')
router.register(r'investment-application', InvestmentApplicationViewSet, basename='investment-application')
router.register(r'investment', InvestmentViewSet, basename='investment'),
router.register(r'invesment-dashboard', InvestmentDashboardViewSet, basename='investment-dashboard'),

router.register(r'investment-distribution', IDRVS, basename='investment-distribution')

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
    # INVESTMENT APPLICATION
    # ======================================
    path('api/submit-investment/', submit_investment_application, name='sumbit-investment'),
    path('api/under-review-investment-application/<int:application_id>/', under_review_investment_application, name='under-review-investment-application'),
    path('api/send-contract-investment-application/<int:application_id>/', send_contrat_investment_application, name='send-contract-investment-application'),
    path('api/sign-contract-investment-application/<int:application_id>/', sign_contract_investment_application, name='sign-contract-investment-application'),
    
    # ======================================
    # DISTRIBUTIONS PERIOD
    # ======================================
    path('api/create-distribution-period/', create_distribution_period, name='create-distriburion-period'),
    path('api/distributions-by-members/', distributions_records, name='distributions-records'),
    
    # ======================================
    # KPIs
    # ======================================
    path('api/kpis/token-value-change/', calculate_token_value_change, name='tkn-value-change'),
    path('api/kpis/distributions-12m/', get_fund_distributions_12m, name='distributions-12m'),
    path('api/kpis/yield-from-distributions/', calculate_yield_from_distributions, name='yield-from-distributions'),
    path('api/kpis/user-price-change/', user_price_change, name='user-price-change'),
    path('api/kpis/user-rent-12m-per-unit/', user_rent_12m_per_unit, name='user-rent-12m-per-unit'),
    path('api/kpis/user-cash-on-cash/', user_cash_on_cash, name='user-cash-on-cash'),
    path('api/kpis/user-current-value/', user_current_value, name='user-current-value'),
    path('api/kpis/user-simple-total-return/', user_simple_total_return, name='user-simple-total-return'),
    # portfolio
    path('api/kpis/user-total-portfolio/', user_total_portfolio, name='user-total-portfolio'),
    path('api/kpis/user-total-distributions-all-funds/', user_total_distributions_all_funds, name='user-total-distributions-all-funds'),
    path('api/kpis/user-total-cash-received-all-funds/', user_total_cash_received_all_funds, name='user-total-cash-received-all-funds'),
    path('api/kpis/user-total-simple-return-all-funds/', user_total_simple_return_all_funds, name='user-total-simple-return-all-funds'),
    path('api/kpis/user-weighted-average-return/', user_weighted_average_return_all_funds, name='user-weighted-average-return'),
    path('api/kpis/user-weighted-average-cash-on-cash-all-funds/', user_weighted_average_cash_on_cash_all_funds, name='user-weighted-average-cash-on-cash-all-funds'),
    
    # ======================================
    # FUND UTILS VIEWS
    # ======================================
    path('api/tokens_count/', get_token_count, name='get-token-count'),
    
    #======================================
    # AI GENERATE CONTENT
    #======================================
    path('api/ai/generate_content/', ai_generate_content, name='ai-generate-content'),
    
    path('testing/', testing, name='testing')
]