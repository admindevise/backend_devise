from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from apps.utils.views.Mixins import DateFilterMixin
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists

from apps.financial_institution.models import FinancialInstitution
from apps.fund.models.membership import InvestorContract
from apps.fund.models.core import (
    Fund,
    OthersI,
    FundCategory,
    TrustAgreement,
    TypeSemestralDocument,
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
    TypeSemestralDocumentSerializer,
    FundSemestralDocumentSerializer,
    TrustAgreementSerializer
)
from apps.fund.serializers.transaction_serializers import TokenTransactionSerializer

# ============================================================================
# Fund Core Views
# ============================================================================
class FundCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite gestionar categorías de fondos.
    Proporciona acciones `list`, `create`, `retrieve`, `update` y `destroy`.
    """
    queryset = FundCategory.objects.all()
    serializer_class = FundCategorySerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        fund_id = self.kwargs.get('fund_id')
        if fund_id:
            validate_entity_exists(Fund, 'Fideicomiso', fund_id)
        super().initial(request, *args, **kwargs)

class FundViewSet(DateFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Fund to be viewed or edited.
    
    Este ViewSet proporciona automáticamente acciones `list`, `create`, `retrieve`,
    `update` y `destroy`.
    
    Cada operación genera registros de auditoría para seguimiento completo.
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    serializer_class = FundSerializer
    http_method_names = ['get', 'post']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        validate_entity_exists(FinancialInstitution, 'Institución Financiera', self.kwargs.get('fi_id'))
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('pk'))

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
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'fund']
    search_fields = ['user__email', 'fund__name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        
        if not user.is_staff:
            return InvestorContract.objects.none()
        
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
            fund=fund_id,
            status=InvestorContract.InvestorContractStatus.CONTRACT_SIGNED
        )
        
        # Filtro opcional por fondo específico
        if fund_id:
            try:
                fund_id = int(fund_id)
                queryset = queryset.filter(fund_id=fund_id)
            except (ValueError, TypeError):
                # Si fund_id no es válido, devolver queryset vacío
                return InvestorContract.objects.none()
        
        # Aplicar filtros de fecha
        return self.apply_date_filters(queryset)


# ============================================================================
# Fund Semestral Documents Views
# ============================================================================
class FundTypeSemestralDocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite gestionar tipos de documentos semestrales de fondos.
    Proporciona acciones `list`, `create`, `retrieve`, `update` y `destroy`.
    """
    queryset = TypeSemestralDocument.objects.all()
    serializer_class = TypeSemestralDocumentSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

# Filter
class FundSemestralDocumentFilterSet(django_filters.FilterSet):
    fund = django_filters.NumberFilter(field_name='fund__id')
    document_type = django_filters.NumberFilter(field_name='document_type__id')
    periodicity = django_filters.ChoiceFilter(choices=FundSemestralDocument.PeriodicityChoices.choices)
    cycle = django_filters.NumberFilter(field_name='cycle')
    
    class Meta:
        model = FundSemestralDocument
        fields = ['fund', 'period_start_date', 'period_end_date', 'document_type', 'periodicity', 'cycle'] 

class FundSemestralDocumentViewSet(DateFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint que permite gestionar documentos semestrales de fondos.
    Proporciona acciones `list`, `create`, `retrieve`, `update` y `destroy`.
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    serializer_class = FundSemestralDocumentSerializer
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ['get', 'post', 'delete', 'patch']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FundSemestralDocumentFilterSet
    search_fields = ['document']
    ordering_fields = ['uploaded_date']
    ordering = ['-uploaded_date']
    date_field = 'uploaded_date'  # Campo de fecha para filtros de fecha
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['fund'] = Fund.objects.get(id=self.kwargs.get('fund_id'))
        return context
    
    def get_queryset(self):
        """
        Filtra los documentos para mostrar solo los del usuario autenticado,
        a menos que el usuario sea admin (en cuyo caso muestra todos).
        """
        user = self.request.user
        queryset = FundSemestralDocument.objects.select_related('fund').filter(fund__user=user)
        
        return self.apply_date_filters(queryset)

    @action(detail=False, methods=['get'], url_path='cycle-options')
    def cycle_options(self, request, **kwargs):
        """
        Retorna las opciones de ciclos disponibles según la periodicidad.

        Query params:
        - periodicity: monthly, quarterly, semi_annually, annually

        Ejemplo: GET /api/fund/{fund_id}/semestral-documents/cycle-options/?periodicity=monthly
        """
        periodicity = request.query_params.get('periodicity')

        if not periodicity:
            return Response({
                'error': 'El parámetro "periodicity" es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)

        cycle_labels = FundSemestralDocumentSerializer.CYCLE_LABELS.get(periodicity)

        if not cycle_labels:
            return Response({
                'error': f'Periodicidad inválida: {periodicity}'
            }, status=status.HTTP_400_BAD_REQUEST)

        options = [
            {'value': cycle, 'label': label}
            for cycle, label in cycle_labels.items()
        ]

        return Response({
            'periodicity': periodicity,
            'options': options
        }, status=status.HTTP_200_OK)    
   
   
# ============================================================================
# OTROSI VIEWS
# ============================================================================
class OthersIViewSet(viewsets.ModelViewSet):
    queryset = OthersI.objects.all()
    serializer_class = OthersISerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

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
    permission_classes = [IsAuthenticated, RegistryPermission]
    serializer_class = TransferReceiptSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'fund']
    search_fields = ['transaction_id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        
        queryset = TransferReceipt.objects.select_related('user', 'fund').filter(fund_id=fund_id)
        
        if not user.is_staff:
            queryset = queryset.filter(user=user)
        
        queryset = self.apply_date_filters(queryset)
        return queryset

class FundTokenViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para gestionar tokens de fondos.
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    serializer_class = FundTokenSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'status', 'created_by', 'owner_user', 'reserved_for_sale', 'reserved_at']
    search_fields = ['token_id', 'nickname']
    ordering_fields = ['created_at', 'token_id']
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        
        queryset = FundToken.objects.select_related('fund', 'created_by', 'owner_user').filter(fund_id=fund_id)
        
        if not user.is_staff:
            queryset = queryset.filter(created_by=user)
            
        queryset = self.apply_date_filters(queryset)
        return queryset

class TokenTransactionViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para gestionar transacciones de tokens.
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    serializer_class = TokenTransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'from_user', 'to_user']
    search_fields = ['kaleido_transaction_id', 'description']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        
        queryset = TokenTransaction.objects.select_related('fund', 'from_user', 'to_user').filter(fund_id=fund_id)
        
        if not user.is_staff:
            queryset = queryset.filter(from_user=user)
            
        queryset = self.apply_date_filters(queryset)
        
        return queryset
    
class TrustAgreementViewSet(DateFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint que permite gestionar contratos fiduciarios de fondos.
    Proporciona acciones `list`, `create`, `retrieve`, `update` y `destroy`.
    """
    permission_classes = [IsAuthenticated, RegistryPermission]
    serializer_class = TrustAgreementSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fund', 'trustor_name']
    search_fields = ['fund__name']
    ordering_fields = ['created_at',]
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        """
        Filtra los contratos fiduciarios para mostrar solo los del usuario autenticado,
        a menos que el usuario sea admin (en cuyo caso muestra todos).
        """
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        
        queryset = TrustAgreement.objects.select_related('fund').filter(fund_id=fund_id, fund__user=user)
            
        return self.apply_date_filters(queryset)