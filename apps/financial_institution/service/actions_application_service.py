from typing import Optional, Tuple
from django.db import transaction
from django.utils import timezone
from apps.financial_institution.models import FinancialInstitutionApplication, FinancialInstitutionApproval
from apps.audit.audit_service import AuditService

class FIActionsError(Exception):
    """Excepción personalizada para errores en aplicaciones de instituciones financieras."""
    pass

class FIActionsService:
    """Servicio para manejar acciones relacionadas con solicitudes de instituciones financieras."""
    
    @staticmethod
    @transaction.atomic
    def pre_approve_application(
        application_id: int,
        pre_approved_by,
        review_notes: str = "",
        max_investment_amount: Optional[float] = None,
        request=None
    ) -> FinancialInstitutionApplication:
        """Pre-aprobar una solicitud específica"""
        
        initial_audit = None
        
        try:
            if request:
                initial_audit = AuditService.log_action(
                    request=request,
                    action_code="FI_MEMBERSHIP_PRE_APPROVAL",
                    obj=pre_approved_by,
                    details={
                        'application_id': application_id,
                        'pre_approved_by': pre_approved_by.id,
                        'pre_approval_notes': review_notes,
                        'operation': 'pre_approve_application'
                    },
                    status='PENDING'
                )
        
            # 1. Obtener y bloquear la solicitud
            application = FIActionsService.obtain_application(application_id)
            
            # Actualizar objeto de auditoría
            FIActionsService.update_audit_log(initial_audit, application)
            
            # 2. Validar estado actual
            if application.status != FinancialInstitutionApplication.ApplicationStatus.PENDING:
                raise ValueError("Solo se pueden pre-aprobar solicitudes pendientes")
            
            # 3. Actualizar aplicación
            application.status = FinancialInstitutionApplication.ApplicationStatus.UNDER_REVIEW
            application.reviewed_by = pre_approved_by
            application.reviewed_at = timezone.now()
            application.review_notes = review_notes
            application.save()
            
            # 4. Crear la aprobacion activa (sin detalles aún)
            approval = FinancialInstitutionApproval.objects.create(
                application=application,
                approved_by=pre_approved_by,
                max_investment_amount=max_investment_amount,
                investor_profile='',
                allowed_fund_types=[],
                approval_notes='',
                conditions='',
                expiry_date=None
            )
            
            # Actualizar auditoría a éxito
            FIActionsService.audit_log_success(initial_audit, approval)
            
            return application, approval
        
        except Exception as e:
            # Auditar error
            FIActionsService.audit_log_error(initial_audit, e, application)
            
            # Re-lanzar la excepción apropiada
            if isinstance(e, ValueError):
                raise e
            else:
                raise FIActionsError(f"Error al pre-aprovar solicitud de ingreso a {application.financial_institution.name}: {str(e)}")
            
    @staticmethod
    @transaction.atomic
    def send_contract(
        application_id: int,
        sent_by,
        contract_url: str,
        send_notes: str = "",
        request=None
    ) -> FinancialInstitutionApplication:
        """Enviar contrato a un solicitante pre-aprobado"""
        
        initial_audit = None
        
        try:
            if request:
                initial_audit = AuditService.log_action(
                    request=request,
                    action_code="FI_MEMBERSHIP_SEND_CONTRACT",
                    obj=sent_by,
                    details={
                        'application_id': application_id,
                        'sent_by': sent_by.id,
                        'contract_url': contract_url,
                        'send_notes': send_notes,
                        'operation': 'send_contract'
                    },
                    status='PENDING'
                )

            # 1. Obtener y bloquear la solicitud
            application = FIActionsService.obtain_application(application_id)
            
            # Actualizar objeto de auditoría
            FIActionsService.update_audit_log(initial_audit, application)
            
            # 2. Validar que tenga una pre-aprobación
            FIActionsService.check_approval_exists(application)
            approval = application.approval
            
            # 3. Validar estado actual
            if application.status != FinancialInstitutionApplication.ApplicationStatus.UNDER_REVIEW:
                raise ValueError("Solo se pueden enviar contratos para solicitudes en revisión")
            
            # 4. Validar estado de la aprobación
            status_list = [
                FinancialInstitutionApproval.ApprovalStatus.PRE_APPROVED, FinancialInstitutionApproval.ApprovalStatus.PRE_APPROVED_WITH_CHANGES
            ]
            if approval.status not in status_list:
                raise ValueError("La aprobación asociada no está en un estado válido para enviar el contrato")
            
            # 5. Actualizar aplicación - Contrato enviado, esperando firma
            application.status = FinancialInstitutionApplication.ApplicationStatus.PENDING_USER_SIGNATURE
            application.save(update_fields=['status'])
            
            # 6. Actualizar aprobación - Contrato enviado
            #application.contract_sent_by = sent_by
            approval.status = FinancialInstitutionApproval.ApprovalStatus.CONTRACT_SENT
            approval.contract_generated_at = timezone.now()
            approval.contract_sent_at = timezone.now()
            approval.save(update_fields=['status', 'contract_generated_at', 'contract_sent_at'])
            
            # 7. Actualizar auditoría a éxito
            FIActionsService.audit_log_success(initial_audit, approval)
            
            return application, approval
        
        except Exception as e:
            # Auditar error
            FIActionsService.audit_log_error(initial_audit, e, application)
            
            # Re-lanzar la excepción apropiada
            if isinstance(e, ValueError):
                raise e
            else:
                raise FIActionsError(f"Error al enviar contrato de ingreso al fondo: {str(e)}")

    @staticmethod
    @transaction.atomic
    def user_sign_contract(
        application_id: int,
        signed_by,
        signature_method: str,
        user_signature_notes: str = "",
        request=None
    ) -> FinancialInstitutionApplication:
        """Marcar contrato como firmado por el usuario"""
        
        initial_audit = None
        
        try:
            if request:
                initial_audit = AuditService.log_action(
                    request=request,
                    action_code="FI_MEMBERSHIP_SIGN_CONTRACT",
                    obj=signed_by,
                    details={
                        'application_id': application_id,
                        'signed_by': signed_by.id,
                        'operation': 'user_sign_contract'
                    },
                    status='PENDING'
                )

            # 1. Obtener y bloquear la solicitud
            application = FIActionsService.obtain_application(application_id)
            
            # Actualizar objeto de auditoría
            FIActionsService.update_audit_log(initial_audit, application)
            
            # 2. Validar que tenga una aprobación
            FIActionsService.check_approval_exists(application)
            approval = application.approval
            
            # 3. Validar estado actual
            if application.status != FinancialInstitutionApplication.ApplicationStatus.PENDING_USER_SIGNATURE:
                raise ValueError("Solo se pueden marcar como firmados los contratos de solicitudes que están pendientes de firma del usuario")
            
            # 4. Validar estado de la aprobación
            if approval.status != FinancialInstitutionApproval.ApprovalStatus.CONTRACT_SENT:
                raise ValueError("La aprobación asociada no está en un estado válido para marcar el contrato como firmado")
            
            # 5. Actualizar aplicación - Contrato firmado, esperando revisión interna
            application.status = FinancialInstitutionApplication.ApplicationStatus.UNDER_REVIEW_FINAL
            application.save(update_fields=['status'])
            
            # 6. Actualizar aprobación - Contrato firmado
            approval.status = FinancialInstitutionApproval.ApprovalStatus.CONTRACT_SIGNED
            approval.contract_signed_at = timezone.now()
            approval.signature_method = signature_method
            approval.user_signature_notes = user_signature_notes
            approval.save(update_fields=['status', 'contract_signed_at', 'signature_method', 'user_signature_notes'])
            
            # 7. Actualizar auditoría a éxito
            FIActionsService.audit_log_success(initial_audit, approval)
            
            return application, approval
        except Exception as e:
            # Auditar error
            FIActionsService.audit_log_error(initial_audit, e, application)
            
            # Re-lanzar la excepción apropiada
            if isinstance(e, ValueError):
                raise e
            else:
                raise FIActionsError(f"Error al marcar contrato como firmado por el usuario: {str(e)}")

    @staticmethod
    @transaction.atomic
    def approve_application(
        application_id: int,
        approved_by,
        approval_notes: str = "",
        conditions: str = "",
        expiry_date=None,
        request=None
    ) -> Tuple[FinancialInstitutionApplication, FinancialInstitutionApproval]:
        """Aprobar solicitud y crear aprobación activa"""
        initial_audit = None
        
        try:
            if request:
                initial_audit = AuditService.log_action(
                    request=request,
                    action_code="FI_MEMBERSHIP_APPROVE",
                    obj=approved_by,
                    details={
                        'application_id': application_id,
                        'approved_by': approved_by.id,
                    },
                    status='PENDING'
                )
        
            # 1. Obtener y bloquear la solicitud
            application = FIActionsService.obtain_application(application_id)
            
            # Actualizar objeto de auditoría
            FIActionsService.update_audit_log(initial_audit, application)
            # 2. Validar estado actual
            if application.status != FinancialInstitutionApplication.ApplicationStatus.UNDER_REVIEW_FINAL:
                raise ValueError("Solo se pueden aprobar solicitudes en revisión final")
            
            # 4. Validar que tenga una aprobación preliminar
            FIActionsService.check_approval_exists(application)
            approval = application.approval
            
            # 5. Actualizar aplicación
            application.status = FinancialInstitutionApplication.ApplicationStatus.APPROVED
            application.reviewed_by = approved_by
            application.reviewed_at = timezone.now()
            application.review_notes = approval_notes
            application.save()
            
            # 6. Actualizar aprobación
            approval.status = FinancialInstitutionApproval.ApprovalStatus.ACTIVE
            approval.approved_by = approved_by
            approval.approval_date = timezone.now()
            approval.approval_notes = approval_notes
            approval.conditions = conditions
            approval.expiry_date = expiry_date
            approval.save()
            
            # Actualizar auditoría a éxito
            FIActionsService.audit_log_success(initial_audit, approval)
            
            return application, approval
        except Exception as e:
            # Auditar error
            FIActionsService.audit_log_error(initial_audit, e, application)
            
            # Re-lanzar la excepción apropiada
            if isinstance(e, ValueError):
                raise e
            else:
                raise FIActionsError(f"Error al aprobar solicitud de ingreso: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def reject_application(
        application_id: int,
        reviewed_by,
        rejection_reason: str,
        rejection_category: Optional[str] = None,
        can_reapply_after: Optional[timezone.datetime] = None,
        review_notes: str = "",
        request=None
    ) -> FinancialInstitutionApplication:
        """Rechazar solicitud"""
        initial_audit = None
        application = None
        
        try:
            if request:
                initial_audit = AuditService.log_action(
                    request=request,
                    action_code="FI_MEMBERSHIP_REJECT",
                    obj=reviewed_by,
                    details={
                        'application_id': application_id,
                        'reviewed_by': reviewed_by.id,
                        'rejection_reason': rejection_reason,
                        'rejection_category': rejection_category,
                        'can_reapply_after': can_reapply_after.isoformat() if can_reapply_after else None,
                        'review_notes': review_notes,
                        'operation': 'reject_application'
                    },
                    status='PENDING'
                )
            # 1. Obtener y bloquear la solicitud
            application = FIActionsService.obtain_application(application_id)
            
            # Actualizar objeto de auditoría
            FIActionsService.update_audit_log(initial_audit, application)
            
            # 2. Validar estados permitidos para rechazo
            rejectable_statuses = [
                FinancialInstitutionApplication.ApplicationStatus.PENDING,
                FinancialInstitutionApplication.ApplicationStatus.UNDER_REVIEW,
                FinancialInstitutionApplication.ApplicationStatus.ADDITIONAL_INFO_REQUIRED,
                FinancialInstitutionApplication.ApplicationStatus.PENDING_USER_SIGNATURE,
                FinancialInstitutionApplication.ApplicationStatus.UNDER_REVIEW_FINAL
            ]
            
            if application.status not in rejectable_statuses:
                if application.status == FinancialInstitutionApplication.ApplicationStatus.REJECTED:
                    raise ValueError("La solicitud ya ha sido rechazada")
                elif application.status == FinancialInstitutionApplication.ApplicationStatus.APPROVED:
                    raise ValueError("No se puede rechazar una solicitud ya aprobada")
                else:
                    raise ValueError(f"No se puede rechazar una solicitud en estado: {application.status}")
        
            
            # 3. Validar estado actual
            application.status = FinancialInstitutionApplication.ApplicationStatus.REJECTED
            application.reviewed_by = reviewed_by
            application.reviewed_at = timezone.now()
            application.rejection_category = rejection_category
            application.can_reapply_after = can_reapply_after
            application.rejection_reason = rejection_reason
            application.review_notes = review_notes
            application.save()
            
            # Actualizar auditoría a éxito
            initial_audit.status = 'SUCCESS'
            initial_audit.save(update_fields=['status'])
            
            return application
        
        except Exception as e:
            # Auditar error
            FIActionsService.audit_log_error(initial_audit, e, application)
            
            # Re-lanzar la excepción apropiada
            if isinstance(e, ValueError):
                raise e
            else:
                raise FIActionsError(f"Error al rechazar solicitud de ingreso: {str(e)}")
    
    
    # ==========================================
    # Métodos auxiliares
    # ==========================================
    
    @staticmethod
    def obtain_application(application_id: int) -> FinancialInstitutionApplication:
        try:
            application = FinancialInstitutionApplication.objects.select_for_update().get(id=application_id)
        except FinancialInstitutionApplication.DoesNotExist:
            raise ValueError(f"Solicitud con ID {application_id} no encontrada")
        return application
    
    @staticmethod
    def update_audit_log(initial_audit, application):
        if initial_audit:
            from django.contrib.contenttypes.models import ContentType
            application_content_type = ContentType.objects.get_for_model(FinancialInstitutionApplication)
            initial_audit.content_type = application_content_type
            initial_audit.object_id = application.id
            initial_audit.details.update({
                'FI_id': application.financial_institution.id,
                'FI_name': application.financial_institution.name,
                'user_id': application.user.id,
                'requested_amount': str(application.requested_investment_amount)
            })
            initial_audit.save(update_fields=['content_type', 'object_id', 'details'])
    
    @staticmethod
    def audit_log_success(initial_audit, approval):
        if initial_audit:
            initial_audit.status = 'SUCCESS'
            initial_audit.details.update({
                'approval_id': approval.id
            })
            initial_audit.save(update_fields=['status', 'details'])
    
    @staticmethod
    def audit_log_error(initial_audit, error_msg, application=None):
        if initial_audit:
            initial_audit.status = 'ERROR'
            initial_audit.details.update({
                'error': str(error_msg),
                'error_type': type(error_msg).__name__,
                'application_id': application.id if application else None
            })
            initial_audit.save(update_fields=['status', 'details'])
            
    @staticmethod
    def check_approval_exists(application):
        if not hasattr(application, 'approval') or not application.approval:
            raise ValueError("La solicitud no tiene una pre-aprobación asociada")


    # ============================================
    # METODOS PUBLICOS
    # ============================================
    
    @staticmethod
    def get_approved_amount(user: int):
        """Obtiene el monto aprobado para un usuario en especifico"""
        
        # Buscar todas las aprobaciones activas del usuario
        approvals = FinancialInstitutionApproval.objects.select_related('application').filter(
            application__user=user,
            status=FinancialInstitutionApproval.ApprovalStatus.ACTIVE
        ).order_by('-approval_date')
        
        if not approvals.exists():
            raise ValueError(f"El usuario {user.email} no tiene aprobaciones activas para inversiones")
        
        # Tomar la aprobación más reciente y verificar si no ha expirado
        latest_approval = approvals.first()
        
        if latest_approval.expiry_date and timezone.now().date() > latest_approval.expiry_date:
            raise ValueError(f"La aprobación más reciente del usuario {user.email} ha expirado")
        
        return latest_approval.max_investment_amount