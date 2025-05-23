from django.contrib import admin
from apps.fund.models import Fund, FundInvestment, TransferReceipt, FundToken

class FundAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount_units', 'amount_tokens', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

class FundInvestmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'investor', 'invested_amount', 'joined_at')
    search_fields = ('fund__name', 'investor__username')
    list_filter = ('joined_at',)
    ordering = ('-joined_at',)
    readonly_fields = ('joined_at',)

class TransferReceiptAdmin(admin.ModelAdmin):
    list_display = ('fund', 'transaction_id', 'created_at')
    search_fields = ('user__username', 'transaction_id')
    
class FundTokenAdmin(admin.ModelAdmin):
    list_display = ('fund', 'token_id', 'created_at')
    search_fields = ('fund__name', 'created_by__username')

admin.site.register(Fund, FundAdmin)
admin.site.register(FundInvestment, FundInvestmentAdmin)
admin.site.register(TransferReceipt, TransferReceiptAdmin)
admin.site.register(FundToken, FundTokenAdmin) 