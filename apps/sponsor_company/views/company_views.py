from ..models import SponsorCompany
from ..serializers.company_serializer import (CreateCompanySerializer,
                            ReadCompanySerializer, ListSelectSponsorSerializer
                            )
from rest_framework.exceptions import ValidationError

from rest_framework import generics

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


@permission_classes([IsAuthenticated])
class CreateCompany(generics.CreateAPIView):
    queryset = SponsorCompany.objects.all()
    serializer_class = CreateCompanySerializer

    def perform_create(self, serializer):
        usuario = self.request.user
        if SponsorCompany.objects.filter(user = usuario).exists():
            raise ValidationError(
                detail = {'detail': 'Company info already created'},
                code = status.HTTP_403_FORBIDDEN
            )
        new_company = serializer.save(user=usuario)
        usuario.company_asociated = new_company
        usuario.save()
#aca falta asociar la empresa a mi usuario

@permission_classes([IsAuthenticated])
class ReadCompany(generics.RetrieveAPIView):
    queryset = SponsorCompany.objects.all()
    serializer_class = ReadCompanySerializer

    def get_object(self):

        if SponsorCompany.objects.filter(user = self.request.user).exists():
            return SponsorCompany.objects.get(user=self.request.user)
             
        raise ValidationError(
                detail = {'detail': 'Company info not created'},
                code = status.HTTP_403_FORBIDDEN
            )

@permission_classes([IsAuthenticated])
class UpdateCompany(generics.UpdateAPIView):
    queryset = SponsorCompany.objects.all()
    serializer_class = CreateCompanySerializer

    def get_object(self):

        if SponsorCompany.objects.filter(user = self.request.user).exists():
            return SponsorCompany.objects.get(user=self.request.user)
             
        raise ValidationError(
                detail = {'detail': 'Company info not created'},
                code = status.HTTP_403_FORBIDDEN
            )
    
@permission_classes([IsAuthenticated])
class ListSelectSponsorView(generics.ListAPIView):
    queryset = SponsorCompany.objects.all()
    serializer_class = ListSelectSponsorSerializer
    pagination_class = None