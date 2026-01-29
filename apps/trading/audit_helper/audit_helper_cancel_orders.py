from apps.audit.audit_service import AuditService

class AuditHelperCancelOrders:
    """Helper para auditoría al cancelar órdenes de venta"""
    
    @staticmethod
    def initial_audit_log(user, order_id, action_code: str, reason: str, request):
        """Registra la auditoría al cancelar una orden de venta"""
        if not request:
            return None
        
        return AuditService.log_action(
            request=request,
            action_code=action_code,
            obj=user,   # Temporalmente el usuario como objeto
            details={
                'user_id': user.id,
                'user_email': user.email,
                'order_id': str(order_id),
                'reason': str(reason),
            },
            status='SUCCESS'
        )
        
    @staticmethod
    def update_audit_log(audit_log, type_order):
        """Actualiza la auditoría al completar la cancelación de una orden de venta"""
        if not audit_log:
            return
        
        from django.contrib.contenttypes.models import ContentType
        audit_log.content_type = ContentType.objects.get_for_model(type_order.__class__)
        audit_log.object_id = str(type_order.id)
        audit_log.save(update_fields=['content_type', 'object_id'])
        
    @staticmethod
    def update_audit_log_error(audit_log, error: str):
        """Actualiza la auditoría en caso de error al cancelar una orden de venta"""
        if not audit_log:
            return
        
        audit_log.status = 'ERROR'
        audit_log.details.update({
            'error': str(error),
            'error_type': type(error).__name__,
        })
        audit_log.save(update_fields=['status', 'details'])