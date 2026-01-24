"""
Fund URLs Configuration

Organización:
1. Core Fund (Fund, Members, Tokens)
2. Investments & Applications
3. Distributions
4. Accounting
5. KPIs (Old & New)
6. Kaleido Integration
7. Operating
8. Utils & AI
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# ============================================================================
# 1. CORE FUND VIEWS
# ============================================================================
from apps.fund.views.core_views import (
    FundViewSet,
    FundMembersViewSet,
    FundTokenViewSet,
    TransferReceiptViewSet,
    TokenTransactionViewSet,
    FundSemestralDocumentViewSet,
    OthersIViewSet,
    TrustAgreementViewSet,
) 

# ============================================================================
# 2. INVESTMENT VIEWS
# ============================================================================
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

from apps.fund.views.investor_contract_views import (
    create_investor_contract,
    sign_investor_contract,
)

# ============================================================================
# 3. DISTRIBUTIONS VIEWS
# ============================================================================
from apps.fund.views.distributions_views import (
    InvestmentDistributionRecordViewSet,
    create_distribution_period,
    distributions_records,
)

# ============================================================================
# 3.1 TRANSFERS VIEWS (Cesiones)
# ============================================================================
from apps.fund.views.transfers_views import (
    TransfersViewSet,
    create_transfer,
    fund_transfer_summary,
    delete_transfer,
)

# ============================================================================
# 3.2 COMMISSIONS VIEWS
# ============================================================================
from apps.fund.views.commissions_views import (
    CommissionsViewSet,
    create_commission,
    update_commission,
    delete_commission,
)

# ============================================================================
# 4. ACCOUNTING VIEWS
# ============================================================================
from apps.fund.views.accounting_views import (
    AccountingEntryViewSet,
    AccountCategoryViewSet,
    AccountingPeriodViewSet,
    AccountabilityViewSet,
)

from apps.fund.views.accounting_service_views import (
    validate_accounting_file,
    import_accounting_file,
    get_default_mapping,
    create_invoice_record,
)

from apps.fund.views.accounting_service_views import (
    validate_accounting_file,
    import_accounting_file,
    get_default_mapping,
)

# ============================================================================
# 5. KPIs - OLD (Legacy)
# ============================================================================
from apps.fund.views.KPIs_old_views import (
    # Token Value
    calculate_token_value_change,
    get_fund_distributions_12m,
    calculate_yield_from_distributions,
    
    # User Metrics
    user_price_change,
    user_rent_12m_per_unit,
    user_cash_on_cash,
    user_current_value,
    user_simple_total_return,
    
    # Portfolio Aggregations
    user_total_portfolio,
    user_total_distributions_all_funds,
    user_total_cash_received_all_funds,
    user_total_simple_return_all_funds,
    user_weighted_average_return_all_funds,
    user_weighted_average_cash_on_cash_all_funds,
    
    # Dividend Yield
    dividend_yield_historical,
    dividend_yield_current,
    accumulated_investment,
)

# ============================================================================
# 6. KPIs - NEW (Strategies)
# ============================================================================
from apps.fund.views.kpis_views import (
    calculate_fund_noi,
    calculate_fund_valuation,
    calculate_fund_cap_rate,
    calculate_output_value,
    calculate_fund_free_cash_flow,
    calculate_fund_cash_on_cash,
    calculate_fund_dividend_yield,
    calculate_fund_dividend_yield_moving_average,
    calculate_fund_irr,
    calculate_fund_moic,
)

# ============================================================================
# 7. KALEIDO INTEGRATION
# ============================================================================
from apps.kaleido.views.kaleido_fund import (
    TokenMintView,
    TokenMintBatchView,
    TokenBurnView,
    TokenBurnBatchView, 
    PurchaseTokenView,
    PurchaseTokenBatchView,
    PurchaseTokenIndexToIndexView,
    batch_creation_progress_view,
)

# ============================================================================
# 8. OPERATING
# ============================================================================
from apps.fund.views.operating_views import (
    FundOperatingIncomeViewSet,
    FundOperatingExpenseViewSet
)

# ============================================================================
# 9. UTILS & AI
# ============================================================================
from apps.fund.views.utils_views import (
    get_token_count,
    ai_generate_content,
    testing,
)


# ============================================================================
# ROUTER REGISTRATION
# ============================================================================
router = DefaultRouter()

# Core Fund
router.register(r'main', FundViewSet, basename='fund')
router.register(r'members', FundMembersViewSet, basename='fund-members')
router.register(r'semestral-document', FundSemestralDocumentViewSet, basename='semestral-document')
router.register(r'othersi', OthersIViewSet, basename='otrosi')
router.register(r'token', FundTokenViewSet, basename='fund-token')
router.register(r'transaction', TokenTransactionViewSet, basename='token-transaction')
router.register(r'transfer_receipt', TransferReceiptViewSet, basename='transfer-receipt')
router.register(r'trust-agreement', TrustAgreementViewSet, basename='trust-agreement')

# Investments
router.register(r'investment', InvestmentViewSet, basename='investment')
router.register(r'investment-application', InvestmentApplicationViewSet, basename='investment-application')
router.register(r'application-pending', PendingApplicationViewSet, basename='investment-application-pending')
router.register(r'investment-dashboard', InvestmentDashboardViewSet, basename='investment-dashboard')

# Distributions
router.register(r'investment-distribution', InvestmentDistributionRecordViewSet, basename='investment-distribution')

# Accounting
router.register(r'accounting-category', AccountCategoryViewSet, basename='accounting-category')
router.register(r'accounting', AccountingEntryViewSet, basename='accounting')
router.register(r'accounting-period', AccountingPeriodViewSet, basename='accounting-period')

# Operating
router.register(r'operating-income', FundOperatingIncomeViewSet, basename='operating-income')
router.register(r'operating-expense', FundOperatingExpenseViewSet, basename='operating-expense')

# Transfers (Cesiones)
router.register(r'transfers-obtain', TransfersViewSet, basename='transfers')

# Commissions
router.register(r'commissions-obtain', CommissionsViewSet, basename='commissions')

# Accountability
router.register(r'accountability', AccountabilityViewSet, basename='accountability')


# ============================================================================
# URL PATTERNS
# ============================================================================
urlpatterns = [
    # Router URLs
    path('api/', include(router.urls)),
    
    # ========================================================================
    # KALEIDO - Token Operations
    # ========================================================================
    path('api/mint/', TokenMintView.as_view(), name='mint-token'),
    path('api/mint-batch/', TokenMintBatchView.as_view(), name='mint-token-batch'),
    path('api/burn/', TokenBurnView.as_view(), name='burn-token'),
    path('api/burn-batch/', TokenBurnBatchView.as_view(), name='burn-token-batch'),
    path('api/purchase/', PurchaseTokenView.as_view(), name='purchase-token'),
    path('api/purchase-batch/', PurchaseTokenBatchView.as_view(), name='purchase-token-batch'),
    path('api/purchase-user/', PurchaseTokenIndexToIndexView.as_view(), name='purchase-token-user'),
    path('api/<int:fund_id>/batch-progress/', batch_creation_progress_view, name='batch-creation-progress'),
    
    # ========================================================================
    # INVESTMENTS - Applications & Contracts
    # ========================================================================
    path('api/investment/submit/', submit_investment_application, name='submit-investment'),
    path('api/investment/application/<int:application_id>/under-review/', under_review_investment_application, name='under-review-investment-application'),
    path('api/investment/application/<int:application_id>/send-contract/', send_contrat_investment_application, name='send-contract-investment-application'),
    path('api/investment/application/<int:application_id>/sign-contract/', sign_contract_investment_application, name='sign-contract-investment-application'),
    
    # Investor Contracts
    path('api/investment/contract/create/', create_investor_contract, name='create-investor-contract'),
    path('api/investment/contract/<int:contract_id>/sign/', sign_investor_contract, name='sign-investor-contract'),
    
    # ========================================================================
    # DISTRIBUTIONS
    # ========================================================================
    path('api/distributions/create-period/', create_distribution_period, name='create-distribution-period'),
    path('api/distributions/records/', distributions_records, name='distributions-records'),
    
    # ========================================================================
    # TRANSFERS (Cesiones)
    # ========================================================================
    path('api/transfers/create/', create_transfer, name='create-transfer'),
    path('api/transfers/<int:transfer_id>/delete/', delete_transfer, name='delete-transfer'),
    path('api/<int:fund_id>/transfers/summary/', fund_transfer_summary, name='fund-transfer-summary'),
    
    path('api/accounting-validate/', validate_accounting_file, name='validate-accounting'),
    path('api/import-account-file/', import_accounting_file, name='import-account-file'),
    path('api/accounting-default-mapping/', get_default_mapping, name='default-mapping'),
    
    # ========================================================================
    # ACCOUNTABILITY
    # ========================================================================
    path('api/accounting-invoice/create-invoice-record/', create_invoice_record, name='create-invoice-record'),
    
    # ========================================================================
    # COMMISSIONS
    # ========================================================================
    path('api/commissions/create/', create_commission, name='create-commission'),
    path('api/commissions/<int:commission_id>/update/', update_commission, name='update-commission'),
    path('api/commissions/<int:commission_id>/delete/', delete_commission, name='delete-commission'),
    
    # ========================================================================
    # KPIs - OLD (Legacy)
    # ========================================================================
    # Token Metrics
    path('api/kpis/old/token-value-change/', calculate_token_value_change, name='token-value-change'),
    path('api/kpis/old/distributions-12m/', get_fund_distributions_12m, name='distributions-12m'),
    path('api/kpis/old/yield-from-distributions/', calculate_yield_from_distributions, name='yield-from-distributions'),
    
    # User Metrics
    path('api/kpis/old/user/price-change/', user_price_change, name='user-price-change'),
    path('api/kpis/old/user/rent-12m/', user_rent_12m_per_unit, name='user-rent-12m-per-unit'),
    path('api/kpis/old/user/cash-on-cash/', user_cash_on_cash, name='user-cash-on-cash'),
    path('api/kpis/old/user/current-value/', user_current_value, name='user-current-value'),
    path('api/kpis/old/user/simple-return/', user_simple_total_return, name='user-simple-total-return'),
    
    # Portfolio Aggregations
    path('api/kpis/old/portfolio/total/', user_total_portfolio, name='user-total-portfolio'),
    path('api/kpis/old/portfolio/distributions/', user_total_distributions_all_funds, name='user-total-distributions-all-funds'),
    path('api/kpis/old/portfolio/cash-received/', user_total_cash_received_all_funds, name='user-total-cash-received-all-funds'),
    path('api/kpis/old/portfolio/simple-return/', user_total_simple_return_all_funds, name='user-total-simple-return-all-funds'),
    path('api/kpis/old/portfolio/weighted-return/', user_weighted_average_return_all_funds, name='user-weighted-average-return'),
    path('api/kpis/old/portfolio/weighted-cash-on-cash/', user_weighted_average_cash_on_cash_all_funds, name='user-weighted-average-cash-on-cash'),
    
    # Dividend Yield
    path('api/kpis/old/dividend-yield/historical/', dividend_yield_historical, name='dividend-yield-historical'),
    path('api/kpis/old/dividend-yield/current/', dividend_yield_current, name='dividend-yield-current'),
    path('api/kpis/old/accumulated-investment/', accumulated_investment, name='accumulated-investment'),
    
    # ========================================================================
    # KPIs - NEW (Strategies)
    # ========================================================================
    path('api/kpis/noi/', calculate_fund_noi, name='calculate-fund-noi'),
    path('api/kpis/fund-valuation/', calculate_fund_valuation, name='calculate-fund-valuation'),
    path('api/kpis/cap-rate/', calculate_fund_cap_rate, name='calculate-cap-rate'),
    path('api/kpis/output-value/', calculate_output_value, name='calculate-output-value'),
    path('api/kpis/free-cash-flow/', calculate_fund_free_cash_flow, name='calculate-fund-free-cash-flow'),
    path('api/kpis/cash-on-cash/', calculate_fund_cash_on_cash, name='calculate-fund-cash-on-cash'),
    path('api/kpis/dividend-yield/', calculate_fund_dividend_yield, name='calculate-fund-dividend-yield'),
    path('api/kpis/dividend-yield-moving/', calculate_fund_dividend_yield_moving_average, name='calculate-fund-dividend-yield-moving'),
    path('api/kpis/irr/', calculate_fund_irr, name='calculate-fund-irr'),
    path('api/kpis/moic/', calculate_fund_moic, name='calculate-fund-moic'),
    
    # ========================================================================
    # UTILS & AI
    # ========================================================================
    path('api/utils/token-count/', get_token_count, name='get-token-count'),
    path('api/ai/generate-content/', ai_generate_content, name='ai-generate-content'),
    
    # Testing (Solo desarrollo)
    path('testing/', testing, name='testing'),
]