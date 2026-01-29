from apps.audit.audit_service import AuditService

class AuditHelperCreateOrders:
    """Helper para auditoría al crear órdenes de venta"""
    
    @staticmethod
    def initial_audit_log(user, action_code: str, request):
        """Registra la auditoría inicial al crear una orden de venta"""
        if not request:
            return None
        
        return AuditService.log_action(
            request=request,
            action_code=action_code,
            obj=user,   # Temporalmente el usuario como objeto
            details={
                'user_id': user.id,
                'user_email': user.email,
            },
            status='PENDING'
        )

    @staticmethod
    def update_audit_log(audit_log, type_order):
        """Actualiza la auditoría al completar la creación de una orden de venta"""
        if not audit_log:
            return
        
        from django.contrib.contenttypes.models import ContentType
        audit_log.content_type = ContentType.objects.get_for_model(type_order)
        audit_log.object_id = str(type_order.id)
        audit_log.status = 'SUCCESS'
        
        # Agregar detalles adicionales
        audit_log.details.update({
            'type_order_id': str(type_order.id),
            'trust_name': type_order.fund.name if hasattr(type_order, 'fund') else None,
            'price_per_unit': float(type_order.price_per_unit) if hasattr(type_order, 'price_per_unit') else None,
            'total_amount': float(type_order.total_amount) if hasattr(type_order, 'total_amount') else None,
        })
        
        audit_log.save(update_fields=['content_type', 'object_id', 'status', 'details'])
        
    @staticmethod
    def update_audit_log_error(audit_log, error: str):
        """Actualiza la auditoría en caso de error al crear una orden de venta"""
        if not audit_log:
            return
        
        audit_log.status = 'ERROR'
        audit_log.details.update({
            'error': str(error),
            'error_type': type(error).__name__,
        })
        audit_log.save(update_fields=['status', 'details'])