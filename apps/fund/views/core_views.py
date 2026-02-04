from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.views.Mixins import DateFilterMixin

from apps.fund.models.membership import InvestorContract
from apps.fund.models.core import (
    Fund,
    OthersI,
    FundCategory,
    TrustAgreement,
    FundSemestralDocument,
)
from apps.fund.models.tokens import (
    FundToken,
    TokenTransaction
)
from apps.fund.models.receipts import TransferReceipt
from apps.fund.serializers.core_serializers import(
    FundSerializer,
    FundCategorySerializer,
    OthersISerializer,
    FundTokenSerializer,
    FundMemberSerializer,
    TransferReceiptSerializer,
    FundSemestralDocumentSerializer,
    TrustAgreementSerializer
)
from apps.fund.serializers.transaction_serializers import TokenTransactionSerializer


class FundCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite gestionar categorías de fondos.
    Proporciona acciones `list`, `create`, `retrieve`, `update` y `destroy`.
    """
    queryset = FundCategory.objects.all()
    serializer_class = FundCategorySerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

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
        user = self.request.user
        
        if user.is_staff:
            queryset = Fund.objects.all()
        else:
            signed_contracts = InvestorContract.objects.filter(
                user=user,
                status=InvestorContract.InvestorContractStatus.CONTRACT_SIGNED
            ).values_list('fund_id', flat=True)  
            
            queryset = Fund.objects.filter(id__in=signed_contracts)
        
        queryset = self.apply_date_filters(queryset)
        return queryset
    
class FundMembersViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = FundMemberSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'fund']
    search_fields = ['user__email', 'fund__name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        # ✅ Solo staff puede acceder a esta información
        if not user.is_staff:
            return InvestorContract.objects.none()
        
        # ✅ OPTIMIZACIÓN: Base queryset mejorado
        queryset = InvestorContract.objects.select_related(
            'user',
            'fund',
            'fund__financial_institution'
        ).prefetch_related(
            'user__groups'
        ).only(
            'id', 'status', 'created_at', 'contract_signed_at',
            'user__id', 'user__email', 'user__first_name', 'user__last_name',
            'fund__id', 'fund__name', 'fund__financial_institution__name'
        ).filter(
            status=InvestorContract.InvestorContractStatus.CONTRACT_SIGNED
        )
        
        # ✅ Filtro opcional por fondo específico
        fund_id = self.request.query_params.get('fund_members')
        if fund_id:
            try:
                fund_id = int(fund_id)
                queryset = queryset.filter(fund_id=fund_id)
            except (ValueError, TypeError):
                # Si fund_id no es válido, devolver queryset vacío
                return InvestorContract.objects.none()
        
        # ✅ Aplicar filtros de fecha
        return self.apply_date_filters(queryset)

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
   
   
# ========================================
# OTROSI VIEWS
# ========================================

class OthersIViewSet(viewsets.ModelViewSet):
    queryset = OthersI.objects.all()
    serializer_class = OthersISerializer
    permission_classes = []


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
    
class TrustAgreementViewSet(DateFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint que permite gestionar contratos fiduciarios de fondos.
    Proporciona acciones `list`, `create`, `retrieve`, `update` y `destroy`.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TrustAgreementSerializer
    authentication_classes = [JWTAuthentication]
    http_method_names = ['get', 'post', 'put', 'delete']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'trustor_name']
    search_fields = ['fund__name']
    ordering_fields = ['created_at',]
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Filtra los contratos fiduciarios para mostrar solo los del usuario autenticado,
        a menos que el usuario sea admin (en cuyo caso muestra todos).
        """
        user = self.request.user
        queryset = TrustAgreement.objects.select_related('fund').filter(fund__user=user)
            
        return self.apply_date_filters(queryset)