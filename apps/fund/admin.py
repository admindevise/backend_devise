from django.contrib import admin
from apps.fund.models import Fund, FundInvestment, TransferReceipt, FundToken, FundApplication

class FundAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount_units', 'amount_tokens', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

class FundApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'applicant', 'requested_amount', 'status', 'created_at')
    search_fields = ('fund__name', 'applicant__username')
    list_filter = ('status', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'applicant', 'reviewed_by')

class FundInvestmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'fund', 'investor', 'invested_amount', 'created_at')
    search_fields = ('fund__name', 'investor__username')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

class TransferReceiptAdmin(admin.ModelAdmin):
    list_display = ('fund', 'transaction_id', 'created_at')
    search_fields = ('user__username', 'transaction_id')
    
class FundTokenAdmin(admin.ModelAdmin):
    list_display = ('fund', 'token_id', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'fund')
    ordering = ('-created_at',)
    search_fields = ('fund__name', 'created_by__username')

admin.site.register(Fund, FundAdmin)
admin.site.register(FundApplication, FundApplicationAdmin)
admin.site.register(FundInvestment, FundInvestmentAdmin)
admin.site.register(TransferReceipt, TransferReceiptAdmin)
admin.site.register(FundToken, FundTokenAdmin) 