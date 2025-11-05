"""
Configuración centralizada de permisos para todos los módulos
Cada módulo define sus propios permisos aquí
"""

# ========================================
# MAPEO DE VIEWSETS A PERMISOS
# ========================================

VIEWSET_PERMISSION_MAP = {
    # ============================================
    # FINANCIAL INSTITUTION
    # ============================================
    'financial_institution.FinancialInstitutionApplicationViewSet': {
        'list': ('fi', 'view_applications'),
        'retrieve': ('fi', 'view_applications'),
        'create': ('fi', 'create_applications'),
    },
    
    'financial_institution.MembersFinancialInstitutionViewSet': {
        'list': ('fi', 'view_members'),
        'retrieve': ('fi', 'view_members'),
    },
    
    'financial_institution.PendingFinancialInstitutionApplicationViewSet': {
        'list': ('fi', 'approve_applications'),
        'retrieve': ('fi', 'approve_applications'),
        'approve': ('fi', 'approve_applications'),
        'reject': ('fi', 'reject_applications'),
    },
    
    # ============================================
    # FUND (Fondos de Inversión)
    # ============================================
    'fund.FundViewSet': {
        'list': ('fund', 'view_funds'),
        'retrieve': ('fund', 'view_funds'),
        'create': ('fund', 'create_funds'),
        'update': ('fund', 'manage_funds'),
        'destroy': ('fund', 'manage_funds'),
    },
    
    'fund.InvestmentApplicationViewSet': {
        'list': ('fund', 'view_investments'),
        'retrieve': ('fund', 'view_investments'),
        'create': ('fund', 'create_investment'),
        'under_review': ('fund', 'approve_investment'),
        'send_contract': ('fund', 'send_investor_contract'),
        'sign_contract': ('fund', 'sign_investor_contract'),
    },
    
    'fund.InvestorContractViewSet': {
        'list': ('fund', 'view_fund_members'),
        'retrieve': ('fund', 'view_fund_members'),
        'create': ('fund', 'send_investor_contract'),
        'sign': ('fund', 'sign_investor_contract'),
    },
    
    # ============================================
    # TRADING
    # ============================================
    'trading.OrderViewSet': {
        'list': ('trading', 'view_orders'),
        'retrieve': ('trading', 'view_orders'),
        'create': ('trading', 'create_order'),
        'cancel': ('trading', 'cancel_order'),
        'execute': ('trading', 'execute_order'),
    },
}

# ========================================
# REGLAS DE PERMISOS POR CONTEXTO
# ========================================

PERMISSION_RULES = {
    # Reglas para Financial Institution
    'fi': {
        'context_field': 'financial_institution',  # Campo para obtener contexto
        'staff_groups': ['ADMINISTRADOR', 'STAFF'],  # Grupos globales con acceso
        'client_groups': ['INVERSIONISTA',],  # Clientes
        'client_allowed_actions': ['create_applications', 'view_applications'],  # Acciones permitidas para clientes
    },
    
    # Reglas para Fund
    'fund': {
        'context_field': 'fund',  # Campo para obtener contexto del fondo
        'staff_groups': ['ADMINISTRADOR', 'STAFF'],
        'client_groups': ['INVERSIONISTA',],
        'client_allowed_actions': [
            'view_funds', 
            'create_investment', 
            'view_investments',
            'sign_investor_contract'
        ],
    },
    
    # Reglas para Trading
    'trading': {
        'context_field': None,  # No requiere contexto específico
        'staff_groups': ['ADMINISTRADOR', 'STAFF'],
        'client_groups': ['INVERSIONISTA'],
        'client_allowed_actions': ['create_order', 'view_orders', 'cancel_order'],
    },
}