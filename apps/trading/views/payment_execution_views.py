from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from apps.trading.serializers_flow.payment_serializers import (
    PaymentExecutionSerializer as PayES
)
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_payment(request):
    """Ejecutar pago usando el nuevo flujo"""
    
    serializer = PayES(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.execute_payment()
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

