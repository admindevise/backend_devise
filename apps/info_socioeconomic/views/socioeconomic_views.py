from rest_framework import status
from rest_framework import generics
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

from ..models import Socioeconomic, OriginFund
from ..serializers.socioeconomic_serializers import (
    SocioeconomicUserInfoSerializer, ListSocioeconomicSerializer
)
from ..serializers.originfund_serializers import OriginFundSerializer


@permission_classes([IsAuthenticated])
class ListOriginsFunds(generics.ListAPIView):
    queryset = OriginFund.objects.all()
    serializer_class = OriginFundSerializer
    pagination_class = None
    

@permission_classes([IsAuthenticated])
class SocioeconomicUserInfo(generics.CreateAPIView):
    serializer_class = SocioeconomicUserInfoSerializer

    def get_queryset(self):
        return Socioeconomic.objects.select_related(
            'foreign_operations_country', 'country_of_tax_residence'
        ).prefetch_related('origin_of_funds')

    def perform_create(self, serializer):
        if Socioeconomic.objects.filter(user=self.request.user).exists():
            raise ValidationError(
                detail={'detail': 'Socioeconomic info already exists for this user.'},
                code=status.HTTP_400_BAD_REQUEST
            )
        serializer.save(user=self.request.user)


@permission_classes([IsAuthenticated])
class UpdateReadSocioeconomicUserInfo(generics.RetrieveUpdateAPIView):

    def get_queryset(self):
        return Socioeconomic.objects.select_related(
            'foreign_operations_country', 'country_of_tax_residence'
        ).prefetch_related('origin_of_funds')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SocioeconomicUserInfoSerializer
        return ListSocioeconomicSerializer

    def get_object(self):
        obj = get_object_or_404(
            Socioeconomic.objects.select_related(
                'foreign_operations_country', 'country_of_tax_residence'
            ).prefetch_related('origin_of_funds'),
            user=self.request.user
        )
        return obj