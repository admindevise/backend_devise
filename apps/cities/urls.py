from django.urls import path
from apps.cities.views import CountriesView, RegionsView, SubRegionsView

urlpatterns = [
    path('fi/<int:fi_id>/countries/', CountriesView.as_view(), name='cities-country'),
    path('fi/<int:fi_id>/countries/<int:country_id>/regions/', RegionsView.as_view(), name='cities-region'),
    path('fi/<int:fi_id>/countries/<int:country_id>/regions/<int:region_id>/cities/', SubRegionsView.as_view(), name='cities-city'),
]