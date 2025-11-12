from django.contrib import admin
from apps.asset.models.core import Asset, AssetType, AssetImage
from apps.asset.models.operating import AssetOperatingIncome, AssetOperatingExpense

# ========================================
# MODELOS CORE (Asset)
# ========================================
@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'color', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    fieldsets = (
        ('Información', {
            'fields': ('name', 'description', 'icon', 'color', 'status')
        }),
        ('Fechas', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']


class AssetImageInline(admin.TabularInline):
    model = AssetImage
    extra = 1
    fields = ['image', 'title', 'order']
    ordering = ['order']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'asset_code', 'name', 'asset_type', 'fund', 
        'status', 'city', 'is_leased', 'created_at'
    ]
    list_filter = [
        'status', 'asset_type', 'fund', 'is_leased', 
        'country', 'created_at'
    ]
    search_fields = [
        'asset_code', 'name', 'description', 'address', 
        'city', 'property_registration', 'cadastral_reference'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'is_active']
    inlines = [AssetImageInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'fund', 'asset_type', 'created_by', 'asset_code', 
                'name', 'description', 'status'
            )
        }),
        ('Ubicación', {
            'fields': (
                'address', 'city', 'state', 'country', 
                'postal_code', 'latitude', 'longitude'
            )
        }),
        ('Características Físicas', {
            'fields': (
                'total_area_m2', 'built_area_m2', 'rentable_area_m2', 
                'year_built'
            )
        }),
        ('Información Legal', {
            'fields': (
                'property_registration', 'cadastral_reference',
                'title_deed_document', 'property_certificate'
            ),
            'classes': ('collapse',)
        }),
        ('Valoración', {
            'fields': (
                'acquisition_value', 'current_value', 'acquisition_date',
                'last_appraisal_date', 'appraisal_document'
            )
        }),
        ('Arrendamiento', {
            'fields': (
                'is_leased', 'tenant_name', 'monthly_rent',
                'lease_start_date', 'lease_end_date', 'lease_contract'
            ),
            'classes': ('collapse',)
        }),
        ('Imágenes', {
            'fields': ('main_image',)
        }),
        ('Metadatos', {
            'fields': ('notes', 'metadata', 'created_at', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('fund', 'asset_type', 'created_by')


@admin.register(AssetImage)
class AssetImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'asset', 'title', 'order', 'created_at']
    list_filter = ['asset', 'created_at']
    search_fields = ['asset__asset_code', 'asset__name', 'title']
    ordering = ['asset', 'order', '-created_at']
    
    fieldsets = (
        ('Información', {
            'fields': ('asset', 'image', 'title', 'description', 'order')
        }),
        ('Fechas', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']


# ========================================
# MODELOS DE INGRESOS Y GASTOS OPERATIVOS
# ========================================
@admin.register(AssetOperatingIncome)
class AssetOperatingIncomeAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'asset', 'period_type', 'period_year', 'period_month',
        'total_operating_income', 'recorded_by', 'created_at'
    ]
    list_filter = [
        'period_type', 'period_year', 'period_month', 
        'asset', 'created_at'
    ]
    search_fields = [
        'asset__asset_code', 'asset__name', 'notes'
    ]
    ordering = ['-period_year', '-period_month', '-created_at']
    readonly_fields = ['created_at', 'period_display']
    
    fieldsets = (
        ('Activo', {
            'fields': ('asset',)
        }),
        ('Período', {
            'fields': (
                'period_type', 'period_year', 'period_month', 
                'period_quarter', 'period_display'
            )
        }),
        ('Ingresos Operativos', {
            'fields': (
                'total_operating_income', 'rental_income', 'other_income'
            )
        }),
        ('Registro', {
            'fields': ('recorded_by', 'notes', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('asset', 'recorded_by')


@admin.register(AssetOperatingExpense)
class AssetOperatingExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'asset', 'period_type', 'period_year', 'period_month',
        'total_operating_expense', 'recorded_by', 'created_at'
    ]
    list_filter = [
        'period_type', 'period_year', 'period_month',
        'asset', 'created_at'
    ]
    search_fields = [
        'asset__asset_code', 'asset__name', 'notes'
    ]
    ordering = ['-period_year', '-period_month', '-created_at']
    readonly_fields = ['created_at', 'period_display']
    
    fieldsets = (
        ('Activo', {
            'fields': ('asset',)
        }),
        ('Período', {
            'fields': (
                'period_type', 'period_year', 'period_month',
                'period_quarter', 'period_display'
            )
        }),
        ('Gastos Operativos', {
            'fields': ('total_operating_expense',)
        }),
        ('Desglose (Opcional)', {
            'fields': (
                'maintenance', 'administration', 'property_taxes',
                'insurance', 'utilities', 'other_expenses'
            ),
            'classes': ('collapse',)
        }),
        ('Registro', {
            'fields': ('recorded_by', 'notes', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('asset', 'recorded_by')