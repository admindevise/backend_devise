from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.fund.models.core import Fund
from apps.fund.models.membership import FundInvestment, InvestmentApplication

from apps.fund.services.investment.investment_validator import InvestmentValidator
from apps.fund.services.investment.investment_calculator import InvestmentCalculator
from apps.fund.services.investment.investment_audit_service import InvestmentAuditService
from apps.fund.services.investment.blockchain_transfer_service import BlockchainTransferService

class InvestmentError(Exception):
    """Excepción personalizada para errores del servicio de inversiones"""
    pass


class InvestmentService:
    """
    Servicio para gestionar inversiones en fondos.
    Responsabilidades:
    - Crear y actualizar inversiones.
    - Validar estados y transiciones de inversiones.
    - Notificar a los usuarios sobre cambios en sus inversiones.
    """
    
    # ========================================
    # SOLICITUD ENVIADA
    # ========================================
    @staticmethod
    def submit_investment(
        fund: Fund,
        user,
        requested_amount: Decimal,
        accepts_terms_and_conditions: bool,
        accepts_risk_disclosure: bool,
        request=None
    ) -> InvestmentApplication:
        """
        Crea una nueva inversión en un fondo para un usuario dado.
        
        Args:
            fund (Fund): Instancia del fondo.
            user (User): Instancia del usuario.
            requested_amount (Decimal): Monto de la inversión.
            request (HttpRequest, optional): Objeto de solicitud HTTP para contexto adicional.
            
        Returns:
            FundInvestment: La inversión creada.
            
        Raises:
            ValueError: Si el monto es inválido o si el fondo no está activo.
            InvestmentError: Para otros errores durante la creación.
        """
        audit_log = InvestmentAuditService._create_pending_audit_log_si(user, fund, request)
        
        try:
            # 1. Validar que el usuario sea miembro
            InvestmentValidator._validate_investor_contract(fund, user)
            
            # 2. Validar el monto
            InvestmentValidator._validate_investment_amount(requested_amount, user)
            
            # 3. Calcular monto exacto de tokens
            tokens_calculation = InvestmentCalculator._calculate_and_validate_tokens(
                requested_amount, fund.price_per_unit
            )
            
            # 4. Si no es exacto, generar sugerencias y lanzar error
            if not tokens_calculation['is_exact']:
                suggestion_message = InvestmentCalculator._generate_amount_suggestions(
                    tokens_calculation, fund.price_per_unit
                )
                raise ValueError(suggestion_message)
            
            # 5. Validar que el fondo esté activo
            InvestmentValidator._validate_fund_active(fund)
            
            # 6. Validar aceptaciones requeridas
            InvestmentValidator._validate_required_acceptances(
                accepted_terms=accepts_terms_and_conditions,
                accepted_risks=accepts_risk_disclosure,
            )
            
            # 7. Crear la inversión
            with transaction.atomic():
                investment = InvestmentService._create_fund_investment(fund, user, requested_amount, accepts_terms_and_conditions, accepts_risk_disclosure)
            
            # Actualizar auditoría a éxito
            InvestmentAuditService._update_audit_success(audit_log)
            
            return investment
            
        except Exception as e:
            InvestmentAuditService._update_audit_error(audit_log, e)
            raise InvestmentError(f"Error al crear inversión: {str(e)}")
    
    @staticmethod
    def _create_fund_investment(fund: Fund, user, amount: Decimal, accepts_terms, accepts_risk) -> InvestmentApplication:
        investment = InvestmentApplication.objects.create(
            fund=fund,
            user=user,
            requested_amount=amount,
            accepts_terms_and_conditions=accepts_terms,
            accepts_risk_disclosure=accepts_risk,
            
        )
        return investment
    
    
    # ========================================
    # SOLICITUD EN REVISION
    # ========================================
    @staticmethod
    @transaction.atomic
    def mark_under_review(
        application: InvestmentApplication,
        reviewed_by,
        review_notes: str = "",
        request=None
    ) -> InvestmentApplication:
        """Marca una solicitud de inversion como 'en revision' por parte del admin/staff"""
        
        audit_log = InvestmentAuditService._create_pending_audit_log(application, request, "INVESTMENT_APPLICATION_UNDER_REVIEW")
        
        try:
            if application.application_status != application.ApplicationStatus.PENDING:
                raise ValueError("Solo se puede marcan en revisión solicitudes en estado PENDING")
            
            application.application_status= InvestmentApplication.ApplicationStatus.UNDER_REVIEW
            application.reviewed_by = reviewed_by
            application.reviewed_at = timezone.now()
            application.review_notes = review_notes
            
            application.save(update_fields=['application_status', 'reviewed_at', 'review_notes'])
            
            InvestmentAuditService._update_audit_success(audit_log)
            
            return application
        except Exception as e:
            InvestmentAuditService._update_audit_error(audit_log, e)
            raise InvestmentError(f"Error al marcar en revision la solicitud de inversión: {str(e)}")
    
    # ========================================
    # SOLICITUD CONTRATO ENVIADO
    # ========================================    
    @staticmethod
    @transaction.atomic
    def send_contract(
        application: InvestmentApplication,
        contract_url: str,
        contract_sent_by,
        request=None
        
    ):
        """Esta funcion simula la pre-aprobacion, en lugar de pre-aprobar envia directamente el contrato dando a entender que si se envia el contrato es porque se aprobo"""
        
        audit_log = InvestmentAuditService._create_pending_audit_log(application, request, 'INVESTMENT_APPLICATION_SEND_CONTRACT')
        
        try:
            
            if application.application_status != InvestmentApplication.ApplicationStatus.UNDER_REVIEW:
                raise ValueError("Solo se puede enviar el contrato a solicitudes en revisión.")
            
            InvestmentService._approve_investment_fields(application, contract_url, contract_sent_by)
            
            # Actualizar auditoría a éxito
            InvestmentAuditService._update_audit_success(audit_log)
            
            return application
        except Exception as e:
            InvestmentAuditService._update_audit_error(audit_log, e)
            raise InvestmentError(f"Error al enviar contrato: {str(e)}")
    
    @staticmethod
    def _approve_investment_fields(application, contract_url, contract_sent_by):
        """
        Actualiza la aplicación con los datos de aprobación y envío de contrato.
        """
        # Actualizar estado y datos del contrato
        application.application_status = InvestmentApplication.ApplicationStatus.CONTRACT_SENT
        application.contract_sent_by = contract_sent_by
        application.contract_url = contract_url
        application.contract_sent_at = timezone.now()
        application.contract_signature_deadline = timezone.now() + timezone.timedelta(days=5)
        
        application.save(update_fields=[
            'application_status', 
            'contract_sent_by', 
            'contract_url', 
            'contract_sent_at', 
            'contract_signature_deadline',
        ])
    
    # ========================================
    # SOLICITUD FIRMAR CONTRATO
    # ========================================
    @staticmethod
    def sign_contract(
        application: InvestmentApplication,
        user,
        request=None
    ) -> tuple[InvestmentApplication, FundInvestment]:
        audit_log = InvestmentAuditService._create_pending_audit_log(application, request, 'INVESTMENT_APPLICATION_SIGN_CONTRACT')
        
        try:
            # 1. Validar usuario que firma
            InvestmentValidator._validate_signature_user(application, user)
            
            # 2. Validar estado de solicitud
            InvestmentValidator._validate_application_status(application)
            
            # 3. Validar tiempo limite de firma
            InvestmentValidator._validate_signature_deadline(application)

            with transaction.atomic():
                transfer_result = BlockchainTransferService._transfer_blockchain_tokens(application, request)
                
                # ✅ DEBUGGING: Agregar log para ver qué devuelve
                print(f"🔍 Transfer result: {transfer_result}")
                print(f"🔍 Transfer result type: {type(transfer_result)}")
                
                # ✅ VERIFICAR que no sea None
                if transfer_result is None:
                    raise ValueError("El servicio de transferencia blockchain devolvió None")
                
                # VERIFICAR si fue exitosa
                if not transfer_result.get('success', False):
                    error_details = transfer_result.get('error', 'Error desconocido en transferencia')
                    validation_errors = transfer_result.get('validation_errors', {})
                    
                    # Formatear errores de validación si existen
                    if validation_errors:
                        error_msg = f"Error de validación en transferencia blockchain: {validation_errors}"
                    else:
                        error_msg = f"Error en transferencia blockchain: {error_details}"
                    
                    raise ValueError(error_msg)
                
                application.application_status = InvestmentApplication.ApplicationStatus.APPROVED
                application.contract_signed_at = timezone.now()
                application.save(update_fields=['application_status', 'contract_signed_at'])
                
                fund_investment = FundInvestment.objects.create(
                    application=application,
                    final_invested_amount=application.requested_amount,
                    created_by=user,
                    units_owned=transfer_result.get('tokens_transferred', 0),
                    purchase_price_per_unit=application.fund.price_per_unit,
                )
            
            InvestmentAuditService._update_audit_success(audit_log)
            InvestmentAuditService._create_audit_investment_approved(application, request)
            
            return application, fund_investment
        except Exception as e:
            InvestmentAuditService._update_audit_error(audit_log, e)
            raise InvestmentError(f"Error al firmar contrato: {str(e)}")
        
