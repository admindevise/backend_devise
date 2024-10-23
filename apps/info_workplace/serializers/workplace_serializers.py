from ..models import Workplace
from rest_framework import serializers

class CreateWorkplaceSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = Workplace
        fields = [ 'occupation', 'company_name', 'company_position',
                'company_country', 'company_region', 'company_city',
                'company_phone', 'company_address', 'company_zip',
                ]
