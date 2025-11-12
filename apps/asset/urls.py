from django.urls import path, include
from apps.asset.views.core_views import (
    AssetTypeViewSet,
    create_asset
)
from apps.asset.views.kpis_views import (
    calculate_asset_noi,
    get_asset_noi_summary,
    calculate_asset_cap_rate,
    calculate_output_value,
    calculate_asset_free_cash_flow,
    calculate_asset_cash_on_cash,
    calculate_asset_dividend_yield,
    calculate_asset_dividend_yield_moving_average,
    calculate_asset_irr,
    calculate_asset_moic
)
from apps.asset.views.operating_views import (
    AssetOperatingExpenseViewSet,
    AssetOperatingIncomeViewSet
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'operating-expense', AssetOperatingExpenseViewSet, basename='operating-expense')
router.register(r'operating-income', AssetOperatingIncomeViewSet, basename='operating-income')

router.register(r'asset-type', AssetTypeViewSet, basename='asset-type')

urlpatterns = [
    path('api/', include(router.urls)),
    
    path('api/create/', create_asset, name='create_asset'),
    
    path('api/kpis/noi/', calculate_asset_noi, name='calculate-asset-noi'),
    path('api/kpis/cap-rate/', calculate_asset_cap_rate, name='calculate-cap-rate'),
    path('api/kpis/output-value/', calculate_output_value, name='calculate-output-value'),
    path('api/kpis/free-cash-flow/', calculate_asset_free_cash_flow, name='calculate-asset-free-cash-flow'),    
    path('api/kpis/cash-on-cash/', calculate_asset_cash_on_cash, name='calculate-asset-cash-on-cash'),        
    path('api/kpis/dividend-yield/', calculate_asset_dividend_yield, name='calculate-asset-dividend-yield'),    
    path('api/kpis/dividend-yield-movil/', calculate_asset_dividend_yield_moving_average, name='calculate-asset-dividend-yield-moving-average'),    
    path('api/kpis/irr/', calculate_asset_irr, name='calculate-asset-irr'),
    path('api/kpis/moic/', calculate_asset_moic, name='calculate-asset-moic'),         
]
