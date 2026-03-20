from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.cities.serializers import CountriesSerializer, RegionsSerializer, SubRegionsSerializer
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.financial_institution.models.core import FinancialInstitution
from cities_light.models import Country, Region, SubRegion


class CountriesView(ListAPIView):
    serializer_class = CountriesSerializer
    queryset = Country.objects.all()
    permission_classes = [IsAuthenticated, RegistryPermission]
    pagination_class = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))


class RegionsView(ListAPIView):
    serializer_class = RegionsSerializer
    queryset = Region.objects.all()
    permission_classes = [IsAuthenticated, RegistryPermission]
    pagination_class = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        validate_entity_exists(Country, 'País', self.kwargs.get('country_id'))

    def get_queryset(self):
        return Region.objects.filter(country_id=self.kwargs.get('country_id'))


class SubRegionsView(ListAPIView):
    serializer_class = SubRegionsSerializer
    queryset = SubRegion.objects.all()
    permission_classes = [IsAuthenticated, RegistryPermission]
    pagination_class = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        validate_entity_exists(Country, 'País', self.kwargs.get('country_id'))
        validate_entity_exists(Region, 'Región', self.kwargs.get('region_id'))

    def get_queryset(self):
        return SubRegion.objects.filter(
            country_id=self.kwargs.get('country_id'),
            region_id=self.kwargs.get('region_id'),
        )