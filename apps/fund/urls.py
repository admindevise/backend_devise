from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FundViewSet, FundPriceViewSet, FundInvestmentViewSet

router = DefaultRouter()
router.register(r'main', FundViewSet, basename='fund'),
router.register(r'fund_investment', FundInvestmentViewSet, basename='fund-investment'),

fund_price_list = FundPriceViewSet.as_view({
    'get': 'list'
})

urlpatterns = [
    path('', include(router.urls)),
    path('fund_prices/<int:fund_id>/<str:interval>/', fund_price_list, name='fund-price-list'),
]