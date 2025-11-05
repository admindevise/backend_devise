import re
import json
import requests
from django.db.models import Sum, Count, Q

from rest_framework import response, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes

from apps.fund.utils import _generate_customer_support_prompt
from apps.fund.serializers.utils_serializers import (
    AISerializer,
    CustomerSupportSerializer,
    TokenCounterUserSerializer
)
from apps.fund.models.membership import (
    FundInvestment,
)

# =======================================
# TESTING SERVICE

@api_view(['GET'])
@permission_classes([AllowAny])
def testing(request):
    from apps.fund.services.kpis.fund_calculations import FundCalculationService
    from apps.fund.models.membership import FundInvestment
    from apps.fund.models.core import Fund
    
    investment = FundInvestment.objects.get(id=9)
    fund=Fund.objects.get(id=1)
    calc_service = FundCalculationService(fund)
    return str(calc_service.calculate_tkn_value_change(request.user)) 
    
    

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


API_KEY="AIzaSyAk6zI1vc6_Oq9DVyF0H7uhX1GsQN3e1cw"
URL_GEMINI="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate_content(request):
    """
    Endpoint para generar contenido de soporte al cliente usando la API de Gemini.
    Especializado en asistencia a inversionistas y consultas de datos financieros.
    """
    serializer = CustomerSupportSerializer(data=request.data)
    
    if serializer.is_valid():
        # Generar prompt de soporte usando los datos del serializer
        enriched_data = _enrich_user_data(request.user, serializer.validated_data)
        
        prompt = _generate_customer_support_prompt(enriched_data)
        
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
        
        api_response = requests.post(URL_GEMINI, headers=headers, json=data)
        
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
            
            # ✅ EXTRAER Y PARSEAR JSON DE LA RESPUESTA
            parsed_json = _extract_and_parse_json(formatted_text)
            
            # ✅ RESPUESTA LIMPIA Y FORMATEADA
            clean_response = {
                "success": True,
                "prompt": prompt,
                "response": parsed_json if parsed_json else formatted_text,
                "raw_response": ai_text,
                "input_data": enriched_data,
                "is_json": parsed_json is not None,
                "support_type": "customer_service"
            }
            
            return response.Response(clean_response, status=status.HTTP_200_OK)
        else:
            return response.Response(api_response.json(), status=api_response.status_code)
    
    return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


""" @api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate_content(request):
    
    #Endpoint para generar contenido utilizando la API de Gemini.
    #Genera automáticamente un prompt para valoración de bienes raíces comerciales
    #usando los datos proporcionados.
    
    serializer = AISerializer(data=request.data)
    
    if serializer.is_valid():
        # Generar prompt de valoración usando los datos del serializer
        prompt = _generate_cre_valuation_prompt(serializer.validated_data)
        
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
            
            # ✅ EXTRAER Y PARSEAR JSON DE LA RESPUESTA
            parsed_json = _extract_and_parse_json(formatted_text)
            
            # ✅ RESPUESTA LIMPIA Y FORMATEADA
            clean_response = {
                "success": True,
                "prompt": prompt,
                "response": parsed_json if parsed_json else formatted_text,  # JSON parseado o texto original
                "raw_response": ai_text,  # Por si necesitas el original
                "input_data": serializer.validated_data,  # Datos de entrada para referencia
                "is_json": parsed_json is not None  # Indica si se pudo parsear como JSON
            }
            
            return response.Response(clean_response, status=status.HTTP_200_OK)
        else:
            return response.Response(api_response.json(), status=api_response.status_code)
    
    return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) """

def _enrich_user_data(self, user, serializer_data):
    """
    Enriquece los datos del serializer con información en tiempo real de la BD
    """
    user = self.request.user
    try:
        # ✅ CONSULTAR INVERSIONES DEL USUARIO
        user_investments = FundInvestment.objects.filter(investor=user).select_related('fund')
        
        # ✅ CONSULTAR APLICACIONES DEL USUARIO
        #user_applications = FundApplication.objects.filter(applicant=user).select_related('fund')
        
        # ✅ CALCULAR ESTADÍSTICAS
        investment_stats = user_investments.aggregate(
            total_invested=Sum('invested_amount'),
            active_investments=Count('id', filter=Q(status='active')),
            total_investments=Count('id')
        )
        
        # ✅ OBTENER ÓRDENES ACTIVAS (si existe el modelo)
        try:
            from apps.trading.models.core_models import PurchaseOrder
            active_orders = PurchaseOrder.objects.filter(
                supplier_user=user, 
                status__in=['pending', 'processing']
            ).count()
        except ImportError:
            active_orders = 0
        
        # ✅ CONSTRUIR DATOS ENRIQUECIDOS
        enriched_data = serializer_data.copy()
        enriched_data['user_data'] = {
            'user_id': user.id,
            'user_email': user.email,
            'total_investments': investment_stats['total_invested'] or 0,
            'active_investments_count': investment_stats['active_investments'] or 0,
            'total_investments_count': investment_stats['total_investments'] or 0,
            'active_orders': active_orders,
            'investment_details': [
                {
                    'fund_name': inv.fund.name,
                    'fund_id': inv.fund.id,
                    'invested_amount': float(inv.invested_amount),
                    'status': inv.status,
                    'investment_date': inv.created_at.strftime('%Y-%m-%d') if inv.created_at else None
                }
                for inv in user_investments[:5]  # Últimas 5 inversiones
            ],
            'application_details': [
                {
                    'fund_name': app.fund.name,
                    'fund_id': app.fund.id,
                    'requested_amount': float(app.requested_amount),
                    'status': app.status,
                    'application_date': app.created_at.strftime('%Y-%m-%d') if app.created_at else None
                }
                for app in user_applications[:5]  # Últimas 5 aplicaciones
            ],
            'last_activity': user_investments.first().created_at.strftime('%Y-%m-%d %H:%M') if user_investments.exists() else 'Sin actividad',
        }
        
        return enriched_data
        
    except Exception as e:
        # Si hay error, usar datos originales
        print(f"Error enriching user data: {e}")
        return serializer_data

def _extract_and_parse_json(text):
    
    #Extrae y parsea el JSON de la respuesta de Gemini
    
    if not text:
        return None
    
    try:
        # Buscar el bloque JSON entre ```json y ```
        json_pattern = r'```json\s*\n(.*?)\n```'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if match:
            json_text = match.group(1)
            # Parsear el JSON
            return json.loads(json_text)
        else:
            # Si no hay bloque ```json, intentar parsear todo el texto como JSON
            return json.loads(text)
            
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None

def _clean_text(text):
    
    #Limpia el texto removiendo caracteres de formato no deseados
    
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
