from django.contrib import admin
from apps.fund.models.core import Fund
from apps.fund.models.membership import FundInvestment, InvestorContract, InvestmentApplication
from apps.fund.models.receipts import TransferReceipt
from apps.fund.models.tokens import FundToken, TokenTransaction

class FundAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount_units', 'amount_tokens', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

class InvestorContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'user', 'status', 'created_at')

class FundInvestmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'user', 'final_invested_amount', 'created_at')
    search_fields = ('fund__name', 'user__username')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
class InvestmentApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'user', 'application_status', 'created_at')
    list_filter = ('fund__name', 'user__email')


class TransferReceiptAdmin(admin.ModelAdmin):
    list_display = ('fund', 'transaction_id', 'created_at')
    search_fields = ('user__username', 'transaction_id')
    
class FundTokenAdmin(admin.ModelAdmin):
    list_display = ('fund', 'token_id', 'status', 'owner_user', 'created_at')
    list_filter = ('status', 'created_at', 'fund', 'owner_user')
    ordering = ('-created_at',)
    search_fields = ('fund__name', 'created_by__username')
    
class TokenTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'token', 'amount', 'created_at')
    search_fields = ('fund__fund__name', 'fund_token__token')
    list_filter = ('created_at',)
    ordering = ('-created_at',)

admin.site.register(Fund, FundAdmin)
admin.site.register(InvestorContract, InvestorContractAdmin)
admin.site.register(FundInvestment, FundInvestmentAdmin)
admin.site.register(InvestmentApplication, InvestmentApplicationAdmin)

admin.site.register(TransferReceipt, TransferReceiptAdmin)
admin.site.register(FundToken, FundTokenAdmin) 
admin.site.register(TokenTransaction, TokenTransactionAdmin)