from django.contrib import admin

# ===================================
# IMPORTS
# ===================================

# Core
from apps.fund.models.core import Fund, OthersI

# Membership
from apps.fund.models.membership import (
    FundInvestment,
    InvestorContract,
    InvestmentApplication,
)

# Tokens
from apps.fund.models.tokens import FundToken, TokenTransaction

# Receipts
from apps.fund.models.receipts import TransferReceipt

# Distributions
from apps.fund.models.distributions import (
    DistributionPeriod,
    InvestmentDistributionRecord,
    TokenDistributionDetail,
)

# Operating
from apps.fund.models.operating import FundOperatingIncome, FundOperatingExpense

# Accounting
from apps.fund.models.accounting import (
    AccountCategory,
    AccountingPeriod,
    AccountingEntry,
    AccountingBalance,
    AccountingImportBatch,
    AccountingImportError,
    FinancialSummary,
    Accountability
)


# ===================================
# CORE
# ===================================

@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount_units', 'amount_tokens', 'price_per_unit', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(OthersI)
class OthersIAdmin(admin.ModelAdmin):
    list_display = ('doc_number', 'document', 'name')
    list_filter = ('doc_number',)


# ===================================
# MEMBERSHIP
# ===================================

@admin.register(InvestorContract)
class InvestorContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'user', 'status', 'created_at')
    list_filter = ('status', 'fund')
    raw_id_fields = ('user', 'fund')


@admin.register(FundInvestment)
class FundInvestmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'investment_status', 'created_at')
    list_filter = ('investment_status',)
    raw_id_fields = ('application',)


@admin.register(InvestmentApplication)
class InvestmentApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'user', 'application_status', 'created_at')
    list_filter = ('application_status', 'fund')
    raw_id_fields = ('user', 'fund')


# ===================================
# TOKENS
# ===================================

@admin.register(FundToken)
class FundTokenAdmin(admin.ModelAdmin):
    list_display = ('token_id', 'fund', 'status', 'owner_user', 'created_at')
    list_filter = ('status', 'fund')
    search_fields = ('token_id',)
    raw_id_fields = ('owner_user', 'fund')


@admin.register(TokenTransaction)
class TokenTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'token', 'amount', 'created_at')
    list_filter = ('fund',)


@admin.register(TransferReceipt)
class TransferReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'transaction_id', 'created_at')
    search_fields = ('transaction_id',)


# ===================================
# DISTRIBUTIONS
# ===================================

@admin.register(DistributionPeriod)
class DistributionPeriodAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'period_year', 'period_month', 'total_distribution_amount', 'status')
    list_filter = ('status', 'fund', 'period_year')


@admin.register(InvestmentDistributionRecord)
class InvestmentDistributionRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'investment', 'distribution_period', 'net_distribution_amount_cop', 'payment_status')
    list_filter = ('payment_status',)
    raw_id_fields = ('investment', 'distribution_period')


@admin.register(TokenDistributionDetail)
class TokenDistributionDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'investment_distribution')
    raw_id_fields = ('investment_distribution',)


# ===================================
# OPERATING
# ===================================

@admin.register(FundOperatingIncome)
class FundOperatingIncomeAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'period_year', 'period_month', 'total_operating_income')
    list_filter = ('fund', 'period_year')


@admin.register(FundOperatingExpense)
class FundOperatingExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'period_year', 'period_month', 'total_operating_expense')
    list_filter = ('fund', 'period_year')


# ===================================
# ACCOUNTING
# ===================================

@admin.register(AccountCategory)
class AccountCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category_type', 'fund', 'is_active')
    list_filter = ('fund', 'category_type', 'is_active')
    search_fields = ('code', 'name')


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ('fund', 'year', 'month', 'period_status')
    list_filter = ('fund', 'period_status', 'year')


@admin.register(AccountingEntry)
class AccountingEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'fund', 'category', 'entry_type', 'amount', 'entry_status')
    list_filter = ('fund', 'entry_status', 'entry_type')
    search_fields = ('description',)
    raw_id_fields = ('fund', 'period', 'category')


@admin.register(AccountingBalance)
class AccountingBalanceAdmin(admin.ModelAdmin):
    list_display = ('fund', 'period', 'category', 'opening_balance', 'closing_balance')
    list_filter = ('fund',)


@admin.register(AccountingImportBatch)
class AccountingImportBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'import_type', 'import_status', 'total_rows', 'successful_rows', 'failed_rows')
    list_filter = ('fund', 'import_status')


@admin.register(AccountingImportError)
class AccountingImportErrorAdmin(admin.ModelAdmin):
    list_display = ('batch', 'row_number', 'severity', 'error_code', 'is_resolved')
    list_filter = ('severity', 'is_resolved')


@admin.register(FinancialSummary)
class FinancialSummaryAdmin(admin.ModelAdmin):
    list_display = ('fund', 'period', 'summary_type', 'total_income', 'total_expenses', 'net_result')
    list_filter = ('fund', 'summary_type')
    
@admin.register(Accountability)
class AccountabilityAdmin(admin.ModelAdmin):
    list_display = ('fund', 'name', 'period_type', 'period_year', 'period_month' )
    list_filter = ('fund', 'period_type')