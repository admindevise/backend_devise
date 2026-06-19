from django.core.management.base import BaseCommand
from django.db import transaction

from apps.financial_institution.models import FinancialInstitution
from apps.financial_institution.models.permissions import FICustomGroup, FIPermission


DEFAULT_GROUP_PERMISSIONS = {
    "INVERSIONISTA": [
        ("fi", "list_view_financial_institutions"),
        ("fi", "view_financial_institutions"),
        ("fi", "create_applications"),
        ("fi", "view_my_permissions"),
        ("fi", "sign_contract_applications"),
        ("fund", "list_funds"),
        ("fund", "retrieve_fund"),
        ("fund", "list_investments"),
        ("fund", "retrieve_investment"),
        ("fund", "list_investment_applications"),
        ("fund", "retrieve_investment_application"),
        ("fund", "create_investment_application"),
        ("fund", "sign_contract_investment_application"),
        ("fund", "sign_investor_contract"),
        ("trading", "find_order_matches"),
        ("trading", "view_active_orders"),
        ("trading", "view_selection_stats"),
        ("trading", "view_negotiation_dashboard"),
        ("trading", "view_negotiation_status_options"),
        ("trading", "view_match_selections"),
        ("trading", "view_active_match_selections"),
        ("trading", "view_contracts"),
        ("trading", "view_transactions"),
        ("trading", "list_unified_orders"),
        ("trading", "list_user_permissions"),
        ('user', 'retrieve_me_profile'),
        ('user', 'retrieve_user_profile'),
        ('user', 'update_user_profile'),
        ('user', 'partial_update_user_profile'),
        ('user', 'update_user_basicdata'),
        ('user', 'partial_update_user_basicdata'),
        ('user', 'verify_referred_code'),
        ('user', 'request_password_reset'),
        ('user', 'confirm_password_reset'),
        ('user', 'verify_password_reset_token'),
        ('user', 'list_id_types'),     
        ('cities', 'view_subregions'),
        ('cities', 'view_regions'),
        ('cities', 'view_countries'),    
        ('academy', 'list_categories'),
        ('academy', 'view_category'),
        ('academy', 'list_articles'),
        ('academy', 'view_article'),
        ('druo', 'view_banks'),
        ('druo', 'view_account_types'),
               
    ],
    "STAFF": [
        ("fi", "list_view_financial_institutions"),
        ("fi", "view_financial_institutions"),
        ("fi", "list_view_applications"),
        ("fi", "view_applications"),
        ("fi", "pre_approve_applications"),
        ("fi", "approve_applications"),
        ("fi", "send_contract_applications"),
        ("fi", "sign_contract_applications"),
        ("fi", "list_view_members"),
        ("fi", "view_members"),
        ("fi", "list_view_memberships"),
        ("fi", "view_memberships"),
        ("fi", "assign_user_to_group"),
        ("fi", "remove_user_from_group"),
        ("fi", "list_view_permissions"),
        ("fi", "view_permissions"),
        ("fi", "view_my_permissions"),
        ("fi", "view_dashboard_stats"),
        ("fi", "pending_applications"),
        ("fi", "list_pending_applications"),
        ("fi", "reject_applications"),
        ("fund", "list_funds"),
        ("fund", "retrieve_fund"),
        ("fund", "create_fund"),
        ("fund", "update_fund"),
        ("fund", "partial_update_fund"),
        ("fund", "list_fund_members"),
        ("fund", "retrieve_fund_member"),
        ("fund", "list_fund_tokens"),
        ("fund", "retrieve_fund_token"),
        ("fund", "list_token_transactions"),
        ("fund", "retrieve_token_transaction"),
        ("fund", "list_investments"),
        ("fund", "retrieve_investment"),
        ("fund", "create_investment"),
        ("fund", "update_investment"),
        ("fund", "partial_update_investment"),
        ("fund", "list_investment_applications"),
        ("fund", "retrieve_investment_application"),
        ("fund", "create_investment_application"),
        ("fund", "under_review_investment_application"),
        ("fund", "send_contract_investment_application"),
        ("fund", "sign_contract_investment_application"),
        ("fund", "list_pending_investment_applications"),
        ("fund", "retrieve_pending_investment_application"),
        ("fund", "list_investment_dashboard"),
        ("fund", "list_investor_contracts"),
        ("fund", "retrieve_investor_contract"),
        ("fund", "create_investor_contract"),
        ("fund", "sign_investor_contract"),
        ("fund", "list_transfers"),
        ("fund", "retrieve_transfer"),
        ("fund", "create_transfer"),
        ("fund", "view_transfer_summary"),
        ("trading", "find_order_matches"),
        ("trading", "execute_payment"),
        ("trading", "view_active_orders"),
        ("trading", "view_selection_stats"),
        ("trading", "view_negotiation_dashboard"),
        ("trading", "view_negotiation_status_options"),
        ("trading", "list_view_transactions"),
        ("trading", "view_transactions"),
        ("trading", "list_view_contracts"),
        ("trading", "view_contracts"),
        ("trading", "list_pending_contracts"),
        ("trading", "approve_or_reject_contract"),
        ("trading", "list_view_match_selections"),
        ("trading", "view_match_selections"),
        ("trading", "view_active_match_selections"),
        ("trading", "create_match_selection"),
        ("trading", "validate_selection_capability"),
        ("trading", "cancel_match_selection"),
        ("trading", "list_unified_orders"),
        ("trading", "list_user_permissions"),
        ('user', 'list_users'),
        ('user', 'retrieve_user'),
        ('user', 'create_user'),
        ('user', 'update_user'),
        ('user', 'partial_update_user'),
        ('user', 'retrieve_user_basicdata'),
        ('user', 'update_user_basicdata'),
        ('user', 'partial_update_user_basicdata'),
        ('user', 'retrieve_user_profile'),
        ('user', 'update_user_profile'),
        ('user', 'partial_update_user_profile'),
        ('user', 'activate_user_email'),
        ('user', 'request_password_reset'),
        ('user', 'confirm_password_reset'),
        ('user', 'verify_password_reset_token'),
        ('user', 'list_id_types'),
        ('user', 'list_user_permissions'),
        ('user', 'verify_referred_code'),       
        ('cities', 'view_subregions'),
        ('cities', 'view_regions'),
        ('cities', 'view_countries'),   
        ('academy', 'list_categories'),
        ('academy', 'create_category'),
        ('academy', 'view_category'),
        ('academy', 'update_category'),
        ('academy', 'partial_update_category'),
        ('academy', 'delete_category'),
        ('academy', 'list_articles'),
        ('academy', 'create_article'),
        ('academy', 'view_article'),
        ('academy', 'update_article'),
        ('academy', 'partial_update_article'),
        ('academy', 'delete_article'),          
        ('druo', 'view_banks'),
        ('druo', 'view_account_types'),
        ('druo', 'view_account_subtypes'),
        ('audit', 'list_audit_logs'),
        ('audit', 'view_audit_log'),
        ('audit', 'list_audit_actions'),
        ('audit', 'view_audit_action'),
        ('audit', 'list_audit_categories'),
        ('audit', 'view_audit_category'),    
    ],
    "ADMINISTRADOR": [
        ("fi", "list_view_financial_institutions"),
        ("fi", "view_financial_institutions"),
        ("fi", "create_financial_institution"),
        ("fi", "list_view_applications"),
        ("fi", "view_applications"),
        ("fi", "create_applications"),
        ("fi", "pre_approve_applications"),
        ("fi", "approve_applications"),
        ("fi", "send_contract_applications"),
        ("fi", "sign_contract_applications"),
        ("fi", "pending_applications"),
        ("fi", "reject_applications"),
        ("fi", "list_pending_applications"),
        ("fi", "list_view_members"),
        ("fi", "view_members"),
        ("fi", "list_view_memberships"),
        ("fi", "view_memberships"),
        ("fi", "assign_user_to_group"),
        ("fi", "remove_user_from_group"),
        ("fi", "list_view_permissions"),
        ("fi", "view_permissions"),
        ("fi", "create_permissions"),
        ("fi", "delete_permissions"),
        ("fi", "list_view_group_permissions"),
        ("fi", "view_group_permissions"),
        ("fi", "create_group_permissions"),
        ("fi", "delete_group_permissions"),
        ("fi", "view_my_permissions"),
        ("fi", "view_dashboard_stats"),
        ("fund", "list_funds"),
        ("fund", "retrieve_fund"),
        ("fund", "create_fund"),
        ("fund", "update_fund"),
        ("fund", "partial_update_fund"),
        ("fund", "delete_fund"),
        ("fund", "list_fund_categories"),
        ("fund", "retrieve_fund_category"),
        ("fund", "create_fund_category"),
        ("fund", "update_fund_category"),
        ("fund", "partial_update_fund_category"),
        ("fund", "delete_fund_category"),
        ("fund", "list_fund_members"),
        ("fund", "retrieve_fund_member"),
        ("fund", "list_fund_type_semestral_documents"),
        ("fund", "retrieve_fund_type_semestral_document"),
        ("fund", "create_fund_type_semestral_document"),
        ("fund", "update_fund_type_semestral_document"),
        ("fund", "partial_update_fund_type_semestral_document"),
        ("fund", "delete_fund_type_semestral_document"),
        ("fund", "list_fund_semestral_documents"),
        ("fund", "retrieve_fund_semestral_document"),
        ("fund", "create_fund_semestral_document"),
        ("fund", "update_fund_semestral_document"),
        ("fund", "partial_update_fund_semestral_document"),
        ("fund", "delete_fund_semestral_document"),
        ("fund", "list_other_income_records"),
        ("fund", "retrieve_other_income_record"),
        ("fund", "create_other_income_record"),
        ("fund", "update_other_income_record"),
        ("fund", "partial_update_other_income_record"),
        ("fund", "delete_other_income_record"),
        ("fund", "list_trust_agreements"),
        ("fund", "retrieve_trust_agreement"),
        ("fund", "create_trust_agreement"),
        ("fund", "update_trust_agreement"),
        ("fund", "partial_update_trust_agreement"),
        ("fund", "delete_trust_agreement"),
        ("fund", "list_fund_tokens"),
        ("fund", "retrieve_fund_token"),
        ("fund", "list_token_transactions"),
        ("fund", "retrieve_token_transaction"),
        ("fund", "list_transfer_receipts"),
        ("fund", "retrieve_transfer_receipt"),
        ("fund", "list_investments"),
        ("fund", "retrieve_investment"),
        ("fund", "create_investment"),
        ("fund", "update_investment"),
        ("fund", "partial_update_investment"),
        ("fund", "delete_investment"),
        ("fund", "list_investment_applications"),
        ("fund", "retrieve_investment_application"),
        ("fund", "create_investment_application"),
        ("fund", "under_review_investment_application"),
        ("fund", "send_contract_investment_application"),
        ("fund", "sign_contract_investment_application"),
        ("fund", "list_pending_investment_applications"),
        ("fund", "retrieve_pending_investment_application"),
        ("fund", "list_investment_dashboard"),
        ("fund", "list_investor_contracts"),
        ("fund", "retrieve_investor_contract"),
        ("fund", "create_investor_contract"),
        ("fund", "sign_investor_contract"),
        ("fund", "list_investment_distribution_records"),
        ("fund", "retrieve_investment_distribution_record"),
        ("fund", "create_investment_distribution_record"),
        ("fund", "update_investment_distribution_record"),
        ("fund", "partial_update_investment_distribution_record"),
        ("fund", "delete_investment_distribution_record"),
        ("fund", "list_commissions"),
        ("fund", "retrieve_commission"),
        ("fund", "create_commission"),
        ("fund", "update_commission"),
        ("fund", "partial_update_commission"),
        ("fund", "delete_commission"),
        ("fund", "list_transfers"),
        ("fund", "retrieve_transfer"),
        ("fund", "create_transfer"),
        ("fund", "view_transfer_summary"),
        ("fund", "delete_transfer"),
        ("fund", "list_account_categories"),
        ("fund", "retrieve_account_category"),
        ("fund", "create_account_category"),
        ("fund", "update_account_category"),
        ("fund", "partial_update_account_category"),
        ("fund", "delete_account_category"),
        ("fund", "list_accounting_periods"),
        ("fund", "retrieve_accounting_period"),
        ("fund", "create_accounting_period"),
        ("fund", "update_accounting_period"),
        ("fund", "partial_update_accounting_period"),
        ("fund", "delete_accounting_period"),
        ("fund", "list_accounting_entries"),
        ("fund", "retrieve_accounting_entry"),
        ("fund", "create_accounting_entry"),
        ("fund", "update_accounting_entry"),
        ("fund", "partial_update_accounting_entry"),
        ("fund", "delete_accounting_entry"),
        ("fund", "list_accountability_records"),
        ("fund", "retrieve_accountability_record"),
        ("fund", "create_accountability_record"),
        ("fund", "update_accountability_record"),
        ("fund", "partial_update_accountability_record"),
        ("fund", "delete_accountability_record"),
        ("fund", "list_operating_incomes"),
        ("fund", "retrieve_operating_income"),
        ("fund", "create_operating_income"),
        ("fund", "update_operating_income"),
        ("fund", "partial_update_operating_income"),
        ("fund", "delete_operating_income"),
        ("fund", "list_operating_expenses"),
        ("fund", "retrieve_operating_expense"),
        ("fund", "create_operating_expense"),
        ("fund", "update_operating_expense"),
        ("fund", "partial_update_operating_expense"),
        ("fund", "delete_operating_expense"),
        ("trading", "find_order_matches"),
        ("trading", "execute_payment"),
        ("trading", "view_active_orders"),
        ("trading", "cleanup_expired_reservations"),
        ("trading", "view_selection_stats"),
        ("trading", "view_negotiation_dashboard"),
        ("trading", "view_negotiation_status_options"),
        ("trading", "list_view_transactions"),
        ("trading", "view_transactions"),
        ("trading", "list_view_contracts"),
        ("trading", "view_contracts"),
        ("trading", "list_pending_contracts"),
        ("trading", "approve_or_reject_contract"),
        ("trading", "list_view_match_selections"),
        ("trading", "view_match_selections"),
        ("trading", "view_active_match_selections"),
        ("trading", "cleanup_expired_match_selections"),
        ("trading", "create_match_selection"),
        ("trading", "validate_selection_capability"),
        ("trading", "cancel_match_selection"),
        ("trading", "grant_trading_permission"),
        ("trading", "list_unified_orders"),
        ("trading", "list_user_permissions"),
        ("audit", "view_audit_log"),
        ("audit", "view_audit_action"),
        ("audit", "view_audit_category"),
        ("audit", "list_audit_logs"),
        ("audit", "list_audit_actions"),
        ("audit", "list_audit_categories"),
        ("druo", "view_banks"),
        ("druo", "view_account_types"),
        ("druo", "view_account_subtypes"),
        ('user', 'list_users'),
        ('user', 'retrieve_user'),
        ('user', 'create_user'),
        ('user', 'update_user'),
        ('user', 'partial_update_user'),
        ('user', 'delete_user'),
        ('user', 'retrieve_user_basicdata'),
        ('user', 'update_user_basicdata'),
        ('user', 'partial_update_user_basicdata'),
        ('user', 'admin_retrieve_user_basicdata'),
        ('user', 'admin_update_user_basicdata'),
        ('user', 'admin_partial_update_user_basicdata'),
        ('user', 'retrieve_user_profile'),
        ('user', 'update_user_profile'),
        ('user', 'partial_update_user_profile'),
        ('user', 'activate_user_email'),
        ('user', 'request_password_reset'),
        ('user', 'confirm_password_reset'),
        ('user', 'verify_password_reset_token'),
        ('user', 'list_id_types'),
        ('user', 'import_users'),
        ('user', 'list_all_users'),
        ('user', 'grant_admin_permission'),
        ('user', 'list_user_permissions'),
        ('user', 'revoke_admin_permission'),
        ('user', 'revoke_all_permissions'),
        ('user', 'verify_referred_code'),
        ('cities', 'view_subregions'),
        ('cities', 'view_regions'),
        ('cities', 'view_countries'),
        ('academy', 'list_categories'),
        ('academy', 'create_category'),
        ('academy', 'view_category'),
        ('academy', 'update_category'),
        ('academy', 'partial_update_category'),
        ('academy', 'delete_category'),
        ('academy', 'list_articles'),
        ('academy', 'create_article'),
        ('academy', 'view_article'),
        ('academy', 'update_article'),
        ('academy', 'partial_update_article'),
        ('academy', 'delete_article'),
        ('druo', 'view_banks'),
        ('druo', 'view_account_types'),
        ('druo', 'view_account_subtypes'),
        ('audit', 'list_audit_logs'),
        ('audit', 'view_audit_log'),
        ('audit', 'list_audit_actions'),
        ('audit', 'view_audit_action'),
        ('audit', 'list_audit_categories'),
        ('audit', 'view_audit_category'),
    ],
}


class Command(BaseCommand):
    help = "Asigna permisos base a grupos FI: INVERSIONISTA, STAFF y ADMINISTRADOR"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fi-id",
            type=int,
            default=None,
            help="ID de FinancialInstitution. Si no se envía, procesa todas.",
        )
        parser.add_argument(
            "--only-group",
            type=str,
            default=None,
            choices=list(DEFAULT_GROUP_PERMISSIONS.keys()),
            help="Asignar permisos solo a un grupo específico.",
        )
        parser.add_argument(
            "--append",
            action="store_true",
            help="Agrega permisos sin reemplazar los existentes.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la operación sin guardar cambios.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        fi_id = options["fi_id"]
        only_group = options["only_group"]
        append = options["append"]
        dry_run = options["dry_run"]

        fis = FinancialInstitution.objects.all()
        if fi_id:
            fis = fis.filter(id=fi_id)

        if not fis.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No se encontraron instituciones financieras. Se omite la asignación de permisos por defecto."
                )
            )
            return

        group_names = [only_group] if only_group else list(DEFAULT_GROUP_PERMISSIONS.keys())

        for fi in fis:
            self.stdout.write(self.style.NOTICE(f"\nFI [{fi.id}] {fi}"))

            for group_name in group_names:
                group = FICustomGroup.objects.filter(
                    financial_institution=fi,
                    name=group_name,
                    is_active=True
                ).first()

                if not group:
                    self.stdout.write(
                        self.style.WARNING(f"  - Grupo {group_name} no existe o está inactivo")
                    )
                    continue

                perms_needed = DEFAULT_GROUP_PERMISSIONS[group_name]
                perms = FIPermission.objects.filter(
                    is_active=True,
                    module__in=[module for module, _ in perms_needed],
                    codename__in=[codename for _, codename in perms_needed],
                )

                found_map = {(perm.module, perm.codename): perm for perm in perms}
                missing = [item for item in perms_needed if item not in found_map]

                if missing:
                    self.stdout.write(
                        self.style.WARNING(f"  - Permisos faltantes para {group_name}: {missing}")
                    )

                perm_ids = [perm.id for perm in found_map.values()]

                if dry_run:
                    action = "append" if append else "replace"
                    self.stdout.write(
                        self.style.NOTICE(
                            f"  - [DRY RUN] {group_name}: {action} {len(perm_ids)} permisos"
                        )
                    )
                    continue

                if append:
                    group.permissions.add(*perm_ids)
                else:
                    group.permissions.set(perm_ids)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  - {group_name}: {len(perm_ids)} permisos asignados"
                    )
                )

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("\nDry run completado. No se guardaron cambios."))
        else:
            self.stdout.write(self.style.SUCCESS("\nAsignación completada."))