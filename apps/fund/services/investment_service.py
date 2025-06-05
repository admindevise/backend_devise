from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from apps.fund.models import Fund, FundApplication, FundInvestment
from apps.audit.audit_service import AuditService
#from apps.fund.utils import calculate_tokens_for_amount  # Asumiendo que existe en utils


class FundInvestmentError(Exception):
    """Excepción personalizada para errores del servicio de inversiones"""
    pass


class FundInvestmentService:
    """
    💰 Servicio de Inversiones en Fondos - Maneja el ciclo de vida completo de inversiones
    
    Responsabilidades:
    - Procesar compras de tokens
    - Manejar pagos y confirmaciones
    - Actualizar estados de inversión
    - Calcular distribuciones y rendimientos
    - Integración con auditoría
    """
    
    #+ ========================================
    #+ Funciones auxiliares de auditoría
    #+ ========================================
    
    @staticmethod
    def _audit_simple_success(user, action_code: str, obj, details: dict):
        """🟡 Auditoría simple: Solo registra SUCCESS directamente"""
        AuditService.log_action(
            user=user,
            action_code=action_code,
            obj=obj,
            details=details
        )
    
    @staticmethod
    def _audit_critical_start(user, action_code: str, obj, details: dict) -> str:
        """🔴 Auditoría crítica: Inicia con PENDING"""
        audit_log = AuditService.log_action(
            user=user,
            action_code=action_code,
            obj=obj,
            details={**details, 'status': 'PENDING'},
            status='PENDING'
        )
        return audit_log.id if hasattr(audit_log, 'id') else str(audit_log)
    
    @staticmethod
    def _audit_critical_success(audit_id: str, user, additional_details: dict = None):
        """🔴 Auditoría crítica: Marca como SUCCESS"""
        details = additional_details or {}
        details['status'] = 'SUCCESS'
        
        try:
            AuditService.update_action_status(
                audit_id=audit_id,
                status='SUCCESS',
                details=details
            )
        except Exception:
            AuditService.log_action(
                user=user,
                action_code="OPERATION_SUCCESS",
                details={**details, 'original_audit_id': audit_id}
            )
    
    @staticmethod
    def _audit_critical_error(audit_id: str, user, error: Exception, additional_details: dict = None):
        """🔴 Auditoría crítica: Marca como ERROR"""
        details = additional_details or {}
        details.update({
            'status': 'ERROR',
            'error_type': type(error).__name__,
            'error_message': str(error),
            'operation_failed': True
        })
        
        try:
            AuditService.update_action_status(
                audit_id=audit_id,
                status='ERROR',
                details=details
            )
        except Exception:
            AuditService.log_action(
                user=user,
                action_code="OPERATION_ERROR",
                details={**details, 'original_audit_id': audit_id}
            )
    
    #+ ========================================
    #+ Métodos públicos del servicio
    #+ ========================================
    
    @staticmethod
    def create_for_approved_application(application: FundApplication, request=None) -> FundInvestment:
        """
        🎯 Crear inversión cuando se aprueba una aplicación
        
        Args:
            application: Aplicación aprobada
            
        Returns:
            FundInvestment: Nueva inversión creada
        """
        with transaction.atomic():
            # Validar que la aplicación esté aprobada
            if application.status != FundApplication.ApplicationStatus.APPROVED:
                raise ValidationError("Application must be approved to create investment")
            
            # Verificar que no exista ya una inversión
            if hasattr(application, 'investment'):
                raise ValidationError("Investment already exists for this application")
            
            investment = FundInvestment.objects.create(
                application=application,
                fund=application.fund,
                investor=application.applicant,
                status=FundInvestment.InvestmentStatus.PENDING_TOKENS,
                # invested_amount se establecerá cuando complete la inversión
            )
            
            if request:
                AuditService.log_action(
                    user=request.user,
                    action_code="INVESTMENT_CREATE",
                    obj=investment,
                    details={
                        'application_id': application.id,
                        'fund_id': investment.fund.id,
                        'investor_id': investment.investor.id,
                        'status': investment.status
                    }
                )
            
            return investment
    
    """ @staticmethod
    def process_token_purchase(investment_id: int, user, payment_amount: Decimal, payment_method: str = "bank_transfer") -> FundInvestment:

        audit_id = None
        try:
            with transaction.atomic():
                # 1. Obtener y validar inversión
                investment = FundInvestment.objects.select_for_update().get(id=investment_id)
                FundInvestmentService._validate_can_purchase_tokens(investment, user, payment_amount)
                
                # 2. Calcular tokens a asignar
                tokens_to_allocate = FundInvestmentService._calculate_tokens_for_payment(
                    investment.fund, payment_amount
                )
                
                # 3. Auditar inicio de operación crítica
                audit_id = FundInvestmentService._audit_critical_start(
                    user=user,
                    action_code="FUND_INVESTMENT_TOKEN_PURCHASE",
                    obj=investment,
                    details={
                        'investment_id': investment.id,
                        'fund_id': investment.fund.id,
                        'payment_amount': str(payment_amount),
                        'payment_method': payment_method,
                        'tokens_to_allocate': str(tokens_to_allocate),
                        'operation': 'process_token_purchase'
                    }
                )
                
                # 4. Actualizar inversión
                old_status = investment.status
                investment.invested_amount = payment_amount
                investment.tokens_allocated = tokens_to_allocate
                investment.status = FundInvestment.InvestmentStatus.ACTIVE
                investment.investment_date = timezone.now()
                if hasattr(investment, 'payment_method'):
                    investment.payment_method = payment_method
                investment.save()
                
                # 5. Actualizar estadísticas del fondo (si aplica)
                FundInvestmentService._update_fund_statistics(investment.fund, payment_amount, tokens_to_allocate)
                
                # 6. Marcar operación como exitosa
                FundInvestmentService._audit_critical_success(
                    audit_id=audit_id,
                    user=user,
                    additional_details={
                        'old_status': old_status,
                        'new_status': investment.status,
                        'final_tokens': str(investment.tokens_allocated),
                        'final_amount': str(investment.invested_amount),
                        'operation_completed': True
                    }
                )
                
                return investment
            
        except Exception as e:
            if audit_id:
                FundInvestmentService._audit_critical_error(
                    audit_id=audit_id,
                    user=user,
                    error=e,
                    additional_details={
                        'investment_id': investment_id,
                        'payment_amount': str(payment_amount),
                        'operation': 'process_token_purchase'
                    }
                )
            raise FundInvestmentError(f"Error al procesar compra de tokens: {str(e)}")
     """
    
    @staticmethod
    def cancel_investment(investment_id: int, user, cancellation_reason: str) -> FundInvestment:
        """
        🚫 Cancelar una inversión
        
        Args:
            investment_id: ID de la inversión a cancelar
            user: Usuario que cancela (debe ser el inversor o staff)
            cancellation_reason: Razón de la cancelación
            
        Returns:
            FundInvestment: Inversión cancelada
        """
        audit_id = None
        try:
            with transaction.atomic():
                # 1. Obtener y validar inversión
                investment = FundInvestment.objects.select_for_update().get(id=investment_id)
                FundInvestmentService._validate_can_cancel(investment, user)
                
                # 2. Auditar inicio de operación crítica
                audit_id = FundInvestmentService._audit_critical_start(
                    user=user,
                    action_code="FUND_INVESTMENT_CANCEL",
                    obj=investment,
                    details={
                        'investment_id': investment.id,
                        'fund_id': investment.fund.id,
                        'cancellation_reason': cancellation_reason,
                        'operation': 'cancel_investment'
                    }
                )
                
                # 3. Actualizar inversión
                old_status = investment.status
                investment.status = FundInvestment.InvestmentStatus.CANCELLED
                if hasattr(investment, 'cancellation_reason'):
                    investment.cancellation_reason = cancellation_reason
                if hasattr(investment, 'cancelled_at'):
                    investment.cancelled_at = timezone.now()
                if hasattr(investment, 'cancelled_by'):
                    investment.cancelled_by = user
                investment.save()
                
                # 4. Revertir estadísticas del fondo si era activa
                if old_status == FundInvestment.InvestmentStatus.ACTIVE:
                    FundInvestmentService._revert_fund_statistics(
                        investment.fund, investment.invested_amount, investment.tokens_allocated
                    )
                
                # 5. Marcar operación como exitosa
                FundInvestmentService._audit_critical_success(
                    audit_id=audit_id,
                    user=user,
                    additional_details={
                        'old_status': old_status,
                        'new_status': investment.status,
                        'cancellation_completed': True
                    }
                )
                
                return investment
            
        except Exception as e:
            if audit_id:
                FundInvestmentService._audit_critical_error(
                    audit_id=audit_id,
                    user=user,
                    error=e,
                    additional_details={
                        'investment_id': investment_id,
                        'operation': 'cancel_investment'
                    }
                )
            raise FundInvestmentError(f"Error al cancelar inversión: {str(e)}")
    
    @staticmethod
    def get_user_investments(user, fund_id: Optional[int] = None, status: Optional[str] = None):
        """
        📊 Obtener inversiones de un usuario
        
        Args:
            user: Usuario inversor
            fund_id: ID del fondo (opcional)
            status: Estado de la inversión (opcional)
            
        Returns:
            QuerySet: Inversiones del usuario
        """
        queryset = FundInvestment.objects.filter(investor=user).select_related('fund', 'application')
        
        if fund_id:
            queryset = queryset.filter(fund_id=fund_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_fund_investments(fund_id: int, user=None):
        """
        📈 Obtener inversiones de un fondo (solo para staff o gestores del fondo)
        
        Args:
            fund_id: ID del fondo
            user: Usuario que consulta (debe ser staff)
            
        Returns:
            QuerySet: Inversiones del fondo
        """
        if user and not user.is_staff:
            raise PermissionDenied("Only staff members can access fund investment data")
        
        return FundInvestment.objects.filter(
            fund_id=fund_id
        ).select_related('investor', 'application').order_by('-investment_date')
    
    #+ ========================================
    #+ Métodos privados de validación
    #+ ========================================    
    
    @staticmethod
    def _validate_token_purchase(investment: FundInvestment, user, token_quantity: int):
        """Validar compra de tokens"""
        if investment.investor != user:
            raise PermissionDenied("Can only purchase tokens for own investment")
        
        if investment.status != FundInvestment.InvestmentStatus.PENDING_TOKENS:
            raise ValidationError("Investment is not in correct status for token purchase")
        
        if token_quantity <= 0:
            raise ValidationError("Token quantity must be greater than zero")
    
    @staticmethod
    def _validate_investment_completion(investment: FundInvestment, user, tokens_to_use: int, final_amount: Decimal):
        """Validar finalización de inversión"""
        if investment.investor != user:
            raise PermissionDenied("Can only complete own investment")
        
        if investment.status != FundInvestment.InvestmentStatus.TOKENS_PURCHASED:
            raise ValidationError("Investment must have tokens purchased to complete")
        
        if tokens_to_use > investment.tokens_purchased:
            raise ValidationError("Cannot use more tokens than purchased")
        
        if tokens_to_use <= 0:
            raise ValidationError("Must use at least one token")
        
        if final_amount <= 0:
            raise ValidationError("Investment amount must be greater than zero")
        
        if investment.fund.current_price <= 0:
            raise ValidationError("Fund price must be greater than zero")
    
    #+ ========================================
    #+ Métodos privados de validación y cálculo
    #+ ========================================
    
    @staticmethod
    def _validate_can_purchase_tokens(investment: FundInvestment, user, payment_amount: Decimal):
        """Validar que se puede procesar la compra de tokens"""
        # 1. Verificar que es el inversor correcto
        if investment.investor != user:
            raise PermissionDenied("You can only purchase tokens for your own investments")
        
        # 2. Verificar estado de la inversión
        if investment.status != FundInvestment.InvestmentStatus.PENDING_TOKENS:
            raise ValidationError(f"Cannot purchase tokens for investment with status {investment.get_status_display()}")
        
        # 3. Verificar que el fondo sigue activo
        if investment.fund.status != 'active':
            raise ValidationError("Cannot purchase tokens for inactive fund")
        
        # 4. Validar amount positivo
        if payment_amount <= 0:
            raise ValidationError("Payment amount must be greater than zero")
        
        # 5. Validar límites del fondo (si aplica)
        if hasattr(investment.fund, 'minimum_investment') and investment.fund.minimum_investment:
            if payment_amount < investment.fund.minimum_investment:
                raise ValidationError(f"Payment amount below minimum investment ({investment.fund.minimum_investment})")
    
    @staticmethod
    def _validate_can_cancel(investment: FundInvestment, user):
        """Validar que se puede cancelar la inversión"""
        # 1. Verificar permisos
        if investment.investor != user and not user.is_staff:
            raise PermissionDenied("You can only cancel your own investments or be staff")
        
        # 2. Verificar estado
        if investment.status == FundInvestment.InvestmentStatus.CANCELLED:
            raise ValidationError("Investment is already cancelled")
        
        if investment.status == FundInvestment.InvestmentStatus.COMPLETED:
            raise ValidationError("Cannot cancel completed investment")
    
    """ @staticmethod
    def _calculate_tokens_for_payment(fund: Fund, payment_amount: Decimal) -> Decimal:
        
        try:
            # Usar función utilitaria existente si está disponible
            return calculate_tokens_for_amount(fund, payment_amount)
        except (ImportError, AttributeError, NameError):
            # Fallback: cálculo simple basado en precio del token
            if hasattr(fund, 'token_price') and fund.token_price:
                return payment_amount / fund.token_price
            else:
                # Asumir 1:1 ratio si no hay precio específico
                return payment_amount """
    
    @staticmethod
    def _update_fund_statistics(fund: Fund, amount: Decimal, tokens: Decimal):
        """Actualizar estadísticas del fondo después de una inversión"""
        # Actualizar campos estadísticos si existen
        if hasattr(fund, 'total_invested'):
            fund.total_invested = (fund.total_invested or Decimal('0')) + amount
        
        if hasattr(fund, 'tokens_sold'):
            fund.tokens_sold = (fund.tokens_sold or Decimal('0')) + tokens
        
        if hasattr(fund, 'investors_count'):
            # Contar inversores únicos
            unique_investors = FundInvestment.objects.filter(
                fund=fund,
                status=FundInvestment.InvestmentStatus.ACTIVE
            ).values('investor').distinct().count()
            fund.investors_count = unique_investors
        
        # Solo guardar si algún campo fue actualizado
        update_fields = []
        if hasattr(fund, 'total_invested'):
            update_fields.append('total_invested')
        if hasattr(fund, 'tokens_sold'):
            update_fields.append('tokens_sold')
        if hasattr(fund, 'investors_count'):
            update_fields.append('investors_count')
        
        if update_fields:
            update_fields.append('updated_at')
            fund.save(update_fields=update_fields)
    
    @staticmethod
    def _revert_fund_statistics(fund: Fund, amount: Decimal, tokens: Decimal):
        """Revertir estadísticas del fondo después de una cancelación"""
        if hasattr(fund, 'total_invested'):
            fund.total_invested = max(Decimal('0'), (fund.total_invested or Decimal('0')) - amount)
        
        if hasattr(fund, 'tokens_sold'):
            fund.tokens_sold = max(Decimal('0'), (fund.tokens_sold or Decimal('0')) - tokens)
        
        if hasattr(fund, 'investors_count'):
            unique_investors = FundInvestment.objects.filter(
                fund=fund,
                status=FundInvestment.InvestmentStatus.ACTIVE
            ).values('investor').distinct().count()
            fund.investors_count = unique_investors
        
        # Solo guardar si algún campo fue actualizado
        update_fields = []
        if hasattr(fund, 'total_invested'):
            update_fields.append('total_invested')
        if hasattr(fund, 'tokens_sold'):
            update_fields.append('tokens_sold')
        if hasattr(fund, 'investors_count'):
            update_fields.append('investors_count')
        
        if update_fields:
            update_fields.append('updated_at')
            fund.save(update_fields=update_fields)