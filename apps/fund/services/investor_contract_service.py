from django.utils import timezone
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from apps.fund.models.membership import InvestorContract
from apps.fund.models.core import Fund
from apps.audit.audit_service import AuditService


class InvestorContractError(Exception):
    """Excepción personalizada para errores relacionados con contratos de inversores."""
    pass


class InvestorContractService:
    """
    Servicio para gestionar contratos de inversores en fondos.
    Responsabilidades:
    - Crear y actualizar contratos de inversores.
    - Validar estados y transiciones de contratos.
    - Notificar a los usuarios sobre cambios en sus contratos.
    """
    
    @staticmethod
    @transaction.atomic
    def create_contract(fund, user, contract_url, request=None):
        """
        Crea un nuevo contrato de inversor para un fondo y usuario dados.
        
        Args:
            fund (Fund): Instancia del fondo.
            user (User): Instancia del usuario.
            request (HttpRequest, optional): Objeto de solicitud HTTP para contexto adicional.
            **kwargs: Argumentos adicionales para el contrato.
            
        Returns:
            InvestorContract: El contrato creado.
            
        Raises:
            ValueError: Si ya existe un contrato para el usuario y fondo.
            InvestorContractError: Para otros errores durante la creación.
        """
        audit_log = InvestorContractService._create_pending_audit_log(user, fund, request)
        
        try:
            # 1. Validar que el usuario este asociado a la institucion Financiera
            InvestorContractService._validate_member_fi(fund, user)
            
            # 1. Validar que no exista un contrato previo
            InvestorContractService._validate_no_existing_contract(fund, user)
            
            # 3. Crear el contrato
            contract = InvestorContractService._create_investor_contract(fund, user, contract_url)
            
            # Actualizar auditoría a éxito
            InvestorContractService._update_audit_success(audit_log, contract)
            
            return contract
            
        except Exception as e:
            InvestorContractService._update_audit_error(audit_log, e)
            raise InvestorContractError(f"Error al solicitar contrato: {str(e)}")

    @staticmethod
    def _validate_member_fi(fund, user):
        from apps.financial_institution.models import FinancialInstitutionApplication
        try:
            member = FinancialInstitutionApplication.objects.get(
                user = user,
                status = FinancialInstitutionApplication.ApplicationStatus.APPROVED,
                financial_institution = fund.financial_institution
            )
        except FinancialInstitutionApplication.DoesNotExist:
            raise ValueError(f"No existe una viculación a la institución financiera ({fund.financial_institution.name}).")
        return member

    @staticmethod
    def _validate_no_existing_contract(fund, user):
        """Valida que no exista un contrato previo para el usuario y fondo."""
        existing_contract = InvestorContract.objects.select_for_update().filter(
            fund=fund,
            user=user
        ).first()
        
        if existing_contract:
            raise ValueError("Ya tienes un contrato de vinculación con este vehiculo de inversión.")

    @staticmethod
    def _create_investor_contract(fund, user, contract_url):
        """Crea la instancia del contrato de inversor."""
        return InvestorContract.objects.create(
            fund=fund,
            user=user,
            contract_url=contract_url,
            expired_at=timezone.now() + timezone.timedelta(days=5), # Ejemplo: expira en 5 días
            status=InvestorContract.InvestorContractStatus.PENDING_SIGNATURE
        )

    @staticmethod
    def _create_pending_audit_log(user, fund, request):
        """Crea un log de auditoría inicial con estado pendiente."""
        if not request:
            return None
            
        return AuditService.log_action(
            request=request,
            action_code="FUND_MEMBERSHIP_SEND_CONTRACT",
            obj=user,
            details={
                "fund_id": fund.id,
                "user_id": user.id,
            },
            status="PENDING"
        )


    @staticmethod
    @transaction.atomic
    def sign_contract(contract, request=None):
        """
        Marca un contrato de inversor como firmado.
        
        Args:
            contract (InvestorContract): Instancia del contrato a firmar.
            request (HttpRequest, optional): Objeto de solicitud HTTP para contexto adicional.
            
        Returns:
            InvestorContract: El contrato actualizado.
        Raises:
            InvestorContractError: Si el contrato no está en estado válido para firmar.
        """
        try:
            contract = InvestorContract.objects.select_related('fund').get(id=contract)
        except InvestorContract.DoesNotExist:
            raise InvestorContractError(f"El contrato con ID {contract} no existe.")
        
        audit_log = InvestorContractService._create_pending_audit_log_sign(contract, request)
        
        try:
            if contract.user != request.user:
                raise ValueError("No tienes permiso para firmar este contrato.")
            
            # 1. Validar estado actual del contrato
            if contract.status != InvestorContract.InvestorContractStatus.PENDING_SIGNATURE:
                raise ValueError("El contrato no está en un estado válido para ser firmado.")
            
            # 2. Verificar si el contrato ha expirado
            InvestorContractService._check_contract_expiry(contract)
            
            contract.status = InvestorContract.InvestorContractStatus.CONTRACT_SIGNED
            contract.contract_signed_at = timezone.now()
            contract.save(update_fields=['status', 'contract_signed_at'])
            
            # Actualizar auditoría a éxito
            InvestorContractService._update_audit_success(audit_log, contract)
            
            return contract
        
        except Exception as e:
            InvestorContractService._update_audit_error(audit_log, e)
            raise InvestorContractError(f"Error al firmar el contrato: {str(e)}")
        

    @staticmethod
    def _create_pending_audit_log_sign(contract, request):
        """Crea un log de auditoría inicial con estado pendiente para la firma."""
        if not request:
            return None
            
        return AuditService.log_action(
            request=request,
            action_code="FUND_MEMBERSHIP_SIGN_CONTRACT",
            obj=contract,
            details={
                "contract_id": contract.id,
                "fund_id": contract.fund.id,
            },
            status="PENDING"
        )

    @staticmethod
    def _check_contract_expiry(contract):
        """Verifica si el contrato ha expirado."""
        if contract.expired_at and timezone.now() > contract.expired_at:
            raise ValueError("El contrato ha expirado, no se puede firmar. Por favor, solicite un nuevo contrato.")

    # ===================================
    # MANEJO DE AUDITORÍA
    # ===================================
    
    @staticmethod
    def _update_audit_success(audit_log, object_audit):
        """Actualiza el log de auditoría con información de éxito."""
        if not audit_log:
            return
            
        investor_contract_type = ContentType.objects.get_for_model(InvestorContract)
        
        audit_log.content_type = investor_contract_type
        audit_log.object_id = object_audit.id
        audit_log.status = 'SUCCESS'
        
        audit_log.save(update_fields=['content_type', 'object_id', 'status'])
    
    @staticmethod
    def _update_audit_error(audit_log, error):
        """Actualiza el log de auditoría con información del error."""
        if not audit_log:
            return
            
        audit_log.status = 'ERROR'
        audit_log.details.update({
            'error': str(error),
            'error_type': type(error).__name__,
        })
        
        audit_log.save(update_fields=['status', 'details'])

    # ===================================================
    # MÉTODOS ADICIONALES PARA FUTURAS FUNCIONALIDADES
    # ===================================================
    
    @staticmethod
    def get_contract(fund, user):
        """Obtiene el contrato de un usuario para un fondo específico."""
        return InvestorContract.objects.filter(fund=fund, user=user).first()
    
    @staticmethod
    def contract_exists(fund, user):
        """Verifica si existe un contrato para el usuario y fondo."""
        return InvestorContract.objects.filter(fund=fund, user=user).exists()