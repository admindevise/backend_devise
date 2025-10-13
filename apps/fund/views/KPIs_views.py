from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics

from apps.fund.serializers.KPIs_serializers import (
    TokenValueChangeSerializer,
    FundDistributionsSummary12MSerializer,
    YieldFromDistributionsSerializer,
    UserPriceChangeSerializer,
    UserRent12mPerUnitSerializer,
    UserCashOnCashSerializer,
    UserCurrentValueSerializer,
    UserSimpleTotalReturnSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_token_value_change(request):
    """
    Vista para calcular el cambio de valor de tokens de un usuario.
    """
    serializer = TokenValueChangeSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_fund_distributions_12m(request):
    """
    Vista para obtener suma de distribuciones de los últimos 12 meses.
    """
    serializer = FundDistributionsSummary12MSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
        

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_yield_from_distributions(request):
    """
    Calcula el rendimiento de una inversión basado en las distribuciones de los últimos 12 meses.
    
    Utiliza la fórmula: Rendimiento = (Total distribuciones 12M / tkn_cost)
    
    **Parámetros requeridos:**
    - fund_id: ID del fondo
    - investment_id: ID de la inversión específica
    """
    
    serializer = YieldFromDistributionsSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)        

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_price_change(request):
    serializer = UserPriceChangeSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)          

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_rent_12m_per_unit(request):
    serializer = UserRent12mPerUnitSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)          
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_cash_on_cash(request):
    serializer = UserCashOnCashSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)                 
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_current_value(request):
    """
    Vista para calcular el valor actual de inversión de un usuario.
    """
    serializer = UserCurrentValueSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)        
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_simple_total_return(request):
    """
    Vista para calcular el valor actual de inversión de un usuario.
    """
    serializer = UserSimpleTotalReturnSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.save()
        
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)           
        
        
        