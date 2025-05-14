from django.db import models
from apps.utils.models import base_model
from apps.user.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

class AuditCategory(base_model.BaseModel):
    """Categorías de auditoría (transacciones, wallet, tokenización, etc.)"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = _("Categoría de Auditoría")
        verbose_name_plural = _("Categorías de Auditoría")

class AuditAction(base_model.BaseModel):
    """Acciones auditables (crear, transferir, quemar, etc.)"""
    category = models.ForeignKey(AuditCategory, on_delete=models.PROTECT, related_name="actions")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    severity = models.CharField(max_length=20, choices=[
        ('LOW', _('Baja')),
        ('MEDIUM', _('Media')),
        ('HIGH', _('Alta')),
        ('CRITICAL', _('Crítica'))
    ], default='MEDIUM')
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"
        
    class Meta:
        verbose_name = _("Acción Auditable")
        verbose_name_plural = _("Acciones Auditables")

class AuditLog(base_model.BaseModel):
    """Registro inmutable de eventos auditables"""
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="audit_logs")
    action = models.ForeignKey(AuditAction, on_delete=models.PROTECT, related_name="audit_logs")
    
    # Referencia genérica al objeto principal (Fund, Token, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Datos adicionales
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    #blockchain_tx_hash = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    details = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=[
        ('SUCCESS', _('Éxito')),
        ('ERROR', _('Error')),
        ('PENDING', _('Pendiente'))
    ], default='SUCCESS')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Registro de Auditoría")
        verbose_name_plural = _("Registros de Auditoría")
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.user} - {self.created_at}"