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
    'financial_institution.FinancialInstitutionViewSet': {
        'list': ('fi', 'list_view_financial_institutions'),
        'retrieve': ('fi', 'view_financial_institutions'),
        'create': ('fi', 'create_financial_institution')
    },
    
    'financial_institution.FinancialInstitutionApplicationViewSet': {
        'list': ('fi', 'list_view_applications'),
        'retrieve': ('fi', 'view_applications')
    },
    
    'financial_institution.MembersFinancialInstitutionViewSet': {
        'list': ('fi', 'list_view_members'),
        'retrieve': ('fi', 'view_members'),
    },
    
    'financial_institution.PendingFinancialInstitutionApplicationViewSet': {
        'list': ('fi', 'list_pending_applications'),
        'retrieve': ('fi', 'pending_applications'),
    },
    
    'financial_institution.FIPermissionViewSet': {
        'list': ('fi', 'list_view_permissions'),
        'retrieve': ('fi', 'view_permissions'),
        'create': ('fi', 'create_permissions'),
        'destroy': ('fi', 'delete_permissions'),
    },
    
    'financial_institution.FICustomGroupViewSet': {
        'list': ('fi', 'list_view_group_permissions'),
        'retrieve': ('fi', 'view_group_permissions'),
        'create': ('fi', 'create_group_permissions'),
        'destroy': ('fi', 'delete_group_permissions'),
    },
    
    'financial_institution.FIUserGroupMembershipViewSet': {
        'list': ('fi', 'list_view_memberships'),
        'retrieve': ('fi', 'view_memberships'),
    },
    
    # Flujo de solicitudes de ingreso a institución financiera
    'financial_institution.FIApplicationActionsViewSet': {
        'create_application': ('fi', 'create_applications'),
        'pre_approve_fi_application': ('fi', 'pre_approve_applications'),
        'send_contract_fi_application': ('fi', 'send_contract_applications'),
        'sign_contract_fi_application': ('fi', 'sign_contract_applications'),
        'approve_application': ('fi', 'approve_applications'),
        'reject_application': ('fi', 'reject_applications'),
    },
    
    # Permisos Tenant específicos
    'financial_institution.FIGroupMembershipActionsViewSet': {
        'assign_user_to_group': ('fi', 'assign_user_to_group'),
        'remove_user_from_group': ('fi', 'remove_user_from_group'),
        'my_fi_permissions': ('fi', 'view_my_permissions'),
    },
    
    # Dashboard stats
    'financial_institution.get_dashboard_stats': {
        'list': ('fi', 'view_dashboard_stats'),
    },
    
    # ============================================
    # FUND (Fondos de Inversión)
    # ============================================
    'fund.FundViewSet': {
        'list': ('fund', 'list_funds'),
        'retrieve': ('fund', 'retrieve_fund'),
        'create': ('fund', 'create_fund'),
        'update': ('fund', 'update_fund'),
        'partial_update': ('fund', 'partial_update_fund'),
        'destroy': ('fund', 'delete_fund'),
    },

    'fund.FundCategoryViewSet': {
        'list': ('fund', 'list_fund_categories'),
        'retrieve': ('fund', 'retrieve_fund_category'),
        'create': ('fund', 'create_fund_category'),
        'update': ('fund', 'update_fund_category'),
        'partial_update': ('fund', 'partial_update_fund_category'),
        'destroy': ('fund', 'delete_fund_category'),
    },

    'fund.FundMembersViewSet': {
        'list': ('fund', 'list_fund_members'),
        'retrieve': ('fund', 'retrieve_fund_member'),
    },

    'fund.FundTypeSemestralDocumentViewSet': {
        'list': ('fund', 'list_fund_type_semestral_documents'),
        'retrieve': ('fund', 'retrieve_fund_type_semestral_document'),
        'create': ('fund', 'create_fund_type_semestral_document'),
        'update': ('fund', 'update_fund_type_semestral_document'),
        'partial_update': ('fund', 'partial_update_fund_type_semestral_document'),
        'destroy': ('fund', 'delete_fund_type_semestral_document'),
    },

    'fund.FundSemestralDocumentViewSet': {
        'list': ('fund', 'list_fund_semestral_documents'),
        'retrieve': ('fund', 'retrieve_fund_semestral_document'),
        'create': ('fund', 'create_fund_semestral_document'),
        'update': ('fund', 'update_fund_semestral_document'),
        'partial_update': ('fund', 'partial_update_fund_semestral_document'),
        'destroy': ('fund', 'delete_fund_semestral_document'),
    },

    'fund.OthersIViewSet': {
        'list': ('fund', 'list_other_income_records'),
        'retrieve': ('fund', 'retrieve_other_income_record'),
        'create': ('fund', 'create_other_income_record'),
        'update': ('fund', 'update_other_income_record'),
        'partial_update': ('fund', 'partial_update_other_income_record'),
        'destroy': ('fund', 'delete_other_income_record'),
    },

    'fund.TrustAgreementViewSet': {
        'list': ('fund', 'list_trust_agreements'),
        'retrieve': ('fund', 'retrieve_trust_agreement'),
        'create': ('fund', 'create_trust_agreement'),
        'update': ('fund', 'update_trust_agreement'),
        'partial_update': ('fund', 'partial_update_trust_agreement'),
        'destroy': ('fund', 'delete_trust_agreement'),
    },

    'fund.FundTokenViewSet': {
        'list': ('fund', 'list_fund_tokens'),
        'retrieve': ('fund', 'retrieve_fund_token'),
    },

    'fund.TokenTransactionViewSet': {
        'list': ('fund', 'list_token_transactions'),
        'retrieve': ('fund', 'retrieve_token_transaction'),
    },

    'fund.TransferReceiptViewSet': {
        'list': ('fund', 'list_transfer_receipts'),
        'retrieve': ('fund', 'retrieve_transfer_receipt'),
    },

    'fund.InvestmentViewSet': {
        'list': ('fund', 'list_investments'),
        'retrieve': ('fund', 'retrieve_investment'),
        'create': ('fund', 'create_investment'),
        'update': ('fund', 'update_investment'),
        'partial_update': ('fund', 'partial_update_investment'),
        'destroy': ('fund', 'delete_investment'),
    },

    'fund.InvestmentApplicationViewSet': {
        'list': ('fund', 'list_investment_applications'),
        'retrieve': ('fund', 'retrieve_investment_application'),
        'create': ('fund', 'create_investment_application'),
        'under_review': ('fund', 'under_review_investment_application'),
        'send_contract': ('fund', 'send_contract_investment_application'),
        'sign_contract': ('fund', 'sign_contract_investment_application'),
    },

    'fund.PendingApplicationViewSet': {
        'list': ('fund', 'list_pending_investment_applications'),
        'retrieve': ('fund', 'retrieve_pending_investment_application'),
    },

    'fund.InvestmentDashboardViewSet': {
        'list': ('fund', 'list_investment_dashboard'),
    },

    'fund.InvestorContractViewSet': {
        'list': ('fund', 'list_investor_contracts'),
        'retrieve': ('fund', 'retrieve_investor_contract'),
        'create': ('fund', 'create_investor_contract'),
        'sign': ('fund', 'sign_investor_contract'),
    },

    'fund.InvestmentDistributionRecordViewSet': {
        'list': ('fund', 'list_investment_distribution_records'),
        'retrieve': ('fund', 'retrieve_investment_distribution_record'),
        'create': ('fund', 'create_investment_distribution_record'),
        'update': ('fund', 'update_investment_distribution_record'),
        'partial_update': ('fund', 'partial_update_investment_distribution_record'),
        'destroy': ('fund', 'delete_investment_distribution_record'),
    },

    'fund.CommissionsViewSet': {
        'list': ('fund', 'list_commissions'),
        'retrieve': ('fund', 'retrieve_commission'),
        'create': ('fund', 'create_commission'),
        'update': ('fund', 'update_commission'),
        'partial_update': ('fund', 'partial_update_commission'),
        'destroy': ('fund', 'delete_commission'),
    },

    'fund.TransfersViewSet': {
        'list': ('fund', 'list_transfers'),
        'retrieve': ('fund', 'retrieve_transfer'),
        'create_transfer': ('fund', 'create_transfer'),
        'fund_transfer_summary': ('fund', 'view_transfer_summary'),
        'delete_transfer': ('fund', 'delete_transfer'),
    },

    'fund.AccountCategoryViewSet': {
        'list': ('fund', 'list_account_categories'),
        'retrieve': ('fund', 'retrieve_account_category'),
        'create': ('fund', 'create_account_category'),
        'update': ('fund', 'update_account_category'),
        'partial_update': ('fund', 'partial_update_account_category'),
        'destroy': ('fund', 'delete_account_category'),
    },

    'fund.AccountingPeriodViewSet': {
        'list': ('fund', 'list_accounting_periods'),
        'retrieve': ('fund', 'retrieve_accounting_period'),
        'create': ('fund', 'create_accounting_period'),
        'update': ('fund', 'update_accounting_period'),
        'partial_update': ('fund', 'partial_update_accounting_period'),
        'destroy': ('fund', 'delete_accounting_period'),
    },

    'fund.AccountingEntryViewSet': {
        'list': ('fund', 'list_accounting_entries'),
        'retrieve': ('fund', 'retrieve_accounting_entry'),
        'create': ('fund', 'create_accounting_entry'),
        'update': ('fund', 'update_accounting_entry'),
        'partial_update': ('fund', 'partial_update_accounting_entry'),
        'destroy': ('fund', 'delete_accounting_entry'),
    },

    'fund.AccountabilityViewSet': {
        'list': ('fund', 'list_accountability_records'),
        'retrieve': ('fund', 'retrieve_accountability_record'),
        'create': ('fund', 'create_accountability_record'),
        'update': ('fund', 'update_accountability_record'),
        'partial_update': ('fund', 'partial_update_accountability_record'),
        'destroy': ('fund', 'delete_accountability_record'),
    },

    'fund.FundOperatingIncomeViewSet': {
        'list': ('fund', 'list_operating_incomes'),
        'retrieve': ('fund', 'retrieve_operating_income'),
        'create': ('fund', 'create_operating_income'),
        'update': ('fund', 'update_operating_income'),
        'partial_update': ('fund', 'partial_update_operating_income'),
        'destroy': ('fund', 'delete_operating_income'),
    },

    'fund.FundOperatingExpenseViewSet': {
        'list': ('fund', 'list_operating_expenses'),
        'retrieve': ('fund', 'retrieve_operating_expense'),
        'create': ('fund', 'create_operating_expense'),
        'update': ('fund', 'update_operating_expense'),
        'partial_update': ('fund', 'partial_update_operating_expense'),
        'destroy': ('fund', 'delete_operating_expense'),
    },
    
    # ============================================
    # TRADING
    # ============================================
    'trading.PurchaseOrderViewSet': {
        'list': ('trading', 'list_view_purchase_orders'),
        'retrieve': ('trading', 'view_purchase_orders'),
        'create': ('trading', 'create_purchase_order'),
        'cancel': ('trading', 'cancel_purchase_order'),
        'destroy': ('trading', 'cancel_purchase_order'),
    },
    
    'trading.SalesOrderViewSet': {
        'list': ('trading', 'list_view_sales_orders'),
        'retrieve': ('trading', 'view_sales_orders'),
        'create': ('trading', 'create_sales_order'),
        'cancel': ('trading', 'cancel_sales_order'),
        'destroy': ('trading', 'cancel_sales_order'),
        'reserved_tokens': ('trading', 'reserve_tokens_sales_order'),
    },

    'trading.TransactionViewSet': {
        'list': ('trading', 'list_view_transactions'),
        'retrieve': ('trading', 'view_transactions'),
    },

    'trading.OrderContractViewSet': {
        'list': ('trading', 'list_view_contracts'),
        'retrieve': ('trading', 'view_contracts'),
        'pending': ('trading', 'list_pending_contracts'),
        'approve': ('trading', 'approve_or_reject_contract'),
    },
    
    'trading.MatchSelectionViewSet': {
        'list': ('trading', 'list_view_match_selections'),
        'retrieve': ('trading', 'view_match_selections'),
        'create_match_selection': ('trading', 'create_match_selection'),
        'validate_selection_capability': ('trading', 'validate_selection_capability'),
        'cancel_selection': ('trading', 'cancel_match_selection'),
        'my_active_selections': ('trading', 'view_active_match_selections'),
        'cleanup_expired': ('trading', 'cleanup_expired_match_selections'),
    },   
    
    'trading.TradingPermissionViewSet': {
        'grant_trading_permission': ('trading', 'grant_trading_permission'),
        'list_user_permissions_trading': ('trading', 'list_user_permissions_trading'),
    },
    
    'trading.NegotiationDashboardViewSet': {
    'orders': ('trading', 'view_negotiation_dashboard'),
    'status_options': ('trading', 'view_negotiation_status_options'),
    },

    # Trading APIViews
    'trading.FindMatchesAPIView': {
        'post': ('trading', 'find_order_matches'),
    },    
    'trading.ActiveOrdersAPIView': {
        'get': ('trading', 'view_active_orders'),
    },
    'trading.CleanupExpiredReservationsAPIView': {
        'post': ('trading', 'cleanup_expired_reservations'),
    },
    'trading.UserSelectionStatsAPIView': {
        'get': ('trading', 'view_selection_stats'),
    },
    'trading.ExecutePaymentAPIView': {
        'post': ('trading', 'execute_payment'),
    },
    'trading.OrdersListAPIView': {
        'get': ('trading', 'list_unified_orders'),
    },
    
    # ============================================
    # USER
    # ============================================
    'user.UserViewSet': {
        'list': ('user', 'list_users'),
        'retrieve': ('user', 'retrieve_user'),
        'create': ('user', 'create_user'),
        'update': ('user', 'update_user'),
        'partial_update': ('user', 'partial_update_user'),
        'destroy': ('user', 'delete_user'),
    },

    'user.VerifyReferredCode': {
        'get': ('user', 'verify_referred_code'),
    },

    'user.UpdateReadUserBasicInfo': {
        'retrieve': ('user', 'retrieve_user_basicdata'),
        'update': ('user', 'update_user_basicdata'),
        'partial_update': ('user', 'partial_update_user_basicdata'),
    },

    'user.AdminUpdateUserBasicInfo': {
        'retrieve': ('user', 'admin_retrieve_user_basicdata'),
        'update': ('user', 'admin_update_user_basicdata'),
        'partial_update': ('user', 'admin_partial_update_user_basicdata'),
    },

    'user.MeApiView': {
        'get': ('user', 'retrieve_me_profile'),
    },

    'user.ActiveEmailView': {
        'get': ('user', 'activate_user_email'),
    },

    'user.UserUpdateApiView': {
        'retrieve': ('user', 'retrieve_user_profile'),
        'update': ('user', 'update_user_profile'),
        'partial_update': ('user', 'partial_update_user_profile'),
    },

    'user.PasswordResetView': {
        'post': ('user', 'request_password_reset'),
    },

    'user.PasswordResetDoneView': {
        'post': ('user', 'confirm_password_reset'),
    },

    'user.CheckSlugView': {
        'get': ('user', 'verify_password_reset_token'),
    },

    'user.IdtypesListView': {
        'list': ('user', 'list_id_types'),
    },

    'user.ImportUsersAPIView': {
        'post': ('user', 'import_users'),
    },

    'user.ListUsersAPIView': {
        'list': ('user', 'list_all_users'),
    },

    'user.GrantAdminPermissionView': {
        'post': ('user', 'grant_admin_permission'),
    },

    'user.ListUserPermissionsView': {
        'get': ('user', 'list_user_permissions'),
    },

    'user.RevokeAdminPermissionView': {
        'post': ('user', 'revoke_admin_permission'),
    },

    'user.RevokeAllPermissionsView': {
        'post': ('user', 'revoke_all_permissions'),
    },    
    
    # ==============================================
    # Audit
    # ==============================================
    'audit.AuditLogViewSet': {
        'list': ('audit', 'list_audit_logs'),
        'retrieve': ('audit', 'view_audit_log'),
    },
    
    'audit.AuditActionViewSet': {
        'list': ('audit', 'list_audit_actions'),
        'retrieve': ('audit', 'view_audit_action'),
    },
    
    'audit.AuditCategoryViewSet': {
        'list': ('audit', 'list_audit_categories'),
        'retrieve': ('audit', 'view_audit_category'),
    },
    
    # ==============================================
    # DRUO
    # ==============================================
    'druo.BanksListView': {
        'list': ('druo', 'view_banks'),
    },
    'druo.AccountTypeListView': {
        'list': ('druo', 'view_account_types'),
    },
    'druo.AccountSubtypeListView': {
        'list': ('druo', 'view_account_subtypes'),
    },
    
    # ==============================================
    # ACADEMY
    # ==============================================
    'academy.CategoryViewSet': {
        'list': ('academy', 'list_categories'),
        'retrieve': ('academy', 'view_category'),
        'create': ('academy', 'create_category'),
        'update': ('academy', 'update_category'),
        'partial_update': ('academy', 'partial_update_category'),
        'destroy': ('academy', 'delete_category'),
    },
    'academy.ArticlesViewSet': {
        'list': ('academy', 'list_articles'),
        'retrieve': ('academy', 'view_article'),
        'create': ('academy', 'create_article'),
        'update': ('academy', 'update_article'),
        'partial_update': ('academy', 'partial_update_article'),
        'destroy': ('academy', 'delete_article'),
    },
    
    # ==============================================
    # CITIES
    # ==============================================
    'cities.CountriesView': {
        'list': ('cities', 'view_countries'),
    },
    'cities.RegionsView': {
        'list': ('cities', 'view_regions'),
    },
    'cities.SubRegionsView': {
        'list': ('cities', 'view_subregions'),
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
        'allow_unauthenticated_clients': True,  # No permitir acceso a clientes no autenticados para acciones de FI
        'client_allowed_actions': ['list_view_financial_institutions', 'view_financial_institutions'],  # Acciones permitidas para clientes
    },
    
    # Reglas para Fund
    'fund': {
        'context_field': 'fund',  # Campo para obtener contexto del fondo
        'staff_groups': ['ADMINISTRADOR', 'STAFF'],
        'client_groups': ['INVERSIONISTA',],
        'allow_unauthenticated_clients': True,  # Permitir acceso a clientes no autenticados para ciertas acciones de fondos
        'client_allowed_actions': [
            'retrieve_fund',
            'list_funds',
        ],
    },
    
    'user': {
        'context_field': 'user',
        'staff_groups': ['ADMINISTRADOR', 'STAFF'],
        'client_groups': ['INVERSIONISTA'],
        'allow_unauthenticated_clients': False,  # Los usuarios deben autenticarse
        'client_allowed_actions': [],
    },    
    
    # Reglas para Trading
    'trading': {
        'context_field': 'fund',  # En trading, el contexto sigue siendo el fondo
        'staff_groups': ['ADMINISTRADOR', 'STAFF'],
        'client_groups': ['INVERSIONISTA'],
        'allow_unauthenticated_clients': False,  # Permitir acceso a clientes no autenticados para ciertas acciones de trading
        'client_allowed_actions': [],
    },
}