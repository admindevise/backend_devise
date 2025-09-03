from decimal import Decimal
from typing import Tuple, Optional
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework import serializers
from django.db.models import QuerySet

from apps.fund.models.core import Fund
from apps.fund.models.membership import FundApplication, FundInvestment
from apps.audit.audit_service import AuditService
from apps.fund.services.investment_service import FundInvestmentService


class FundApplicationError(Exception):
    """Excepción personalizada para errores del servicio de aplicaciones a fondos"""
    pass


class FundApplicationService:
    """
    🏥 Servicio de Aplicaciones a Fondos - Maneja toda la lógica de negocio
    
    Responsabilidades:
    - Crear aplicaciones con validaciones de negocio
    - Aprobar/rechazar aplicaciones 
    - Gestionar estados y transiciones
    - Integración con auditoría y notificaciones
    """
    #+ ========================================
    #+ Métodos públicos del servicio
    #+ ========================================
    
    @staticmethod
    def create_application(fund_id: int, user, requested_amount: Decimal, notes: str = "", request=None) -> FundApplication:
        """
        Crear una nueva aplicación a un fondo con todas las validaciones
        
        Args:
            fund_id: ID del fondo al que se aplica
            user: Usuario que aplica
            requested_amount: Monto solicitado
            notes: Notas del aplicante (opcional)
            
        Returns:
            FundApplication: Nueva aplicación creada
            
        Raises:
            ValidationError: Si las validaciones de negocio fallan
        """
        with transaction.atomic():
            # 1. Validaciones de negocio
            fund = FundApplicationService._validate_fund_for_application(fund_id)
            FundApplicationService._validate_user_eligibility(fund, user, requested_amount)
            
            # 2. Crear la aplicación
            application = FundApplication.objects.create(
                fund=fund,
                applicant=user,
                requested_amount=requested_amount,
                applicant_notes=notes,
                status=FundApplication.ApplicationStatus.PENDING
            )
            
            # 3. Auditar creación usando request si está disponible
            if request:
                AuditService.log_action(
                    request=request,
                    action_code="INVESTMENT_APPLICATION_CREATE",
                    obj=application,
                    details={
                        'fund_id': fund.id,
                        'fund_name': fund.name,
                        'requested_amount': str(requested_amount),
                        'operation': 'create_application'
                    },
                    status='SUCCESS'
                )
            
            return application
    
    @staticmethod
    def approve_application(application_id: int, reviewer, review_notes: str = "", request=None) -> Tuple[FundApplication, FundInvestment]:
        """
        Aprobar una aplicación y crear inversión automáticamente
        
        Args:
            application_id: ID de la aplicación a aprobar
            reviewer: Usuario que revisa (debe ser staff)
            review_notes: Notas de la revisión (opcional)
            
        Returns:
            Tuple[FundApplication, FundInvestment]: Aplicación aprobada e inversión creada
            
        Raises:
            ValidationError: Si no se puede aprobar
            PermissionDenied: Si el usuario no tiene permisos
        """
        initial_audit = None
        
        try:
            with transaction.atomic():
                # 1. Obtener y validar aplicación
                application = FundApplication.objects.select_for_update().get(id=application_id)
                FundApplicationService._validate_can_approve(application, reviewer)
                
                # 2. Crear auditoría inicial si tenemos request
                if request:
                    initial_audit = AuditService.log_action(
                        request=request,
                        action_code="INVESTMENT_APPLICATION_APPROVED",
                        obj=application,
                        details={
                            'application_id': application.id,
                            'fund_id': application.fund.id,
                            'applicant_id': application.applicant.id,
                            'operation': 'approve_application'
                        },
                        status='PENDING'
                    )                
                
                # 3. Actualizar aplicación a aprobada
                old_status = application.status
                application.status = FundApplication.ApplicationStatus.APPROVED
                application.reviewed_by = reviewer
                application.reviewed_at = timezone.now()
                application.review_notes = review_notes
                application.save(update_fields=[
                    'status', 'reviewed_by', 'reviewed_at', 'review_notes', 'updated_at'
                ])
                
                # 4. Crear inversión automáticamente
                investment = FundApplicationService._create_investment_for_application(application)
                
                # 5. Actualizar auditoría a SUCCESS
                if initial_audit:
                    initial_audit.status = 'SUCCESS'
                    initial_audit.details.update({
                        'investment_id': investment.id,
                        'old_status': old_status,
                        'new_status': application.status,
                        'review_notes': review_notes,
                        'investment_status': investment.status
                    })
                    initial_audit.save(update_fields=['status', 'details'])
                
                return application, investment
                
        except Exception as e:
            # Auditar error
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                initial_audit.save(update_fields=['status', 'details'])
            
            raise e
    
    @staticmethod
    def reject_application(application_id: int, reviewer, rejection_reason: str, review_notes: str = "", request=None) -> FundApplication:
        """
        Rechazar una aplicación
        """
        initial_audit = None 
        
        try:
            with transaction.atomic():
                if not rejection_reason.strip():
                    raise ValidationError("rejection_reason is required when rejecting an application")
                
                # 1. Obtener y validar aplicación
                application = FundApplication.objects.select_for_update().get(id=application_id)
                FundApplicationService._validate_can_reject(application, reviewer)
                
                # 2. Crear auditoría inicial si tenemos request
                if request:
                    initial_audit = AuditService.log_action(
                        request=request, 
                        action_code="INVESTMENT_APPLICATION_REJECTED",
                        obj=application,
                        details={
                            'application_id': application.id,
                            'fund_id': application.fund.id,
                            'applicant_id': application.applicant.id,
                            'operation': 'reject_application'
                        },
                        status='PENDING'
                    )
                
                # 3. Actualizar aplicación a rechazada
                old_status = application.status
                application.status = FundApplication.ApplicationStatus.REJECTED
                application.reviewed_by = reviewer
                application.reviewed_at = timezone.now()
                application.rejection_reason = rejection_reason
                application.review_notes = review_notes
                application.save(update_fields=[
                    'status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 
                    'review_notes', 'updated_at'
                ])
                
                # 4. Actualizar auditoría a SUCCESS
                if initial_audit:
                    initial_audit.status = 'SUCCESS'
                    initial_audit.details.update({
                        'old_status': old_status,
                        'new_status': application.status,
                        'rejection_reason': rejection_reason,
                        'review_notes': review_notes
                    })
                    initial_audit.save(update_fields=['status', 'details'])
                
                return application
                
        except Exception as e:
            # Auditar error
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'rejection_reason': rejection_reason
                })
                initial_audit.save(update_fields=['status', 'details'])
            
            raise e
    
    @staticmethod
    def set_under_review(application_id: int, reviewer, review_notes: str = "", request=None) -> FundApplication:
        """
        Cambiar aplicación a estado "under review"
        """
        with transaction.atomic():
            # 1. Obtener y validar aplicación
            application = FundApplication.objects.select_for_update().get(id=application_id)
            
            # Validar permisos
            if not reviewer.is_staff:
                raise PermissionDenied("Only staff members can change application status")
            
            # Validar estado actual
            if application.status != FundApplication.ApplicationStatus.PENDING:
                raise ValidationError("Can only set pending applications under review")
            
            # Actualizar estado
            old_status = application.status
            application.status = FundApplication.ApplicationStatus.UNDER_REVIEW
            application.reviewed_by = reviewer
            application.reviewed_at = timezone.now()
            application.review_notes = review_notes
            application.save(update_fields=[
                'status', 'reviewed_by', 'reviewed_at', 'review_notes', 'updated_at'
            ])
            
            # Auditar cambio si tenemos request
            if request:
                AuditService.log_action(
                    request=request,  # ✅ Usar request directamente
                    action_code="INVESTMENT_APPLICATION_UNDER_REVIEW",
                    obj=application,
                    details={
                        'application_id': application.id,
                        'old_status': old_status,
                        'new_status': application.status,
                        'review_notes': review_notes,
                        'operation': 'set_under_review'
                    },
                    status='SUCCESS'
                )
            
            return application
        
    @staticmethod
    def get_user_applications(user, fund_id: Optional[int] = None) -> 'QuerySet[FundApplication]':
        """
        Obtener aplicaciones de un usuario
        
        Args:
            user: Usuario
            fund_id: ID del fondo (opcional, para filtrar)
            
        Returns:
            QuerySet: Aplicaciones del usuario
        """
        queryset = FundApplication.objects.filter(applicant=user).select_related('fund')
        
        if fund_id:
            queryset = queryset.filter(fund_id=fund_id)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_applications_for_review(reviewer) -> 'QuerySet[FundApplication]':
        """
        Obtener aplicaciones pendientes de revisión (solo para staff)
        
        Args:
            reviewer: Usuario revisor (debe ser staff)
            
        Returns:
            QuerySet: Aplicaciones pendientes de revisión
        """
        if not reviewer.is_staff:
            raise PermissionDenied("Only staff members can access applications for review")
        
        return FundApplication.objects.filter(
            status__in=[
                FundApplication.ApplicationStatus.PENDING,
                FundApplication.ApplicationStatus.UNDER_REVIEW
            ]
        ).select_related('fund', 'applicant').order_by('created_at')
    
    #+ ========================================
    #+ Métodos privados de validación
    #+ ========================================
    
    @staticmethod
    def _validate_fund_for_application(fund_id: int) -> Fund:
        """Validar que el fondo existe y está disponible para aplicaciones"""
        try:
            fund = Fund.objects.get(id=fund_id)
        except Fund.DoesNotExist:
            raise ValidationError("Fund does not exist.")
        
        if fund.status != 'active':
            raise ValidationError("Cannot apply to inactive fund")
        
        # Validar si el fondo está aceptando aplicaciones
        if hasattr(fund, 'accepting_applications') and not fund.accepting_applications:
            raise ValidationError("Fund is not currently accepting applications")
        
        # Validar fecha límite de aplicación
        if hasattr(fund, 'application_deadline') and fund.application_deadline:
            if timezone.now().date() > fund.application_deadline:
                raise ValidationError("Application deadline has passed for this fund")
        
        return fund
    
    @staticmethod
    def _validate_user_eligibility(fund: Fund, user, requested_amount: Decimal):
        """Validar que el usuario puede aplicar al fondo con el monto solicitado"""
        # 1. Verificar aplicación duplicada
        existing_application = FundApplication.objects.filter(
            fund=fund, 
            applicant=user,
            status__in=[
                FundApplication.ApplicationStatus.PENDING,
                FundApplication.ApplicationStatus.UNDER_REVIEW,
                FundApplication.ApplicationStatus.APPROVED
            ]
        ).exists()
        
        if existing_application:
            raise ValidationError("You already have an active application for this fund.")
        
        # 2. Validar monto positivo
        if requested_amount <= 0:
            raise ValidationError("Request amount must be greater than zero.")
        
        # 3. Validar monto mínimo del fondo
        if hasattr(fund, 'minimum_investment') and fund.minimum_investment:
            if requested_amount < fund.minimum_investment:
                raise ValidationError(f"Minimum investment for this fund is ({fund.minimum_investment})")
        
        # 4. Validar monto máximo del fondo
        if hasattr(fund, 'maximum_investment') and fund.maximum_investment:
            if requested_amount > fund.maximum_investment:
                raise ValidationError(f"Maximum investment for this fund is {fund.maximum_investment}")
        
        # 5. Validar capacidad disponible del fondo
        if hasattr(fund, 'amount_total') and fund.amount_total:
            if requested_amount > fund.amount_total:
                raise ValidationError(f"Requested amount exceeds fund available capacity ({fund.amount_total})")
        
        # 6. Validar perfil completo del usuario (si aplica)
        if hasattr(user, 'has_complete_profile') and not user.has_complete_profile:
            raise ValidationError("You must complete your profile before applying to funds")
    
    @staticmethod
    def _validate_can_approve(application: FundApplication, reviewer):
        """Validar que la aplicación puede ser aprobada"""
        # 1. Verificar permisos
        if not reviewer.is_staff:
            raise PermissionDenied("Only staff members can approve applications")
        
        # 2. Verificar estado de la aplicación
        if application.status not in [
            FundApplication.ApplicationStatus.PENDING,
            FundApplication.ApplicationStatus.UNDER_REVIEW
        ]:
            raise ValidationError(f"Cannot approve application with status {application.get_status_display()}")
        
        # 3. Verificar que el fondo sigue activo
        if application.fund.status != 'active':
            raise ValidationError("Cannot approve application for inactive fund")
        
        # 4. Verificar que no existe ya una inversión
        if hasattr(application, 'investment'):
            raise ValidationError("Investment already exists for this application")
    
    @staticmethod
    def _validate_can_reject(application: FundApplication, reviewer):
        """Validar que la aplicación puede ser rechazada"""
        # 1. Verificar que el revisor es staff
        if not reviewer.is_staff:
            raise PermissionDenied("Only staff members can reject applications")
        
        # 2. Verificar estado de la aplicación
        if application.status == FundApplication.ApplicationStatus.REJECTED:
            raise serializers.ValidationError("Application is already rejected")
        
        if application.status == FundApplication.ApplicationStatus.APPROVED:
            raise serializers.ValidationError("Cannot reject an already approved application")
    
    @staticmethod
    def _create_investment_for_application(application: FundApplication) -> FundInvestment:
        """
        Crear inversión cuando se aprueba una aplicación
        
        Args:
            application: Aplicación aprobada
            
        Returns:
            FundInvestment: Nueva inversión creada
        """
        # Usar el servicio de inversiones para crear la inversión
        return FundInvestmentService.create_for_approved_application(application)