from ..models import Residentialplace
from rest_framework import serializers

class CreateResidentialPlaceSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = Residentialplace
        fields = [ 'resident_country', 'resident_region', 'resident_city',
                'resident_address', 'resident_zip', 'resident_phone',
                ]
