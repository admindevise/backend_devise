from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from apps.trading.models.core_models import PurchaseOrder
from apps.fund.models.core import Fund
from apps.trading.views.utils_views import validate_entity_exists
from apps.trading.serializers_flow.payment_serializers import (
    PaymentExecutionSerializer as PayES
)
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_payment(request, fund_id, order_id):
    """Ejecutar pago usando el nuevo flujo"""
    validate_entity_exists(Fund, 'Fideicomiso', fund_id)
    validate_entity_exists(PurchaseOrder, 'Orden de compra', order_id)
    
    serializer = PayES(
        data=request.data,
        context={
            'request': request,
            'fund_id': fund_id,
            'order_id': order_id
        }
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

