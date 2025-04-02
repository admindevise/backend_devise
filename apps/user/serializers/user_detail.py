from rest_framework import serializers

from apps.info_financial.serializers.financial_serializer import CreateFinancialSerializer
from apps.info_residential.serializers.residentialplace_serializer import CreateResidentialPlaceSerializer
from apps.info_workplace.serializers.workplace_serializers import CreateWorkplaceSerializer
from apps.info_socioeconomic.serializers.socioeconomic_serializers import SocioeconomicUserInfoSerializer
from apps.user.serializers.basic_info_user_serializer import UserBasicInfoSerializer

from apps.user.models import User
from apps.info_financial.models import Financial
from apps.info_residential.models import Residentialplace
from apps.info_workplace.models import Workplace
from apps.info_socioeconomic.models import Socioeconomic

class UserDetailedSerializer(UserBasicInfoSerializer):
    financial_data = serializers.SerializerMethodField('get_financial_data')
    residential_data = serializers.SerializerMethodField('get_residential_data')
    workplace_data = serializers.SerializerMethodField('get_workplace_data')
    socioeconomic_data = serializers.SerializerMethodField('get_socioeconomic_data')

    class Meta:
        model = User
        fields = UserBasicInfoSerializer.Meta.fields + [
            'financial_data',
            'residential_data',
            'workplace_data',
            'socioeconomic_data'
        ]

    def get_financial_data(self, obj):
        try:
            financial = Financial.objects.get(user=obj)
            return CreateFinancialSerializer(financial).data
        except Financial.DoesNotExist:
            return None
            
    def get_residential_data(self, obj):
        try:
            residential = Residentialplace.objects.get(user=obj)
            return CreateResidentialPlaceSerializer(residential).data
        except Residentialplace.DoesNotExist:
            return None
            
    def get_workplace_data(self, obj):
        try:
            workplace = Workplace.objects.get(user=obj)
            return CreateWorkplaceSerializer(workplace).data
        except Workplace.DoesNotExist:
            return None
            
    def get_socioeconomic_data(self, obj):
        try:
            socioeconomic = Socioeconomic.objects.get(user=obj)
            return SocioeconomicUserInfoSerializer(socioeconomic).data
        except Socioeconomic.DoesNotExist:
            return None