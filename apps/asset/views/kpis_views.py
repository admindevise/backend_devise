from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.asset.serializers.kpi_serializers import (
    AssetNOICalculationSerializer,
    AssetNOISummarySerializer,
    AssetCapRateCalculationSerializer,
    AssetOutputValueCalculationSerializer,
    AssetFreeCashFlowCalculationSerializer,
    AssetCashOnCashCalculationSerializer,
    AssetDividendYieldCalculationSerializer,
    AssetDividendYieldMovingAverageSerializer,
    AssetIRRCalculationSerializer,
    AssetMOICCalculationSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_asset_noi(request):
    """
    Calcula NOI de un asset.
    
    Body:
        {
            "asset_id": 1,
            "period_year": 2024,  // opcional
            "period_month": 6,     // opcional
            "months_back": 12      // opcional (default: 12)
        }
    """
    serializer = AssetNOICalculationSerializer(
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
def get_asset_noi_summary(request):
    """
    Obtiene resumen de NOI con análisis de tendencias.
    
    Body:
        {
            "asset_id": 1,
            "months": 12  // opcional (default: 12)
        }
    """
    serializer = AssetNOISummarySerializer(
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
def calculate_asset_cap_rate(request):
    """
    Calcula Cap Rate de un asset.
    
    Cap Rate = (NOI Anual / Valor del Activo) * 100
    
    Body:
        {
            "asset_id": 1
        }
    
    Response:
        {
            "success": true,
            "data": {
                "cap_rate_metrics": {
                    "cap_rate": 7.0,
                    "noi_anual": 84000.0,
                    "valor_activo": 1200000.0,
                    "interpretation": "Cap Rate moderado-alto...",
                    "risk_level": "moderate"
                },
                ...
            },
            "message": "Cap Rate calculado: 7.00% - Moderate Risk"
        }
    """
    serializer = AssetCapRateCalculationSerializer(
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
def calculate_output_value(request):
    serializer = AssetOutputValueCalculationSerializer(
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
def calculate_asset_free_cash_flow(request):
    """
    Calcula Free Cash Flow de un asset.
    
    FCF = NOI + Ingresos no operativos - Gastos no operativos - CAPEX - Deuda
    
    Body (últimos 12 meses):
        {
            "asset_id": 1
        }
    
    Body (período específico):
        {
            "asset_id": 1,
            "period_year": 2024,
            "period_month": 6
        }
    
    Response:
        {
            "success": true,
            "data": {
                "fcf_metrics": {
                    "free_cash_flow": 40000.0,
                    "fcf_per_token": 400.0,
                    "fcf_margin_percentage": 47.62
                },
                "fcf_components": {
                    "total_noi": 84000.0,
                    "non_operating_income": 0.0,
                    "non_operating_expenses": 0.0,
                    "capex": 4000.0,
                    "debt_payment": 40000.0
                },
                ...
            },
            "message": "FCF positivo: $40,000.00 COP ($400.00 por token)..."
        }
    """
    serializer = AssetFreeCashFlowCalculationSerializer(
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
def calculate_asset_cash_on_cash(request):
    """
    Calcula Cash on Cash Return de un asset.
    
    Cash on Cash = (FCF Anual / Capital Invertido) × 100
    
    Body:
        {
            "asset_id": 1,
            "months_back": 12,
            "include_breakdown": false
        }
    
    Response:
        {
            "success": true,
            "data": {
                "cash_on_cash_metrics": {
                    "cash_on_cash_percentage": 10.0,
                    "fcf_anual": 40000.0,
                    "capital_invertido": 400000.0,
                    "interpretation": "Excelente retorno...",
                    "performance_level": "excellent"
                },
                "additional_metrics": {
                    "payback_period_years": 10.0,
                    "monthly_fcf_average": 3333.33
                },
                ...
            },
            "message": "Cash on Cash calculado: 10.00% - Excellent"
        }
    """
    serializer = AssetCashOnCashCalculationSerializer(
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
def calculate_asset_dividend_yield(request):
    """
    Calcula Dividend Yield de un asset.
    
    Dividend Yield = (Dividendo por Token / Valor Compra Token) × 100
    
    Body (anualizado):
        {
            "asset_id": 1
        }
    
    Body (período específico):
        {
            "asset_id": 1,
            "period_year": 2024,
            "period_month": 12
        }
    """
    serializer = AssetDividendYieldCalculationSerializer(
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
def calculate_asset_dividend_yield_moving_average(request):
    """
    Calcula Dividend Yield Promedio Móvil de un asset.
    
    Body:
        {
            "asset_id": 1,
            "months_back": 12,
            "include_monthly_breakdown": true
        }
    """
    serializer = AssetDividendYieldMovingAverageSerializer(
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
def calculate_asset_irr(request):
    """
    Calcula TIR (Tasa Interna de Retorno / IRR) de un asset.
    
    Body (con parámetros manuales):
        {
            "asset_id": 1,
            "annual_dividends_per_token": 400,
            "exit_price_per_token": 4600,
            "holding_period_years": 5
        }
    
    Body (con datos históricos):
        {
            "asset_id": 1,
            "use_historical_dividends": true,
            "holding_period_years": 5
        }
    """
    serializer = AssetIRRCalculationSerializer(
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
def calculate_asset_moic(request):
    """
    Calcula MOIC (Múltiplo de Inversión) de un asset.
    
    Body (con parámetros manuales):
        {
            "asset_id": 1,
            "total_dividends_received": 2000,
            "exit_price_per_token": 4600,
            "holding_period_years": 5
        }
    
    Body (con datos históricos):
        {
            "asset_id": 1,
            "use_historical_dividends": true,
            "holding_period_years": 5
        }
    """
    serializer = AssetMOICCalculationSerializer(
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
        
        
        