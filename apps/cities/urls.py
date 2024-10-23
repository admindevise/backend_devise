from apps.cities.views import CountriesView, RegionsView, SubRegionsView

from django.urls.conf import path


urlpatterns = [
    path('countries/', CountriesView.as_view(), name="cities-contry"),
    path('countries/<slug:slug_country>/regions/', RegionsView.as_view(), name="cities-region"),
    path('countries/<slug:slug_country>/regions/<slug:slug_region>/cities/', SubRegionsView.as_view(), name="cities-city"),
]
