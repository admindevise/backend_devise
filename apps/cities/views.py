from apps.cities.serializers import CountriesSerializer, RegionsSerializer, SubRegionsSerializer

from rest_framework.generics import ListAPIView

from cities_light.models import Country, Region, SubRegion


class CountriesView(ListAPIView):
    serializer_class = CountriesSerializer
    queryset = Country.objects.all()
    permission_classes = []
    pagination_class = None


class RegionsView(ListAPIView):
    serializer_class = RegionsSerializer
    queryset = Region.objects.all()
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        return Region.objects.filter(country__pk=self.kwargs.get('slug_country'))


class SubRegionsView(ListAPIView):
    serializer_class = SubRegionsSerializer
    queryset = SubRegion.objects.all()
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        print("GET", self.request.GET)
        return SubRegion.objects.filter(
            country__pk=self.kwargs.get('slug_country'),
            region__pk=self.kwargs.get('slug_region')
        )
