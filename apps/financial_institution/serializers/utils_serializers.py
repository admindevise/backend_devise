from rest_framework import serializers
from apps.financial_institution.models.core import (
    FinancialInstitutionApproval
)
from apps.user.serializers.basic_info_user_serializer import UserShortInfoSerializer

class MembersFinancialInstitutionSerializer(serializers.ModelSerializer):
    user = UserShortInfoSerializer()
    approval_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    class Meta:
        model = FinancialInstitutionApproval
        fields = ['user', 'approval_date', 'max_investment_amount', 'investor_profile']