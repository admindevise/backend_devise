from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.shortcuts import get_object_or_404

from apps.financial_institution.models import (
    FinancialInstitution,
    FinancialInstitutionApplication,
    FinancialInstitutionApproval
)
from apps.financial_institution.serializers.core_serializers import (
    FinancialInstitutionSerializer, 
    FinancialInstitutionApplicationSerializer,
    FinancialInstitutionApprovalSerializer,
    FinancialInstitutionRejectionSerializer
)

class FinancialInstitutionViewSet(viewsets.ModelViewSet):
    queryset = FinancialInstitution.objects.all()
    serializer_class = FinancialInstitutionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            return FinancialInstitution.objects.filter(created_by=user, status='active')
        
        return FinancialInstitution.objects.none()
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_application(request):
    """Crear nueva solicitud"""
    serializer = FinancialInstitutionApplicationSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_application(request, application_id):
    """Aprobar solicitud específica"""
    # Verificar permisos y existencia
    application = get_object_or_404(
        FinancialInstitutionApplication,
        id=application_id,
        status='pending'  # Solo pendientes se pueden aprobar
    )
    
    # Agregar el ID al contexto del serializer
    serializer = FinancialInstitutionApprovalSerializer(
        data=request.data,
        context={'request': request, 'application': application}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_application(request, application_id):
    """Rechazar solicitud específica"""
    # Verificar permisos y existencia
    application = get_object_or_404(
        FinancialInstitutionApplication,
        id=application_id,
    )
    
    # Usar serializer específico para rechazo
    serializer = FinancialInstitutionRejectionSerializer(
        data=request.data,
        context={'request': request, 'application': application}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)