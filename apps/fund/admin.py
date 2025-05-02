from django.contrib import admin
from apps.fund.models import Fund, FundInvestment, TransferReceipt

class FundAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount', 'created_at')
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
    list_display = ('fund', 'transfer_id', 'created_at')
    search_fields = ('user__username', 'transfer_id')

admin.site.register(Fund, FundAdmin)
admin.site.register(FundInvestment, FundInvestmentAdmin)
admin.site.register(TransferReceipt, TransferReceiptAdmin)