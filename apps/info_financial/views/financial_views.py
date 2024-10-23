from ..models import Financial
from ..serializers.financial_serializer import CreateFinancialSerializer
from rest_framework.exceptions import ValidationError

from rest_framework import generics

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.druo.functions.accounts_api import create_account


@permission_classes([IsAuthenticated])
class CreateFinancialUserInfo(generics.CreateAPIView):
    queryset = Financial.objects.all()
    serializer_class = CreateFinancialSerializer

    def perform_create(self, serializer):
        if Financial.objects.filter(user = self.request.user).exists():
            raise ValidationError(
                detail = {'detail': 'Financial info already created'},
                code = status.HTTP_403_FORBIDDEN
            )
        account_info = serializer.save(user=self.request.user)
        print("25. financial_views: ", account_info.account_number )
        #Creando la cuenta en DRUO
        create_account(self.request.user, account_info)


@permission_classes([IsAuthenticated])
class UpdateReadFinancialUserInfo(generics.RetrieveUpdateAPIView):
    queryset = Financial.objects.all()
    serializer_class = CreateFinancialSerializer

    def get_object(self):

        if Financial.objects.filter(user = self.request.user).exists():
            return Financial.objects.get(user=self.request.user)
        
        raise ValidationError(
                detail = {'detail': 'Financial info not created'},
                code = status.HTTP_403_FORBIDDEN
            )