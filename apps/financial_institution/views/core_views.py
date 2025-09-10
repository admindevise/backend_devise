from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, viewsets

from apps.financial_institution.models import (
    FinancialInstitution
)
from apps.financial_institution.serializers.core_serializers import (
    FISerializer, 
    FIApplicationSerializer,
    FIPreApprovalSerializer,
    FIContractSendSerializer,
    FIContractSignSerializer,
    FIApprovalSerializer,
    FIRejectionSerializer,
)

class FinancialInstitutionViewSet(viewsets.ModelViewSet):
    queryset = FinancialInstitution.objects.all()
    serializer_class = FISerializer
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
    serializer = FIApplicationSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pre_approve_fi_application(request, application_id):
    """
    Pre-aprobar una solicitud de institución financiera
    
    Permite a un administrador pre-aprobar una solicitud, cambiando su estado
    a "under_review" y creando un registro de aprobación preliminar.
    """
    serializer = FIPreApprovalSerializer(
        data=request.data,
        context={'request': request, 'application': application_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_contract_fi_application(request, application_id):
    """
    Enviar contrato a un solicitante pre-aprobado
    
    Permite enviar un documento de contrato a un usuario cuya solicitud
    ha sido pre-aprobada y está en revisión.
    """
    serializer = FIContractSendSerializer(
        data=request.data,
        context={'request': request, 'application': application_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sign_contract_fi_application(request, application_id):
    """Firmar contrato enviado"""
    serializer = FIContractSignSerializer(
        data=request.data,
        context={'request': request, 'application': application_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_application(request, application_id):
    """Aprobar solicitud específica"""
    serializer = FIApprovalSerializer(
        data=request.data,
        context={'request': request, 'application': application_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_application(request, application_id):
    """Rechazar solicitud específica"""   
    # Usar serializer específico para rechazo
    serializer = FIRejectionSerializer(
        data=request.data,
        context={'request': request, 'application': application_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)