from decimal import Decimal
from django.utils import timezone

from apps.financial_institution.service.actions_application_service import FIActionsService
from apps.fund.models.membership import InvestmentApplication
from apps.fund.models.core import Fund

class InvestmentValidator:
    def __init__(self, investment_data):
        self.investment_data = investment_data

    # ========================================================
    # VALIDACIONES SOLICITUD DE INVERSIÓN (submit_investment)
    # ========================================================
    @staticmethod
    def _validate_investor_contract(fund: Fund, user):
        """
        Valida que el usuario tenga un contrato de inversor aprobado para el fondo específico.
        
        Args:
            fund: Instancia del fondo
            user: Instancia del usuario
            
        Raises:
            ValueError: Si no tiene contrato aprobado o está suspendido
        """
        from apps.fund.models.membership import InvestorContract
        
        try:
            # Buscar contrato activo del usuario para este fondo
            investor_contract = InvestorContract.objects.get(
                fund=fund,
                user=user
            )
            
            # Verificar si el contrato no ha expirado (si tiene fecha de expiración)
            if investor_contract.status != InvestorContract.InvestorContractStatus.CONTRACT_SIGNED:
                raise ValueError(f"No puedes crear una inversión sin tener una vinculación activa con el fondo '{fund.name}'. ")
                
        except InvestorContract.DoesNotExist:
            raise ValueError(
                f"Debe ser miembro del fondo '{fund.name}' para poder realizar inversiones. "
                "Por favor, solicite su membresía al fondo antes de continuar."
            ) 
            
    @staticmethod
    def _validate_investment_amount(amount: Decimal, user):
        if amount <= 0:
            raise ValueError("El monto de la inversión debe ser mayor que cero.")
        
        max_amount = FIActionsService.get_approved_amount(user)
        if amount > max_amount:
            raise ValueError(f"El monto de la inversión excede el máximo aprobado de {max_amount}.")
        
    @staticmethod
    def _validate_fund_active(fund: Fund):
        if fund.status != 'active':
            raise ValueError("No puedes solicitar una inverción a un fondo inactivo")
                
    @staticmethod
    def _validate_required_acceptances(
        accepted_terms: bool,
        accepted_risks: bool,
    ):
        required_acceptances = {
            'accepts_terms_and_conditions': accepted_terms,
            'accepts_risk_disclosure': accepted_risks,
        }
        
        missing = [name for name, accepted in required_acceptances.items() if not accepted]
        
        if missing:
            missing_text= ', '.join(missing)
            raise ValueError(f"Faltan las siguientes aceptaciones requeridas: {missing_text}.")    
    
    # ================================================
    # VALIDACIONES FIRMA DE CONTRATO (sign_contract)
    # ================================================
    
    @staticmethod
    def _validate_signature_user(application, user):
        if application.user != user:
            raise ValueError("Solo el usuario propietario de la solicitud puede firmar el contrato.")        

    @staticmethod
    def _validate_application_status(application):
        if application.application_status != InvestmentApplication.ApplicationStatus.CONTRACT_SENT:
            raise ValueError("Solo se puede firmar el contrato en estado: Contrato Enviado")        
    
    @staticmethod
    def _validate_signature_deadline(application):
        if (application.contract_signature_deadline and application.contract_signature_deadline <= timezone.now()):
            raise ValueError(f"El tiempo limite permitido para firmar el contrato ha expirado")
        
    

    
    