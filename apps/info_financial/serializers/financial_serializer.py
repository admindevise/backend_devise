from ..models import Financial
from rest_framework import serializers

class CreateFinancialSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = Financial
        fields = [ 'bank', 'account_number', 'account_type', 'account_subtype',
                'certification_file', 'aba_code', 'swift_code',
                ]


class ListFinancialSerializer(serializers.ModelSerializer):
    bank = serializers.StringRelatedField()
    account_type = serializers.StringRelatedField()
    account_subtype = serializers.StringRelatedField()
    
    class Meta:
        model = Financial
        fields = ['id', 'bank', 'account_number', 'account_type', 'account_subtype',
                'certification_file', 'aba_code', 'swift_code',
                ]