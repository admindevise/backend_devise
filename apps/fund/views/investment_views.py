from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_filters.rest_framework import DjangoFilterBackend
from apps.utils.views.Mixins import DateFilterMixin

from apps.fund.models.membership import FundInvestment, InvestmentApplication

from apps.fund.serializers.investment_serializers import (
    InvestmentSerializer,
    InvestmentApplicationSerializer,
    SubmitInvestmentSerializer,
    IAReviewSerializer,
    IASendContractSerializer,
    IAContractSignSerializer
)

class InvestmentApplicationViewSet(DateFilterMixin, viewsets.ModelViewSet):
    serializer_class = InvestmentApplicationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'fund']
    search_fields = ['user__email', 'fund__name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']    
    
    def get_queryset(self):
        user = self.request.user
        queryset = InvestmentApplication.objects.select_related('user', 'fund').all()
        
        if not user.is_staff:
            queryset = queryset.filter(user=user)
        
        return self.apply_date_filters(queryset)

class InvestmentViewSet(DateFilterMixin, viewsets.ModelViewSet):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_methods_names = ['get', 'post']
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['application', 'units_owned']
    search_fields = ['application__user__email', 'application__fund__name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        queryset = FundInvestment.objects.select_related('application__fund', 'application__user').all()
        
        if not user.is_staff:
            queryset = queryset.filter(application__user=user)
            
        return self.apply_date_filters(queryset)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_investment_application(request):
    serializer = SubmitInvestmentSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def under_review_investment_application(request, application_id):
    serializer = IAReviewSerializer(
        data=request.data,
        context={'request': request, 'application_id': application_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_contrat_investment_application(request, application_id):
    serializer = IASendContractSerializer(
        data=request.data,
        context={'request': request, 'application_id': application_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sign_contract_investment_application(request, application_id):
    serializer = IAContractSignSerializer(
        data=request.data,
        context={'request': request, 'application_id': application_id}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

