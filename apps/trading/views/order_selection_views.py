from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from apps.trading.serializers.match_selection_serializers import (
    MatchSelectionSerializer,
    AutoMatchSelectionSerializer,
    MatchSelectionValidationSerializer
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_select_matches(request):
    """Selección automática de matches basada en mejor precio"""
    
    serializer = AutoMatchSelectionSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.process_auto_selection()
        
        # Verificar si es advertencia de unidades insuficientes
        if result.get('warning_type') == 'INSUFFICIENT_UNITS':
            return Response(result, status=status.HTTP_206_PARTIAL_CONTENT)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_matches(request):
    """Selección manual de matches específicos"""
    
    serializer = MatchSelectionSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.process_selection()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_match_selection(request):
    """Valida que una orden puede seleccionar matches y devuelve matches disponibles"""
    
    serializer = MatchSelectionValidationSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'valid': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        matches_info = serializer.get_available_matches()
        
        return Response({
            'valid': True,
            'matches_info': matches_info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'valid': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)