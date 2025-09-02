"""
Utility functions for Fund operations
"""

from django.db.models import Q
from apps.fund.models.tokens import FundToken
from django.db import transaction

def get_next_available_token(fund_id, user=None):
    """
        Get the next available token (oldest by created_at) for purchase.
        
        Args:
            fund_id (int): ID of the fund to get token from
            user: User object for validation (optional)
            
        Returns:
            FundToken: Next available token object
            
        Raises:
            ValueError: If no tokens are available
    """
    try:
        # Get the oldest available token
        token = FundToken.objects.filter(
            fund_id=fund_id,
            status=True,
        ).filter(
            Q(owner_user__is_staff=True)
        ).order_by('created_at').first()
        
        if not token:
            raise ValueError(f"No available tokens found for fund {fund_id}")
            
        return token
        
    except Exception as e:
        raise ValueError(f"Error getting next available token: {str(e)}")

def reserve_next_available_token(fund_id, user):
    """
        Reserve the next available token for a user by setting the owner_user field.
        Uses select_for_update to prevent race conditions.
        
        Args:
            fund_id (int): ID of the fund
            user: User object to assign as owner
            
        Returns:
            FundToken: Reserved token object
            
        Raises:
            ValueError: If no tokens are available
    """
    with transaction.atomic():
        # Get oldest available token with select_for_update to prevent race conditions
        token = FundToken.objects.select_for_update().filter(
            fund_id=fund_id,
            status=True
        ).filter(
            Q(owner_user__is_staff=True)
        ).order_by('created_at').first()
        
        if not token:
            raise ValueError(f"No available tokens found for fund {fund_id}")
        
        # Reserve the token
        token.owner_user = user
        token.save(update_fields=['owner_user'])
        
        return token

#+ ========================================
#+ Métodos públicos del servicio
#+ ========================================

def get_next_available_token_trading(fund_id, user=None):
    """
    Get the next available token for trading (oldest by created_at).
    
    Args:
        fund_id (int): ID of the fund to get token from
        user: User object for validation (optional)
        
    Returns:
        FundToken: Next available token object
        
    Raises:
        ValueError: If no tokens are available
    """
    try:
        # Get the oldest available token
        token = FundToken.objects.filter(
            fund_id=fund_id,
            status=True,
            owner_user__isnull=False
        ).order_by('created_at').first()
        
        if not token:
            raise ValueError(f"No available tokens found for fund {fund_id}")
            
        return token
        
    except Exception as e:
        raise ValueError(f"Error getting next available token for trading: {str(e)}")

def reserve_next_available_token_trading(fund_id, user):
    """
    Reserve the next available token for trading by setting the owner_user field.
    Uses select_for_update to prevent concurrent access.
    Args:
        fund_id (int): ID of the fund
        user: User object to assign as owner
    Returns:
        FundToken: Reserved token object
    Raises:
        ValueError: If no tokens are available
    """
    with transaction.atomic():
        # Get oldest available token with select_for_update to
        token = FundToken.objects.select_for_update().filter(
            fund_id=fund_id,
            status=True,
            owner_user__isnull=False
        ).order_by('created_at').first()
        
        if not token:
            raise ValueError(f"No available tokens found for fund {fund_id}")

        # Reserve the token
        token.owner_user = user
        token.save(update_fields=['owner_user'])
        
        return token


def get_oldest_available_tokens(fund_id, quantity=None):
    """
    Get the oldest available tokens in ascending order from FundTokens for multi-token purchases.
    
    Available tokens are defined as:
    - status=True (active)
    - owner_user=admin (tokens owned by admin are available for purchase)
    
    Args:
        fund_id (int): ID of the fund to get tokens from
        quantity (int, optional): Maximum number of tokens to return. 
                                 If None, returns all available tokens.
    
    Returns:
        QuerySet: QuerySet of FundToken objects ordered by created_at (oldest first)
        
    Example:
        # Get 5 oldest available tokens for fund with ID 1
        tokens = get_oldest_available_tokens(fund_id=1, quantity=5)
        
        # Get all available tokens for fund with ID 1
        all_tokens = get_oldest_available_tokens(fund_id=1)
        
        # Convert to list of token IDs for use in purchase operations
        token_ids = list(tokens.values_list('token_id', flat=True))
    """
    # CORREGIDO: Buscar tokens que pertenezcan al admin (disponibles para compra)
    # Asumiendo que el admin tiene is_staff=True o user_id=24
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        # Opción 1: Buscar por usuario admin con is_staff=True
        admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
        if not admin_user:
            # Opción 2: Fallback al usuario con ID 24 si no se encuentra admin
            admin_user = User.objects.filter(id=24).first()
        
        if not admin_user:
            raise ValueError("No se encontró usuario admin para identificar tokens disponibles")
            
        queryset = FundToken.objects.filter(
            fund_id=fund_id,
            status=True,  # Active tokens only
            owner_user=admin_user  # Tokens owned by admin are available for purchase
        ).order_by('created_at')  # Oldest first (ascending order)
        
        if quantity is not None:
            queryset = queryset[:quantity]
        
        return queryset
        
    except Exception as e:
        raise ValueError(f"Error getting available tokens: {str(e)}")

def get_available_tokens_count(fund_id):
    """
    Get the count of available tokens for a specific fund.
    
    Args:
        fund_id (int): ID of the fund to count available tokens for
        
    Returns:
        int: Number of available tokens
    """
    # CORREGIDO: Contar tokens que pertenezcan al admin
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        # Buscar usuario admin
        admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(id=24).first()
        
        if not admin_user:
            return 0
            
        return FundToken.objects.filter(
            fund_id=fund_id,
            status=True,
            owner_user=admin_user  # Tokens owned by admin are available
        ).count()
        
    except Exception as e:
        return 0

def check_token_availability(fund_id, required_quantity):
    """
    Check if a fund has enough available tokens for a purchase.
    
    Args:
        fund_id (int): ID of the fund to check
        required_quantity (int): Number of tokens required
        
    Returns:
        dict: Dictionary with availability information
            - available (bool): Whether enough tokens are available
            - available_count (int): Number of available tokens
            - required_count (int): Number of tokens required
            - shortage (int): Number of tokens short (0 if enough available)
    """
    available_count = get_available_tokens_count(fund_id)
    
    return {
        'available': available_count >= required_quantity,
        'available_count': available_count,
        'required_count': required_quantity,
        'shortage': max(0, required_quantity - available_count)
    }

def reserve_oldest_tokens(fund_id, quantity, user):
    """
    Reserve the oldest available tokens for a user by setting the owner_user field.
    This is useful for multi-token purchases to prevent race conditions.
    
    Args:
        fund_id (int): ID of the fund
        quantity (int): Number of tokens to reserve
        user: User object to assign as owner
        
    Returns:
        list: List of reserved FundToken objects
        
    Raises:
        ValueError: If not enough tokens are available
    """
    from django.db import transaction
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    with transaction.atomic():
        # CORREGIDO: Buscar tokens del admin disponibles para reserva
        admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(id=24).first()
        
        if not admin_user:
            raise ValueError("No se encontró usuario admin para identificar tokens disponibles")
        
        # Get oldest available tokens with select_for_update to prevent race conditions
        available_tokens = FundToken.objects.select_for_update().filter(
            fund_id=fund_id,
            status=True,
            owner_user=admin_user  # Tokens owned by admin are available
        ).order_by('created_at')[:quantity]
        
        available_tokens_list = list(available_tokens)
        
        if len(available_tokens_list) < quantity:
            raise ValueError(
                f"Not enough tokens available. Requested: {quantity}, "
                f"Available: {len(available_tokens_list)}"
            )
        
        # Update owner_user for all selected tokens
        token_ids = [token.id for token in available_tokens_list]
        FundToken.objects.filter(id__in=token_ids).update(owner_user=user)
        
        # Refresh objects to get updated data
        return list(FundToken.objects.filter(id__in=token_ids))


#+ ========================================
#+ Metodos para AI y Generación de Contenido
#+ ========================================

def _generate_cre_valuation_prompt(data):
    """
    Genera el prompt para valoración de bienes raíces usando los datos proporcionados
    """
    city_name = data['city_name']
    latitude = data['latitude']
    longitude = data['longitude']
    asset_type = data['asset_type']
    square_footage = data['square_footage']
    year_built = data['year_built']
    occupancy_rate = data['occupancy_rate']
    net_operating_income = data['net_operating_income']
    
    return f"""Usted es un experto de clase mundial en valoración de bienes raíces comerciales (CRE) en Colombia con acceso a extensos datos de mercado. Un usuario ha proporcionado detalles de su activo y ha seleccionado una ubicación precisa en Google Maps. Su tarea es proporcionar un informe de valoración completo en formato JSON.

**Contexto de Ubicación:**
*   Ciudad: {city_name}, Colombia
*   Coordenadas Geográficas (Lat/Lng): El usuario ha señalado una ubicación precisa en ({latitude:.6f}, {longitude:.6f}). Utilice estas coordenadas para inferir la calidad y el valor de la zona.

**Detalles del Activo:**
*   Tipo: {asset_type}
*   Área: {square_footage} m²
*   Año de Construcción: {year_built}
*   Tasa de Ocupación: {occupancy_rate}%
*   Ingreso Operativo Neto Anual (NOI): {net_operating_income:,} COP

**Su Respuesta DEBE ser un único objeto JSON con la siguiente estructura. No incluya ningún otro texto o formato markdown fuera del propio objeto JSON:**

```json
{{
  "estimatedValue": {{
    "low": 15000000000,
    "high": 18000000000,
    "currency": "COP"
  }},
  "valuationBreakdown": {{
    "capRate": 5.5,
    "pricePerSqft": 3500000
  }},
  "marketAnalysis": {{
    "summary": "string",
    "opportunities": ["string"],
    "risks": ["string"]
  }},
  "zonalMetrics": [
    {{
      "name": "string",
      "value": "string",
      "position": {{ "lat": 4.610, "lng": -74.082 }}
    }}
  ]
}}
```

**Instrucciones y Restricciones:**
1.  Todos los valores numéricos en el JSON deben ser números reales, no cadenas de texto.
2.  Los valores "low" y "high" para estimatedValue deben ser representaciones enteras realistas en pesos colombianos (COP) (ej., 15000000000 para $15 mil millones COP).
3.  Calcule 'capRate' como ({net_operating_income:,} / ((low + high) / 2)) * 100.
4.  Calcule 'pricePerSqft' (que representa el precio por metro cuadrado) como (((low + high) / 2) / {square_footage}).
5.  El resumen, las oportunidades y los riesgos del marketAnalysis deben ser perspicaces y específicos para el tipo de activo y el contexto de la ubicación ({city_name}, {latitude}, {longitude}).
6.  Genere de 3 a 4 'zonalMetrics'. Su 'position' debe tener coordenadas 'lat' y 'lng' plausibles que estén cerca (en un radio de ~1-2 km) de la ubicación seleccionada por el usuario ({latitude}, {longitude}), pero sin superponerse. Las métricas deben ser relevantes para el tipo de activo (ej., 'Vacancia Comercial Promedio', 'Índice de Tráfico Peatonal', 'Ingreso Promedio del Hogar').

Basándose en estos datos específicos del activo en {city_name}, proporcione una valoración profesional y detallada que refleje las condiciones del mercado inmobiliario colombiano."""

def _generate_customer_support_prompt(data):
    """
    Genera el prompt para un agente de soporte al cliente para inversionistas
    """
    user_type = data.get('user_type', 'investor')
    query_type = data.get('query_type', 'general')
    user_data = data.get('user_data', {})
    context = data.get('context', '')
    
    # ✅ FORMATEAR DATOS REALES DEL USUARIO
    user_summary = _format_user_data_detailed(user_data)
    investment_summary = _format_investment_details(user_data.get('investment_details', []))
    application_summary = _format_application_details(user_data.get('application_details', []))
    
    return f"""Usted es un agente experto de soporte al cliente especializado en servicios de inversión y gestión de fondos. Tiene acceso completo a los datos del usuario en tiempo real.

**Perfil del Usuario:**
*   Tipo de Usuario: {user_type}
*   Consulta Categoría: {query_type}
*   Contexto: {context}

**DATOS REALES DEL USUARIO EN TIEMPO REAL:**
{user_summary}

**INVERSIONES ACTIVAS DEL USUARIO:**
{investment_summary}

**APLICACIONES DEL USUARIO:**
{application_summary}

**Su Respuesta DEBE ser un único objeto JSON con la siguiente estructura:**

```json
{{
  "response": {{
    "message": "Respuesta basada en los datos REALES del usuario: {user_data.get('user_email', 'usuario')}",
    "actionItems": [
      {{
        "type": "data_query",
        "description": "Consulta específica basada en datos reales",
        "model": "FundInvestment",
        "query_params": {{"user_id": {user_data.get('user_id', 'N/A')}}}
      }}
    ],
    "realTimeInsights": [
      {{
        "type": "portfolio_summary",
        "data": "El usuario tiene {user_data.get('total_investments_count', 0)} inversiones activas por un total de ${user_data.get('total_investments', 0):,} COP",
        "recommendation": "Recomendación basada en datos reales"
      }}
    ]
  }},
  "dataQueries": [
    {{
      "query": "FundInvestment.objects.filter(investor_id={user_data.get('user_id', 'N/A')})",
      "purpose": "Obtener inversiones del usuario {user_data.get('user_email', 'N/A')}",
      "results_count": {user_data.get('total_investments_count', 0)}
    }}
  ]
}}
```

**Datos Específicos Disponibles:**
- Usuario: {user_data.get('user_email', 'N/A')} (ID: {user_data.get('user_id', 'N/A')})
- Inversiones Activas: {user_data.get('active_investments_count', 0)}
- Total Invertido: ${user_data.get('total_investments', 0):,} COP
- Última Actividad: {user_data.get('last_activity', 'Sin actividad')}

**Contexto de la Consulta:** {context}

**Objetivo:** Proporcionar respuestas precisas usando los datos REALES del usuario {user_data.get('user_email', 'usuario')}."""

def _format_user_data_detailed(user_data):
    """Formatea datos detallados del usuario con datos reales"""
    if not user_data:
        return "*   No hay datos del usuario disponibles"
    
    formatted = [
        f"*   Usuario: {user_data.get('user_email', 'N/A')} (ID: {user_data.get('user_id', 'N/A')})",
        f"*   Total Invertido: ${user_data.get('total_investments', 0):,} COP",
        f"*   Inversiones Activas: {user_data.get('active_investments_count', 0)} de {user_data.get('total_investments_count', 0)} totales",
        f"*   Órdenes Pendientes: {user_data.get('active_orders', 0)}",
        f"*   Última Actividad: {user_data.get('last_activity', 'Sin actividad')}"
    ]
    
    return '\n'.join(formatted)

def _format_investment_details(investments):
    """Formatea detalles de inversiones"""
    if not investments:
        return "*   No hay inversiones registradas"
    
    formatted = ["**Inversiones Recientes:**"]
    for inv in investments[:3]:
        formatted.append(
            f"*   📊 {inv['fund_name']}: ${inv['invested_amount']:,} COP "
            f"({inv['status']}) - {inv['investment_date']}"
        )
    
    if len(investments) > 3:
        formatted.append(f"*   ... y {len(investments) - 3} inversiones más")
    
    return '\n'.join(formatted)

def _format_application_details(applications):
    """Formatea detalles de aplicaciones"""
    if not applications:
        return "*   No hay aplicaciones registradas"
    
    formatted = ["**Aplicaciones Recientes:**"]
    for app in applications[:3]:
        formatted.append(
            f"*   📝 {app['fund_name']}: ${app['requested_amount']:,} COP "
            f"({app['status']}) - {app['application_date']}"
        )
    
    if len(applications) > 3:
        formatted.append(f"*   ... y {len(applications) - 3} aplicaciones más")
    
    return '\n'.join(formatted)