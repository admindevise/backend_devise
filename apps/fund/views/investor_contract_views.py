from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, viewsets

from apps.fund.serializers.invester_contract_serializers import (
    InvestorContractSerializer,
    InvestorContractCreateSerializer,
    InvestorContractSignSerializer,
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_investor_contract(request):
    """Crear nuevo contrato de inversor"""
    serializer = InvestorContractCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sign_investor_contract(request, contract_id):
    """
    Firmar un contrato de inversor existente
    
    Permite a un usuario autenticado firmar un contrato de inversor que está en estado pendiente.
    """
    serializer = InvestorContractSignSerializer(
        data=request.data,
        context={'request': request, 'contract': contract_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    