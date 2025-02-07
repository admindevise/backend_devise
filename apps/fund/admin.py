from django.contrib import admin
from apps.fund.models import Fund, FundPrice

class FundAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

admin.site.register(Fund, FundAdmin)