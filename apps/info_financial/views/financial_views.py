from rest_framework import generics, status
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from ..models import Financial
from ..serializers.financial_serializer import (
    CreateFinancialSerializer, ListFinancialSerializer
)
from apps.druo.functions.accounts_api import create_account


@permission_classes([IsAuthenticated])
class CreateFinancialUserInfo(generics.CreateAPIView):
    """
    Create financial information for the authenticated user.
    Only one financial record per user is allowed.
    """
    serializer_class = CreateFinancialSerializer

    def get_queryset(self):
        return Financial.objects.select_related('bank', 'account_type', 'account_subtype')

    def perform_create(self, serializer):
        if Financial.objects.filter(user=self.request.user).exists():
            raise ValidationError(
                detail={'detail': 'Financial info already exists for this user.'},
                code=status.HTTP_400_BAD_REQUEST
            )
        
        account_info = serializer.save(user=self.request.user)
        
        # Create account in DRUO - continue even if it fails
        try:
            create_account(self.request.user, account_info)
        except Exception as e:
            print(f"Failed to create DRUO account for user {self.request.user.id}: {str(e)}")
            # Don't raise exception, just log the error


@permission_classes([IsAuthenticated])
class UpdateReadFinancialUserInfo(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update financial information for the authenticated user.
    """
    
    def get_queryset(self):
        return Financial.objects.select_related('bank', 'account_type', 'account_subtype')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CreateFinancialSerializer
        return ListFinancialSerializer

    def get_object(self):
        obj = get_object_or_404(
            Financial.objects.select_related('bank', 'account_type', 'account_subtype'),
            user=self.request.user
        )
        return obj