from rest_framework import generics, status
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from ..models import Residentialplace
from ..serializers.residentialplace_serializer import (
    CreateResidentialPlaceSerializer, ListResidentialPlaceSerializer
)


@permission_classes([IsAuthenticated])
class CreateResidentialplaceInfo(generics.CreateAPIView):
    """
    Create residential place information for the authenticated user.
    Only one residential place record per user is allowed.
    """
    serializer_class = CreateResidentialPlaceSerializer

    def get_queryset(self):
        return Residentialplace.objects.select_related('resident_country', 'resident_region', 'resident_city')

    def perform_create(self, serializer):
        if Residentialplace.objects.filter(user=self.request.user).exists():
            raise ValidationError(
                detail={'detail': 'Residential place info already exists for this user.'},
                code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save(user=self.request.user)


@permission_classes([IsAuthenticated])
class UpdateReadResidentialplaceInfo(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update residential place information for the authenticated user.
    """
    
    def get_queryset(self):
        return Residentialplace.objects.select_related('resident_country', 'resident_region', 'resident_city')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CreateResidentialPlaceSerializer
        return ListResidentialPlaceSerializer

    def get_object(self):
        obj = get_object_or_404(
            Residentialplace.objects.select_related('resident_country', 'resident_region', 'resident_city'),
            user=self.request.user
        )
        return obj