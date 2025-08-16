from django.db import models
from django.utils import timezone
from datetime import timedelta

class UserAdminPermission(models.Model):
    """Modelo para gestionar permisos temporales que usuarios otorgan a admins"""
    
    PERMISSION_TYPES = [
        # Gestion de perfil de usuario
        ('VIEW_PROFILE', 'Ver perfil completo'),
        ('EDIT_PROFILE', 'Editar información básica'),
        ('TRADING_VIEW', 'Ver órdenes de trading'),
        ('TRADING_MANAGE', 'Gestionar órdenes de trading'),
        ('FULL_ACCESS', 'Acceso total temporal'),
    
        # Gestión de órdenes
        ('CREATE_PURCHASE_ORDER', 'Crear órdenes de compra'),
        ('CREATE_SALES_ORDER', 'Crear órdenes de venta'),
        ('CANCEL_ORDERS', 'Cancelar mis órdenes'),
        ('VIEW_ORDERS', 'Ver mis órdenes'),
        
        # Proceso de matching
        ('SELECT_MATCHES', 'Seleccionar matches para mis órdenes'),
        ('AUTO_SELECT_MATCHES', 'Permitir selección automática'),
        ('CANCEL_SELECTIONS', 'Cancelar selecciones de matches'),
        
        # Proceso de pago
        ('EXECUTE_PAYMENTS', 'Ejecutar pagos de mis órdenes'),
        ('VIEW_PAYMENT_STATUS', 'Ver estado de pagos'),
        
        # Permisos amplios
        ('TRADING_FULL_ACCESS', 'Acceso completo a trading'),
        ('FUND_SPECIFIC_ACCESS', 'Acceso específico a un fondo'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('ACTIVE', 'Activo'),
        ('EXPIRED', 'Expirado'),
        ('REVOKED', 'Revocado'),
    ]
    
    
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        null=True, blank=True,
        help_text="Fondo específico al que aplica (null = todos los fondos)"
    )
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
        max_length=50, 
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
    
    # Limites operacionales
    max_order_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        help_text="Monto máximo por orden (null = sin límite)"
    )
    
    max_daily_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        help_text="Monto máximo diario (null = sin límite)"
    )
    
    max_units_per_order = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Unidades máximas por orden (null = sin límite)"
    )
    
    # Configuración de comportamiento
    auto_approve_under_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        help_text="Auto-aprobar órdenes menores a este monto"
    )
    
    require_confirmation = models.BooleanField(
        default=True,
        help_text="Requiere confirmación del usuario antes de ejecutar"
    )
    
    # Tracking de uso
    usage_count = models.PositiveIntegerField(default=0)
    max_uses = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Máximo número de usos (null = ilimitado)"
    )
    
    last_amount_used = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True
    )
    
    total_amount_used = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0
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
    
class PermissionExecution(models.Model):
    """Registro de cada acción ejecutada con permiso"""
    
    permission = models.ForeignKey(
        UserAdminPermission,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    
    action_type = models.CharField(max_length=50)  # 'CREATE_ORDER', 'EXECUTE_PAYMENT', etc.
    
    # Contexto de la acción
    purchase_order = models.ForeignKey(
        'trading.PurchaseOrder',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    sales_order = models.ForeignKey(
        'trading.SalesOrder', 
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    units = models.PositiveIntegerField(null=True)
    
    # Resultado
    success = models.BooleanField()
    result_data = models.JSONField(default=dict)
    error_message = models.TextField(null=True, blank=True)
    
    # Metadata
    executed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['permission', 'executed_at']),
            models.Index(fields=['action_type', 'success']),
        ]

class PendingPermissionAction(models.Model):
    """Acciones que requieren confirmación del usuario"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
        ('EXPIRED', 'Expirado'),
    ]
    
    permission = models.ForeignKey(UserAdminPermission, on_delete=models.CASCADE)
    admin_user = models.ForeignKey('User', on_delete=models.CASCADE)
    
    action_type = models.CharField(max_length=50)
    action_description = models.TextField()
    action_data = models.JSONField()  # Datos de la orden/pago a ejecutar
    
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    fund = models.ForeignKey('fund.Fund', null=True, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # Auto-rechazar si no se responde
    responded_at = models.DateTimeField(null=True)
    
    # Respuesta del usuario
    user_response = models.TextField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['permission', 'requested_at']),
        ]