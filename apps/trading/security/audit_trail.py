from apps.audit.audit_service import AuditService
from django.utils import timezone
import json

class TradingAuditTrail:
    """Sistema de auditoría especializado para trading"""
    
    @staticmethod
    def log_critical_action(user, action, details, request=None):
        """Log de acciones críticas con contexto completo"""
        
        critical_context = {
            'user_id': user.id,
            'user_email': user.email,
            'ip_address': request.META.get('REMOTE_ADDR') if request else None,
            'user_agent': request.META.get('HTTP_USER_AGENT') if request else None,
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'details': details,
            'session_key': request.session.session_key if request and hasattr(request, 'session') else None
        }
        
        # Log en base de datos
        AuditService.log_action(
            request=request,
            action_code=f'TRADING_{action}',
            obj=None,
            details=critical_context,
            status='LOGGED'
        )
        
        # Log adicional para compliance (archivo separado)
        import logging
        trading_logger = logging.getLogger('trading.compliance')
        trading_logger.info(f"TRADING_ACTION: {json.dumps(critical_context)}")