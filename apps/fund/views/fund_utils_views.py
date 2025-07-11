from rest_framework import response, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.fund.serializers.serializer_utils import TokenCounterUserSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_token_count(request):
    """
    Endpoint para contar los tokens del usuario autenticado en un fondo específico.
    Obtiene automáticamente el user_id del token JWT.
    Si es staff, puede especificar un user_id diferente.
    """
    current_user = request.user
    
    # Validar datos del request
    serializer = TokenCounterUserSerializer(data=request.data)
    
    if serializer.is_valid():
        fund_id = serializer.validated_data['fund_id']
        user_id = serializer.validated_data.get('user_id')  # Puede ser None
        
        # Determinar el usuario objetivo
        if current_user.is_staff and user_id:
            # Staff puede consultar cualquier usuario
            target_user_id = user_id
        else:
            # Usuario normal o staff sin especificar user_id
            target_user_id = current_user.id
        
        # Preparar datos para el conteo
        count_data = {
            'user_id': target_user_id,
            'fund_id': fund_id
        }
        
        # Obtener conteo de tokens
        token_count = serializer.get_token_count(count_data)
        
        return response.Response({
            'token_count': token_count,
            'fund_id': fund_id,
            'user_id': target_user_id,
            'email': current_user.email,
            'queried_by_staff': current_user.is_staff and user_id is not None
        }, status=status.HTTP_200_OK)
    
    return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)