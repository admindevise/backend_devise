from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from apps.trading.serializers.payment_serializers import (
    PaymentExecutionSerializer, 
    PaymentValidationSerializer
)

from apps.trading.serializers_flow.payment_serializers import (
    PaymentExecutionSerializer as PayES
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_selection(request):
    """
    Paga la selección específica de matches y ejecuta todas las transacciones automáticamente
    
    Parámetros:
      - purchase_order_id: ID de la orden de compra (requerido)
      - payment_method: Método de pago (opcional, se genera automático)
      - reference: Referencia de pago (opcional, se genera automático)
      - metadata: Metadatos adicionales (opcional)
    
    NOTA: El monto se extrae automáticamente de la selección previa
    """
    
    # Validar y ejecutar usando el serializer
    serializer = PaymentExecutionSerializer(
        data=request.data, 
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Ejecutar pago completo
        result = serializer.execute_payment()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_payment(request):
    """
    Valida que una orden puede ser pagada y devuelve información del pago
    
    Parámetros:
      - purchase_order_id: ID de la orden de compra
    """
    
    serializer = PaymentValidationSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'valid': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        payment_info = serializer.get_payment_info()
        
        return Response({
            'valid': True,
            'payment_info': payment_info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'valid': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
        
# En views
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