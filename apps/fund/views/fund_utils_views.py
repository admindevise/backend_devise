from rest_framework import response, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.fund.serializers.serializer_utils import TokenCounterUserSerializer, AISerializer

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
            'token_count': token_count['tokens_available'],
            'tokens_reserved': token_count['tokens_reserved'],
            'tokens_total': token_count['tokens_total'],
            'fund_id': fund_id,
            'user_id': target_user_id,
            'email': current_user.email,
            'queried_by_staff': current_user.is_staff and user_id is not None
        }, status=status.HTTP_200_OK)
    
    return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


import requests
API_KEY = "AIzaSyAk6zI1vc6_Oq9DVyF0H7uhX1GsQN3e1cw"
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate_content(request):
    """
    Endpoint para generar contenido utilizando la API de Gemini.
    Requiere un prompt en el cuerpo de la solicitud.
    """
    serializer = AISerializer(data=request.data)
    
    if serializer.is_valid():
        prompt = serializer.validated_data['prompt']
        
        headers = {
            'X-goog-api-key': API_KEY,
            'Content-Type': 'application/json'
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        api_response = requests.post(url, headers=headers, json=data)
        
        if api_response.status_code == 200:
            # ✅ EXTRAER Y FORMATEAR EL TEXTO
            gemini_data = api_response.json()
            
            # Extraer el texto de la respuesta
            ai_text = ""
            if 'candidates' in gemini_data and len(gemini_data['candidates']) > 0:
                candidate = gemini_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        ai_text = parts[0]['text']
            
            # ✅ LIMPIAR Y FORMATEAR EL TEXTO
            formatted_text = _clean_text(ai_text)
            
            # ✅ RESPUESTA LIMPIA Y FORMATEADA
            clean_response = {
                "success": True,
                "prompt": prompt,
                "response": formatted_text,
                "raw_response": ai_text  # Por si necesitas el original
            }
            
            return response.Response(clean_response, status=status.HTTP_200_OK)
        else:
            return response.Response(api_response.json(), status=api_response.status_code)
    
    return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def _clean_text(text):
    """
    Limpia el texto removiendo caracteres de formato no deseados
    """
    if not text:
        return ""
    
    # ✅ LIMPIAR CARACTERES DE FORMATO
    cleaned = text.replace('\\n', '\n')  # Convertir \n literales a saltos de línea reales
    cleaned = cleaned.replace('\\t', ' ')  # Convertir tabs a espacios
    cleaned = cleaned.replace('\\r', '')   # Remover carriage returns
    cleaned = cleaned.replace('\r\n', '\n')  # Normalizar line endings
    cleaned = cleaned.replace('\r', '\n')    # Convertir CR a LF
    
    # ✅ LIMPIAR ESPACIOS EXCESIVOS
    import re
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Máximo 2 saltos de línea consecutivos
    cleaned = re.sub(r' {2,}', ' ', cleaned)      # Máximo 1 espacio consecutivo
    cleaned = cleaned.strip()                     # Remover espacios al inicio y final
    
    return cleaned