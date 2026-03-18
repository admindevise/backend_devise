from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists
from django_filters import rest_framework as django_filters
from apps.utils.views.Mixins import DateFilterMixin

from apps.fund.models.membership import FundInvestment, InvestmentApplication
from apps.fund.models.core import Fund

from apps.fund.serializers.investment_serializers import (
    InvestmentSerializer,
    InvestmentApplicationSerializer,
    InvestmentDashboardSerializer,
    SubmitInvestmentSerializer,
    IAReviewSerializer,
    IASendContractSerializer,
    IAContractSignSerializer
)

# =================================================
# VIEWS DE INVERSIONES
# =================================================
class InvestmentApplicationFilterSet(django_filters.FilterSet):
    application_status = django_filters.ChoiceFilter(
        choices=InvestmentApplication.ApplicationStatus.choices
    )
    
    class Meta:
        model = InvestmentApplication
        fields = ['user', 'fund', 'application_status']


class PendingApplicationViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = InvestmentApplicationSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InvestmentApplicationFilterSet
    search_fields = ['user__email', 'fund__name']
    ordering_fields = ['created_at', 'application_status']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
        
    def get_queryset(self):
        fund_id = self.kwargs.get('fund_id')
        return InvestmentApplication.objects.select_related('user', 'fund').filter(fund_id=fund_id, application_status=InvestmentApplication.ApplicationStatus.PENDING)

class InvestmentViewSet(DateFilterMixin, viewsets.ModelViewSet):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    http_methods_names = ['get', 'post']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['application', 'units_owned', 'application__user__id', 'application__fund__id']
    search_fields = ['application__user__id', 'application__fund__name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        
        queryset = FundInvestment.objects.select_related('application__fund', 'application__user').filter(application__fund_id=fund_id)
        
        if not user.is_staff:
            queryset = queryset.filter(application__user=user)
            
        return self.apply_date_filters(queryset)

class InvestmentDashboardViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = InvestmentDashboardSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    http_methods_names = ['get']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['application__fund']
    search_fields = ['application__user__email', 'application__fund__name']
    ordering_fields = ['created_at', 'total_amount', 'units_owned']
    ordering = ['-created_at']
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')
        
        queryset = FundInvestment.objects.select_related('application__fund', 'application__user').filter(application__fund_id=fund_id)
        
        if not user.is_staff:
            queryset = queryset.filter(application__user=user)
            
        return self.apply_date_filters(queryset)

# =================================================
# ACCIONES PARA CAMBIAR EL ESTADO DE LA SOLICITUD
# =================================================
class InvestmentApplicationViewSet(DateFilterMixin, viewsets.ModelViewSet):
    serializer_class = InvestmentApplicationSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    http_method_names = ['get', 'post']

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InvestmentApplicationFilterSet
    search_fields = ['user__email', 'fund__name']
    ordering_fields = ['created_at', 'application_status']
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        fund_id = self.kwargs.get('fund_id')

        queryset = InvestmentApplication.objects.select_related('user', 'fund').filter(fund_id=fund_id)

        if not user.is_staff:
            queryset = queryset.filter(user=user)

        return self.apply_date_filters(queryset)

    @action(detail=False, methods=['post'], url_path='submit')
    def submit(self, request, **kwargs):
        """
        POST /fund/<fund_id>/investment-application/submit/
        """
        serializer = SubmitInvestmentSerializer(
            data=request.data,
            context={
                'request': request,
                'fund_id': self.kwargs.get('fund_id')
            }
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='under-review')
    def under_review(self, request, pk=None, **kwargs):
        """
        POST /fund/<fund_id>/investment-application/<pk>/under-review/
        """
        serializer = IAReviewSerializer(
            data=request.data,
            context={
                'request': request,
                'application_id': pk
            }
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='send-contract')
    def send_contract(self, request, pk=None, **kwargs):
        """
        POST /fund/<fund_id>/investment-application/<pk>/send-contract/
        """
        serializer = IASendContractSerializer(
            data=request.data,
            context={
                'request': request,
                'application_id': pk
            }
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='sign-contract')
    def sign_contract(self, request, pk=None, **kwargs):
        """
        POST /fund/<fund_id>/investment-application/<pk>/sign-contract/
        """
        serializer = IAContractSignSerializer(
            data=request.data,
            context={
                'request': request,
                'application_id': pk
            }
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

