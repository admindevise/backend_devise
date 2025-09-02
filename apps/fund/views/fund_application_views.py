from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import action

from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.views.Mixins import DateFilterMixin

from apps.fund.serializers.fund_investment_serializers import (
    FundInvestmentSerializer,
    FundApplicationSerializer,
    FundApplicationStatusSerializer,
    FundApplicationReviewSerializer,
    FundApplicationRejectionSerializer
)
from apps.fund.models.membership import FundApplication
from apps.fund.services.application_service import FundApplicationService

class FundApplicationViewSet(DateFilterMixin, viewsets.ModelViewSet):
    serializer_class = FundApplicationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_methods_names = ['get', 'post']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'applicant']
    search_fields = ['fund__name', 'applicant__email']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    
    def get_serializer_class(self):
        """
        Determinar qué serializer usar según la acción
        """
        if self.action in ['approve_application', 'reject_application', 'list', 'retrieve']:
            return FundApplicationStatusSerializer
        else:
            return FundApplicationSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = FundApplication.objects.select_related('fund', 'applicant')
        
        if not user.is_staff:
            queryset = queryset.filter(applicant=user)
        
        return self.apply_date_filters(queryset)
    
    @action(detail=True, methods=['patch'], url_path='approve')
    def approve_application(self, request, pk=None):
        """
        Aprobar aplicación - NO usa serializer de aprobación,
        usa el servicio directamente
        """
        # 1. Validar entrada con serializer auxiliar
        review_serializer = FundApplicationReviewSerializer(data=request.data)
        review_serializer.is_valid(raise_exception=True)
        
        try:
            # 2. Llamar al servicio directamente
            application, investment = FundApplicationService.approve_application(
                application_id=pk,
                reviewer=request.user,
                review_notes=review_serializer.validated_data.get('review_notes', ''),
                request=request
            )
            
            # 3. Respuesta con datos procesados
            return Response({
                "status": "success",
                "message": "Application approved successfully",
                "data": {
                    "application": FundApplicationSerializer(application).data,
                    "investment": FundInvestmentSerializer(investment).data
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'], url_path='reject')
    def reject_application(self, request, pk=None):
        """
        Rechazar aplicación - Similar al approve
        """
        # 1. Validar entrada
        rejection_serializer = FundApplicationRejectionSerializer(data=request.data)
        rejection_serializer.is_valid(raise_exception=True)
        
        try:
            # 2. Llamar al servicio
            application = FundApplicationService.reject_application(
                application_id=pk,
                reviewer=request.user,
                rejection_reason=rejection_serializer.validated_data['rejection_reason'],
                review_notes=rejection_serializer.validated_data.get('review_notes', '')
            )
            
            # 3. Respuesta
            return Response({
                "status": "success",
                "message": "Application rejected successfully",
                "data": FundApplicationSerializer(application).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": str(e.detail[0])
            }, status=status.HTTP_400_BAD_REQUEST)

class FundApplicationPendingReviewView(DateFilterMixin, ListAPIView):
    """
    Vista para listar aplicaciones pendientes de revisión.
    Permite a los administradores ver todas las aplicaciones pendientes de revisión.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = FundApplicationStatusSerializer
    pagination_class = PageNumberPagination
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'applicant']
    search_fields = ['fund__name', 'applicant__email', 'applicant__first_name']
    ordering_fields = ['created_at', 'status', 'requested_amount']
    ordering = ['-created_at']
    
    page_size = 10
    page_size_query_param = 'page_size'
    
    
    def get_queryset(self):
        """
        Usar servicio para obtener el queryset filtrado
        """
        queryset = FundApplicationService.get_applications_for_review(self.request.user)
        
        queryset = self.apply_date_filters(queryset)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """ Sobrescribir el método list para usar el servicio y devolver los datos procesados"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                "status": "success",
                "count": len(serializer.data),
                "data": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_message = str(e)
            
            # Si es un error de filtro invalid_choice, formatearlo mejor
            if "invalid_choice" in error_message or "Escoja una opción válida" in error_message:
                return Response({
                    "status": "validation_error",
                    "error": "El valor proporcionado para el filtro no es válido o no existe",
                    "detail": "Verifique que los IDs de fondo o aplicante existan en el sistema",
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Para otros errores, mantener el formato original
            return Response({
                "error": error_message,
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)