from ..models import SponsorCompany
from rest_framework import serializers
from apps.cities.serializers import (CountriesSerializer, RegionSimpleSerializer, SubRegionSimpleSerializer)

class CreateCompanySerializer(serializers.ModelSerializer):
      
    class Meta:
        model = SponsorCompany
        fields = [
                'company_name', 'company_country', 'company_region',
                'company_city', 'company_phone', 'company_address', 'company_zip_code',
                'nit', 'camara_comercio', 'logo_empresa', 'info_empresa',
                'area_registro',
                ]
        
class ReadCompanySerializer(serializers.ModelSerializer):

    company_country = CountriesSerializer(read_only=True)
    company_region = RegionSimpleSerializer(read_only=True)
    company_city = SubRegionSimpleSerializer(read_only=True)
    class Meta:
        model = SponsorCompany
        fields = [
                'company_name', 'company_country', 'company_region',
                'company_city', 'company_phone', 'company_address', 'company_zip_code',
                'nit', 'camara_comercio', 'logo_empresa', 'info_empresa',
                'area_registro',
                ]

class ListSelectSponsorSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = SponsorCompany
        fields = [
                'id',
                'company_name',
                ]
        
