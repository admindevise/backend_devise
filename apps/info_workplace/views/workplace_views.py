from rest_framework import generics, status
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from ..models import Workplace
from ..serializers.workplace_serializers import (
    CreateWorkplaceSerializer, ListWorkplaceSerializer
)


@permission_classes([IsAuthenticated])
class CreateWorkplace(generics.CreateAPIView):
    serializer_class = CreateWorkplaceSerializer

    def get_queryset(self):
        return Workplace.objects.select_related('company_country', 'company_region', 'company_city')

    def perform_create(self, serializer):
        if Workplace.objects.filter(user=self.request.user).exists():
            raise ValidationError(
                detail={'detail': 'Workplace info already exists for this user.'},
                code=status.HTTP_400_BAD_REQUEST
            )
        serializer.save(user=self.request.user)


@permission_classes([IsAuthenticated])
class UpdateReadWorkplace(generics.RetrieveUpdateAPIView):

    def get_queryset(self):
        return Workplace.objects.select_related('company_country', 'company_region', 'company_city')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CreateWorkplaceSerializer
        return ListWorkplaceSerializer

    def get_object(self):
        obj = get_object_or_404(
            Workplace.objects.select_related('company_country', 'company_region', 'company_city'),
            user=self.request.user
        )
        return obj