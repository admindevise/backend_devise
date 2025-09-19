from apps.audit.audit_service import AuditService

class InvestmentAuditService:
    @staticmethod
    def _create_pending_audit_log(application, request, action=None):
        """
        Crea un log de auditoría inicial con estado pendiente.
        
        Args:
            application: Instancia del objeto
            request: Objeto HttpRequest para auditoria
            action: Codigo referente a auditoria
        """
        if not request:
            return None
        return AuditService.log_action(
            request=request,
            action_code=action,
            obj=application,
            details={
              "user_email": application.user.email,
              "fund_name": application.fund.name
            },
            status="PENDING",
        )
    
    @staticmethod
    def _update_audit_success(audit_log):
        """Actualiza el log de auditoría con información de éxito."""
        if not audit_log:
            return
            
        audit_log.status = 'SUCCESS'
        audit_log.save(update_fields=['status'])
        
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
        
    # EXCLUSIVO DE (submit_investment)
    @staticmethod
    def _create_pending_audit_log_si(user, fund, request):
        """Crea un log de auditoría inicial con estado pendiente."""
        if not request:
            return None
        return AuditService.log_action(
            request=request,
            action_code='INVESTMENT_APPLICATION_CREATE',
            obj=user,
            details={
              "user_email": user.email,
              "fund_name": fund.name
            },
            status="PENDING",
        ) 
        
    # EXCLUSIVO DE (sign_contract)        
    @staticmethod
    def _create_audit_investment_approved(application, request):
        """Crea un log de auditoría para la aprobación de la inversión."""
        if not request:
            return None
        return AuditService.log_action(
            request=request,
            action_code='INVESTMENT_APPLICATION_APPROVED',
            obj=application,
            details={
              "user_email": application.user.email,
              "fund_name": application.fund.name,
              "application_id": application.id
            },
            status="SUCCESS",
        )
