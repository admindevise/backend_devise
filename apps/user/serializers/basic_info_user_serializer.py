from rest_framework import serializers
from ..models import User

class UserBasicInfoSerializer(serializers.ModelSerializer):
    
    class Meta:
        fields = [
                'username',
                'is_natural_person', 'first_name', 'last_name', 'username',
                'birth_date','birth_country','birth_region','birth_city',
                'local_id_type',
                'document_number', 'document_front_image', 'document_back_image', 'selfie', #weetrust
                'doc_country_expedition', 'doc_region_expedition', 'doc_city_expedition',
                'expedition_date', 'mail_delivery', 
                ]
        model = User
    

