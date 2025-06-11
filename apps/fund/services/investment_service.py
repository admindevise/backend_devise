from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from apps.fund.models import Fund, FundApplication, FundInvestment
from apps.audit.audit_service import AuditService

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
                status=FundInvestment.InvestmentStatus.APPROVED,
                # invested_amount se establecerá cuando complete la inversión
            )
            
            if request:
                AuditService.log_action(
                    user=request,
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
    
    @staticmethod
    def cancel_investment(investment_id: int, user, cancellation_reason: str) -> FundInvestment:
        """
        Cancelar una inversión
        
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
        Obtener inversiones de un usuario
        
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
        Obtener inversiones de un fondo (solo para staff o gestores del fondo)
        
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