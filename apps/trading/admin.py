from django.contrib import admin
from apps.trading.models.core_models import (
    PurchaseOrder,
    SalesOrder,
    Transaction,
    OrderBook,
)

from apps.trading.models.selection_models import (
    MatchSelection
)

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_number',
        'units',
        'price_per_unit',
        'total_amount',
        'expiration_date',
        'margin',
        'status',
        'supplier_user',
        'fund',
        'created_by',
        'paid_at',
        'cancelled_at',
        'created_at'
    )
    search_fields = ('order_number',)
    list_filter = ('status',)
    ordering = ('-created_at',)
    readonly_fields = ('total_amount',)

class SalesOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_number',
        'units',
        'price_per_unit',
        'total_amount',
        'expiration_date',
        'margin',
        'status',
        'seller_user',
        'fund',
        'created_by',
        'cancelled_at',
        'created_at'
    )
    search_fields = ('order_number',)
    list_filter = ('status',)
    ordering = ('-created_at',)
    readonly_fields = ('total_amount',)

class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'purchase_order',
        'sales_order',
        'buyer',
        'seller',
        'fund',
        'units',
        'price_per_unit',
        'total_amount',
        'created_at',
    )
    search_fields = ('purchase_order__order_number', 'sales_order__order_number')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('total_amount',)

class OrderBookAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'fund',
        'last_price',
        'daily_high',
        'daily_low',
        'daily_volume',
        'status',
        'created_at',
    )
    search_fields = ('fund',)
    list_filter = ('status',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
class MatchSelectionAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'sales_order', 'total_units')
    search_fields = ('created_by',)
    list_filter = ('status',)

admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
admin.site.register(SalesOrder, SalesOrderAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(OrderBook, OrderBookAdmin)
admin.site.register(MatchSelection, MatchSelectionAdmin)