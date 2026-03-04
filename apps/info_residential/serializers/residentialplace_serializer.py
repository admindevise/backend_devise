from ..models import Residentialplace
from rest_framework import serializers
from apps.cities.serializers import (
    CountrySimpleSerializer, 
    RegionSimpleSerializer, 
    SubRegionSimpleSerializer
)

class CreateResidentialPlaceSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = Residentialplace
        fields = [ 'resident_country', 'resident_region', 'resident_city',
                'resident_address', 'resident_zip', 'resident_phone',
                ]

class ListResidentialPlaceSerializer(serializers.ModelSerializer):
    resident_country = CountrySimpleSerializer(read_only=True)
    resident_region = RegionSimpleSerializer(read_only=True)
    resident_city = SubRegionSimpleSerializer(read_only=True)
    
    class Meta:
        model = Residentialplace
        fields = ['id', 'resident_country', 'resident_region', 'resident_city',
                'resident_address', 'resident_zip', 'resident_phone',
                ]