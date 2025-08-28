from django.db import transaction, models
from django.utils import timezone
from typing import Tuple, Optional

from apps.financial_institution.models import FinancialInstitutionApplication, FinancialInstitutionApproval

class FinancialInstitutionApplicationService:
    """
    Servicio para gestionar el flujo completo de solicitudes y aprobaciones
    """
    
    @staticmethod
    @transaction.atomic
    def submit_application(
        user, 
        financial_institution, 
        requested_investor_profile: str,
        requested_investment_amount: Optional[float] = None,
        application_notes: str = "",
        kyc_documents: dict = None
    ) -> FinancialInstitutionApplication:
        """Crear nueva solicitud"""
            
        base_filter = {
            'user': user,
            'financial_institution': financial_institution
        }
        
        # 1. Verificar solicitudes activas (UNA consulta específica)
        active_statuses = ['pending', 'under_review', 'approved', 'additional_info']
        has_active = FinancialInstitutionApplication.objects.select_for_update().filter(
            **base_filter,
            status__in=active_statuses
        ).exists()
        
        if has_active:
            raise ValueError("Ya tienes una solicitud pendiente con esta institución")
        
        # 2. Verificar rechazos permanentes (UNA consulta específica)
        has_permanent_rejection = FinancialInstitutionApplication.objects.select_for_update().filter(
            **base_filter,
            status='rejected',
            rejection_category__in=['fraud', 'compliance']
        ).exists()
        
        if has_permanent_rejection:
            raise ValueError("Tu solicitud ha sido rechazada permanentemente y no puedes volver a aplicar")
        
        # 3. Verificar restricciones de tiempo (UNA consulta específica)
        latest_rejected = FinancialInstitutionApplication.objects.select_for_update().filter(
            **base_filter,
            status='rejected',
            can_reapply_after__gt=timezone.now().date()  # Solo los que tienen restricción activa
        ).order_by('-reviewed_at').first()
        
        if latest_rejected:
            raise ValueError(
                f"No puedes volver a aplicar hasta el {latest_rejected.can_reapply_after.strftime('%d/%m/%Y')}"
            )
        
        # 4. Crear nueva solicitud
        application = FinancialInstitutionApplication.objects.create(
            user=user,
            financial_institution=financial_institution,
            requested_investor_profile=requested_investor_profile,
            requested_investment_amount=requested_investment_amount,
            application_notes=application_notes,
            kyc_documents=kyc_documents or {}
        )
        
        return application
    
    @staticmethod
    @transaction.atomic
    def approve_application(
        application_id: int,
        approved_by,
        investor_profile: str,
        max_investment_amount: Optional[float] = None,
        allowed_fund_types: list = None,
        approval_notes: str = "",
        conditions: str = "",
        expiry_date=None
    ) -> Tuple[FinancialInstitutionApplication, FinancialInstitutionApproval]:
        """Aprobar solicitud y crear aprobación activa"""
        
        if not approved_by.is_staff:
            raise ValueError("Solo el personal autorizado puede aprobar solicitudes")
        
        application = FinancialInstitutionApplication.objects.get(id=application_id)
        
        if application.status != 'pending':
            raise ValueError("Solo se pueden aprobar solicitudes pendientes")
        
        # Actualizar aplicación
        application.status = FinancialInstitutionApplication.ApplicationStatus.APPROVED
        application.reviewed_by = approved_by
        application.reviewed_at = timezone.now()
        application.review_notes = approval_notes
        application.save()
        
        # Crear aprobación activa
        approval = FinancialInstitutionApproval.objects.create(
            application=application,
            approved_by=approved_by,
            investor_profile=investor_profile,
            max_investment_amount=max_investment_amount,
            allowed_fund_types=allowed_fund_types or [],
            approval_notes=approval_notes,
            conditions=conditions,
            expiry_date=expiry_date
        )
        
        return application, approval
    
    @staticmethod
    def reject_application(
        application_id: int,
        reviewed_by,
        rejection_reason: str,
        rejection_category: Optional[str] = None,
        can_reapply_after: Optional[timezone.datetime] = None,
        review_notes: str = ""
    ) -> FinancialInstitutionApplication:
        """Rechazar solicitud"""
        
        application = FinancialInstitutionApplication.objects.get(id=application_id)
        
        application.status = FinancialInstitutionApplication.ApplicationStatus.REJECTED
        application.reviewed_by = reviewed_by
        application.reviewed_at = timezone.now()
        application.rejection_category = rejection_category
        application.can_reapply_after = can_reapply_after
        application.rejection_reason = rejection_reason
        application.review_notes = review_notes
        application.save()
        
        return application