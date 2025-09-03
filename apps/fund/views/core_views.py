from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend

from apps.audit.audit_service import AuditService
from apps.utils.views.Mixins import DateFilterMixin

from apps.fund.models.core import (
    Fund,
    FundSemestralDocument
)
from apps.fund.models.tokens import (
    FundToken,
    TokenTransaction
)
from apps.fund.models.receipts import TransferReceipt
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
    http_method_names = ['get', 'post']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        return self.apply_date_filters(
            Fund.objects.select_related('user').all()
        )
    
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