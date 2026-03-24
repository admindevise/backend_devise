from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from apps.utils.core_permissions.api_permissions import RegistryPermission
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from apps.financial_institution.models.permissions import FIUserGroupMembership

from apps.financial_institution.models.core import (
    FinancialInstitution,
    FinancialInstitutionApplication
)
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.financial_institution.serializers.core_serializers import (
    FISerializer, 
    FIApplicationSerializer,
    FIPreApprovalSerializer,
    FIContractSendSerializer,
    FIContractSignSerializer,
    FIApprovalSerializer,
    FIRejectionSerializer,
)

# ===================================================
# VIEWS DE INSTITUCIONES FINANCIERAS
# ===================================================
class FinancialInstitutionViewSet(viewsets.ModelViewSet):
    queryset = FinancialInstitution.objects.all()
    serializer_class = FISerializer
    http_method_names = ['get', 'post']
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            'action': getattr(self, 'action', None),
            'fi_id': self.kwargs.get('fi_id') or self.request.data.get('financial_institution'),
            'view': self,
        })
        return context    
    
    def get_queryset(self):
        user = self.request.user

        # Superuser: ve todas las instituciones
        if user.is_superuser:
            return FinancialInstitution.objects.all()

        # Staff: ve únicamente las instituciones a las que pertenece
        if user.is_staff:
            fi_ids = FIUserGroupMembership.objects.filter(
                user=user,
                is_active=True,
                group__is_active=True,
            ).values_list('group__financial_institution_id', flat=True).distinct()

            return FinancialInstitution.objects.filter(id__in=fi_ids)
        
        return FinancialInstitution.objects.all()

    

# ===================================================
# VIEWS DE SOLICITUDES DE INSTITUCIONES FINANCIERAS
# ===================================================
class FIApplicationActionsViewSet(viewsets.GenericViewSet):
    """
    Acciones de solicitudes FI en formato class-based para compatibilidad con RegistryPermission
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        
        validate_entity_exists(FinancialInstitutionApplication, 'Solicitud de institución financiera', self.kwargs.get('application_id'))
        super().initial(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='create')
    def create_application(self, request, fi_id=None):
        serializer = FIApplicationSerializer(
            data=request.data,
            context={
                'request': request,
                'fi_id': fi_id
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path=r'(?P<application_id>[^/.]+)/pre-approve')
    def pre_approve_fi_application(self, request, **kwargs):
        serializer = FIPreApprovalSerializer(
            data=request.data,
            context={
                'request': request,
                'fi_id': self.kwargs.get('fi_id'),
                'application': kwargs.get('application_id')
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path=r'(?P<application_id>[^/.]+)/send-contract')
    def send_contract_fi_application(self, request, **kwargs):
        serializer = FIContractSendSerializer(
            data=request.data,
            context={
                'request': request,
                'fi_id': self.kwargs.get('fi_id'),
                'application': self.kwargs.get('application_id'),
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path=r'(?P<application_id>[^/.]+)/sign-contract')
    def sign_contract_fi_application(self, request, **kwargs):
        serializer = FIContractSignSerializer(
            data=request.data,
            context={
                'request': request,
                'fi_id': self.kwargs.get('fi_id'),
                'application': self.kwargs.get('application_id'),
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path=r'(?P<application_id>[^/.]+)/approve')
    def approve_application(self, request, **kwargs):
        serializer = FIApprovalSerializer(
            data=request.data,
            context={
                'request': request,
                'fi_id': self.kwargs.get('fi_id'),
                'application': self.kwargs.get('application_id')
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path=r'(?P<application_id>[^/.]+)/reject')
    def reject_application(self, request, **kwargs):
        serializer = FIRejectionSerializer(
            data=request.data,
            context={
                'request': request,
                'fi_id': self.kwargs.get('fi_id'),
                'application': self.kwargs.get('application_id'),
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)