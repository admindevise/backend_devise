from django.contrib.contenttypes.models import ContentType
from apps.audit.models import AuditLog, AuditAction
from django.utils import timezone

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip, True

class AuditService:
    @staticmethod
    def log_action(request, action_code, obj, transaction_id=None, details=None, status='SUCCESS'):
        """
        Registra una acción auditable en el sistema.
        
        Args:
            request: Objeto request de Django
            action_code: Código de la acción (ej: "TRANSFER_TOKEN")
            obj: Objeto al que se refiere la acción (Fund, Token, etc.)
            transaction_id: ID de transacción (opcional)
            details: Diccionario con detalles adicionales (opcional)
            status: Estado de la acción ('SUCCESS', 'ERROR', 'PENDING')
        
        Returns:
            AuditLog: El registro de auditoría creado
        """
        try:
            action = AuditAction.objects.get(code=action_code)
            
            # Obtener IP y User Agent
            ip_address, _ = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Crear registro de auditoría
            audit_log = AuditLog.objects.create(
                user=request.user,
                action=action,
                content_type=ContentType.objects.get_for_model(obj),
                object_id=str(obj.id),
                transaction_id=transaction_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
                status=status
            )
            
            return audit_log
        except Exception as e:
            # Loggear el error pero no interrumpir el flujo
            print(f"Error logging action: {str(e)}")
            return None

    @staticmethod
    def update_transaction_status(audit_log_id, status):
        """
        Actualiza el estado de una transacción solo si está en estado PENDING
        """
        try:
            update_fields = {'status': status}
            
            # Solo actualizar los registros que estén en estado PENDING
            affected_rows = AuditLog.objects.filter(
                id=audit_log_id,
                status='PENDING'  # Solo actualizar si está en PENDING
            ).update(**update_fields)
            
            if affected_rows > 0:
                return AuditLog.objects.get(id=audit_log_id)
            else:
                # No se actualizó nada, posiblemente porque el registro estaba en ERROR
                # Obtener el registro para devolverlo sin modificar
                return AuditLog.objects.get(id=audit_log_id)
        except Exception as e:
            print(f"Error updating transaction status: {str(e)}")
            return None