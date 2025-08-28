from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend

from apps.audit.audit_service import AuditService
from apps.utils.views.Mixins import DateFilterMixin

from apps.fund.models import(
    Fund,
    FundToken,
    TransferReceipt,
    TokenTransaction,
    FundSemestralDocument
)
from apps.fund.serializers.core_serializers import(
    FundSerializer,
    FundTokenSerializer,
    TransferReceiptSerializer,
    FundSemestralDocumentSerializer,
)
from apps.fund.serializers.transaction_serializers import TokenTransactionSerializer


class FundViewSet(DateFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Fund to be viewed or edited.
    
    Este ViewSet proporciona automáticamente acciones `list`, `create`, `retrieve`,
    `update` y `destroy`.
    
    Cada operación genera registros de auditoría para seguimiento completo.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FundSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    #filterset_fields = ['user', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Filtra los fondos para mostrar solo los del usuario autenticado,
        a menos que el usuario sea admin (en cuyo caso muestra todos).
        """
        #user = self.request.user
        queryset = Fund.objects.all()
            
        queryset = self.apply_date_filters(queryset)
        return queryset

    def perform_create(self, serializer):
        """
        Asigna el usuario autenticado al fondo y crea registro de auditoría.
        """
        user = self.request.user
        
        # Registrar inicio de creación
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="FUND_CREATE",
            obj=user,  # Usamos el usuario como referencia hasta crear el fondo
            details={
                'name': serializer.validated_data.get('name'),
                'amount': serializer.validated_data.get('amount'),
                'operation': 'create_fund'
            },
            status='PENDING'
        )
        
        try:
            # Crear el fondo
            fund = serializer.save(user=user)
            
            # Actualizar estado de auditoría a SUCCESS
            if initial_audit:
                initial_audit.status = 'SUCCESS'
                initial_audit.save(update_fields=['status'])
                
                # Actualizar también el objeto de referencia para que quede asociado al fondo
                if hasattr(initial_audit, 'content_type'):
                    fund_content_type = ContentType.objects.get_for_model(Fund)
                    initial_audit.content_type = fund_content_type
                    initial_audit.object_id = fund.id
                    initial_audit.save(update_fields=['content_type', 'object_id'])
            
            return fund
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise  # Re-lanzar la excepción para que DRF la maneje

    def perform_update(self, serializer):
        """
        Actualiza un fondo y crea registro de auditoría.
        """
        # Obtener el fondo antes de la actualización
        fund = self.get_object()
        old_data = {
            'name': fund.name,
            'description': fund.description,
            'amount': str(fund.amount)
        }
        
        # Registrar inicio de actualización
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="FUND_UPDATE",
            obj=fund,
            details={
                'old_data': old_data,
                'operation': 'update_fund'
            },
            status='PENDING'
        )
        
        try:
            # Actualizar el fondo
            updated_fund = serializer.save()
            
            # Datos después de la actualización
            new_data = {
                'name': updated_fund.name,
                'description': updated_fund.description,
                'amount': str(updated_fund.amount)
            }
            
            # Actualizar estado de auditoría a SUCCESS
            if initial_audit:
                initial_audit.status = 'SUCCESS'
                initial_audit.details.update({'new_data': new_data})
                initial_audit.save(update_fields=['status', 'details'])
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise  # Re-lanzar la excepción para que DRF la maneje
            
    def perform_destroy(self, instance):
        """
        Elimina un fondo y crea registro de auditoría.
        """
        # Registrar inicio de eliminación
        fund_data = {
            'id': instance.id,
            'name': instance.name,
            'description': instance.description,
            'amount': str(instance.amount)
        }
        
        # Para eliminar, creamos un único registro directamente como SUCCESS
        # ya que no hay un estado intermedio significativo
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="FUND_DELETE",
            obj=self.request.user,  # Referencia al usuario ya que el fondo será eliminado
            details={
                'fund_data': fund_data,
                'operation': 'delete_fund'
            },
            status='PENDING'
        )
        
        try:
            # Eliminar el fondo
            result = super().perform_destroy(instance)
            
            # Actualizar estado de auditoría a SUCCESS
            if initial_audit:
                initial_audit.status = 'SUCCESS'
                initial_audit.save(update_fields=['status'])
                
            return result
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise  # Re-lanzar la excepción para que DRF la maneje
        
class FundSemestralDocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite gestionar documentos semestrales de fondos.
    Proporciona acciones `list`, `create`, `retrieve`, `update` y `destroy`.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FundSemestralDocumentSerializer
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ['get', 'post', 'delete']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund']
    search_fields = ['document']
    ordering_fields = ['uploaded_date']
    ordering = ['-uploaded_date']

    def get_queryset(self):
        """
        Filtra los documentos para mostrar solo los del usuario autenticado,
        a menos que el usuario sea admin (en cuyo caso muestra todos).
        """
        user = self.request.user
        queryset = FundSemestralDocument.objects.select_related('fund').filter(fund__user=user)
            
        return queryset
        
class TransferReceiptViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint que permite ver recibos de transferencia.
    Solo permite operaciones de lectura (list, retrieve).
    
    Filtros disponibles:
    - user: ID del usuario
    - fund: ID del fondo
    - created_at: Fecha de creación del recibo
    
    Búsqueda:
    - transfer_id: ID de la transferencia
    
    Ordenamiento:
    - created_at: Fecha de creación
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TransferReceiptSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'fund']
    search_fields = ['transaction_id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = TransferReceipt.objects.all()
        
        if not user.is_superuser:
            queryset = queryset.filter(user=user)
        
        queryset = self.apply_date_filters(queryset)
        return queryset

class FundTokenViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para gestionar tokens de fondos.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FundTokenSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'status', 'created_by', 'owner_user', 'reserved_for_sale', 'reserved_at']
    search_fields = ['token_id', 'nickname']
    ordering_fields = ['created_at', 'token_id']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = FundToken.objects.all()
        
        if not user.is_staff:
            queryset = queryset.filter(created_by=user)
            
        queryset = self.apply_date_filters(queryset)
        
        return queryset

class TokenTransactionViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para gestionar transacciones de tokens.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TokenTransactionSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'from_user', 'to_user']
    search_fields = ['kaleido_transaction_id', 'description']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = TokenTransaction.objects.all()
        
        if not user.is_staff:
            queryset = queryset.filter(from_user=user)
            
        queryset = self.apply_date_filters(queryset)
        
        return queryset