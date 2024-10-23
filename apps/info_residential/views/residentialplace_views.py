from ..models import Residentialplace
from ..serializers.residentialplace_serializer import CreateResidentialPlaceSerializer
from rest_framework.exceptions import ValidationError


from rest_framework import generics

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@permission_classes([IsAuthenticated])
class CreateResidentialplaceInfo(generics.CreateAPIView):
    queryset = Residentialplace.objects.all()
    serializer_class = CreateResidentialPlaceSerializer

    def perform_create(self, serializer):
        if Residentialplace.objects.filter(user = self.request.user).exists():
             raise ValidationError(
                detail = {'detail': 'Residential Place info already created'},
                code = status.HTTP_403_FORBIDDEN
            )
        serializer.save(user=self.request.user)

@permission_classes([IsAuthenticated])
class UpdateReadResidentialplaceInfo(generics.RetrieveUpdateAPIView):
    queryset = Residentialplace.objects.all()
    serializer_class = CreateResidentialPlaceSerializer

    def get_object(self):

        if Residentialplace.objects.filter(user = self.request.user).exists():
            return Residentialplace.objects.get(user=self.request.user)
        
        raise ValidationError(
                detail = {'detail': 'Residential Place not created'},
                code = status.HTTP_403_FORBIDDEN
            )