from ..models import Socioeconomic, OriginFund
from ..serializers.socioeconomic_serializers import SocioeconomicUserInfoSerializer
from ..serializers.originfund_serializers import OriginFundSerializer

from rest_framework.exceptions import ValidationError

from rest_framework import generics

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


@permission_classes([IsAuthenticated])
class ListOriginsFunds(generics.ListAPIView):
    queryset = OriginFund.objects.all()
    serializer_class = OriginFundSerializer
    pagination_class = None
    

@permission_classes([IsAuthenticated])
class SocioeconomicUserInfo(generics.CreateAPIView):
    queryset = Socioeconomic.objects.all()
    serializer_class = SocioeconomicUserInfoSerializer

    def perform_create(self, serializer):
        if Socioeconomic.objects.filter(user = self.request.user).exists():
             raise ValidationError(
                detail = {'detail': 'Socioeconomic info already created'},
                code = status.HTTP_403_FORBIDDEN
            )
        serializer.save(user=self.request.user)

@permission_classes([IsAuthenticated])
class UpdateReadSocioeconomicUserInfo(generics.RetrieveUpdateAPIView):
    queryset = Socioeconomic.objects.all()
    serializer_class = SocioeconomicUserInfoSerializer

    def get_object(self):

        if Socioeconomic.objects.filter(user = self.request.user).exists():
            return Socioeconomic.objects.get(user=self.request.user)
        
        raise ValidationError(
                detail = {'detail': 'Socioeconomic info not created'},
                code = status.HTTP_403_FORBIDDEN
            )