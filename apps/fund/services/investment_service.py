from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.utils import timezone

from apps.fund.models.core import Fund
from apps.fund.models.membership import FundInvestment
from apps.audit.audit_service import AuditService
from apps.financial_institution.service.actions_application_service import FIActionsService

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
    
    @staticmethod
    @transaction.atomic
    def create_investment(fund: Fund, user, amount: Decimal, request=None) -> FundInvestment:
        """
        Crea una nueva inversión en un fondo para un usuario dado.
        
        Args:
            fund (Fund): Instancia del fondo.
            user (User): Instancia del usuario.
            amount (Decimal): Monto de la inversión.
            request (HttpRequest, optional): Objeto de solicitud HTTP para contexto adicional.
            
        Returns:
            FundInvestment: La inversión creada.
            
        Raises:
            ValueError: Si el monto es inválido o si el fondo no está activo.
            InvestmentError: Para otros errores durante la creación.
        """
        audit_log = InvestmentService._create_pending_audit_log(user, fund, request)
        
        try:
            # 1. Validar el monto
            InvestmentService._validate_amount(amount)
            
            # 2. Validar que el fondo esté activo
            InvestmentService._validate_fund_active(fund)
            
            # 3. Crear la inversión
            investment = InvestmentService._create_fund_investment(fund, user, amount)
            
            # Actualizar auditoría a éxito
            InvestmentService._update_audit_success(audit_log, investment)
            
            return investment
            
        except Exception as e:
            InvestmentService._update_audit_error(audit_log, e)
            raise InvestmentError(f"Error al crear inversión: {str(e)}")
    
    @staticmethod
    def _validate_amount(amount: Decimal):
        if amount <= 0:
            raise ValueError("El monto de la inversión debe ser mayor que cero.")
        
        max_amount = FIActionsService.get_approved_amount()
    
    @staticmethod
    def _validate_fund_active(fund: Fund):
        if not fund.is_active:
            raise ValueError("No se puede invertir en un fondo inactivo.")
    
    @staticmethod
    def _create_fund_investment(fund: Fund, user, amount: Decimal) -> FundInvestment:
        investment = FundInvestment.objects.create(
            fund=fund,
            user=user,
            amount=amount,
            invested_at=timezone.now()
        )
        return investment
    
    # ============================================
    # METODOS DE AUDITORIA
    # ============================================
    
    @staticmethod
    def _create_pending_audit_log(user, fund, request, action="create_investment"):
        """Crea un log de auditoría inicial con estado pendiente."""
        if not request:
            return None
        return AuditService.create_audit_log(
            request=request,
            action_code=action,
            obj=fund,
            details={
              "user_email": user.email,
              "fund_name": fund.name
            },
            status="PENDING",
        )