from django.db import models
from django.utils import timezone
from datetime import timedelta

class UserAdminPermission(models.Model):
    """Modelo para gestionar permisos temporales que usuarios otorgan a admins"""
    
    PERMISSION_TYPES = [
        ('VIEW_PROFILE', 'Ver perfil completo'),
        ('EDIT_PROFILE', 'Editar información básica'),
        ('TRADING_VIEW', 'Ver órdenes de trading'),
        ('TRADING_MANAGE', 'Gestionar órdenes de trading'),
        ('FULL_ACCESS', 'Acceso total temporal'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('ACTIVE', 'Activo'),
        ('EXPIRED', 'Expirado'),
        ('REVOKED', 'Revocado'),
    ]
    
    user = models.ForeignKey(
        'User', 
        on_delete=models.CASCADE, 
        related_name='granted_permissions',
        help_text="Usuario que otorga el permiso"
    )
    admin_user = models.ForeignKey(
        'User', 
        on_delete=models.CASCADE, 
        related_name='received_permissions',
        help_text="Admin que recibe el permiso"
    )
    permission_type = models.CharField(
        max_length=20, 
        choices=PERMISSION_TYPES,
        help_text="Tipo de permiso otorgado"
    )
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='ACTIVE'
    )
    reason = models.TextField(
        help_text="Motivo por el cual se otorga el permiso"
    )
    
    # Fechas
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Fecha de expiración del permiso"
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Metadatos
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = ('user', 'admin_user', 'permission_type')
        verbose_name = "Permiso de Usuario a Admin"
        verbose_name_plural = "Permisos de Usuario a Admin"
    
    def is_valid(self):
        """Verifica si el permiso está vigente"""
        return (
            self.status == 'ACTIVE' and 
            self.expires_at > timezone.now()
        )
    
    def revoke(self):
        """Revoca el permiso"""
        self.status = 'REVOKED'
        self.revoked_at = timezone.now()
        self.save(update_fields=['status', 'revoked_at'])
    
    def mark_used(self):
        """Marca el permiso como usado recientemente"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
    
    def __str__(self):
        return f"{self.user.email} → {self.admin_user.email} ({self.permission_type})"