from django.db import models
from django.utils import timezone

class InvestorContract(models.Model):
    """
    Modelo para manejar contratos de vinculaciones a fondos.
    Responsabilidad: Gestionar el estado del contrato entre el usuario y el fondo.
    """
    class InvestorContractStatus(models.TextChoices):
        PENDING_SIGNATURE = 'pending_signature', 'Pendiente de Firma'
        CONTRACT_SIGNED = 'contract_signed', 'Contrato Firmado'
        SUSPENDED = 'suspended', 'Suspendido'
    
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name="investor_contracts",
        verbose_name="Fondo"
    )
    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name="investor_contracts",
        verbose_name="Usuario"
    )
    status = models.CharField(
        max_length=20,
        choices=InvestorContractStatus.choices,
        default=InvestorContractStatus.PENDING_SIGNATURE,
        verbose_name="Estado de aprobación"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    
    # ===========================================
    # ESCENARIO DE CONTRATO FIRMADO
    # ===========================================
    contract_url = models.URLField(
        null=True,
        blank=True,
        verbose_name="URL del contrato a firmar"
    )
    contract_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de firma del contrato"
    )
    expired_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de expiración para firma"
    )
    
    # ===========================================
    # ESCENARIO DE SUSPENSIÓN
    # ===========================================
    
    suspension_reason = models.TextField(
        null=True,
        blank=True, verbose_name="Motivo de suspensión"
    )
    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de suspensión"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contrato de Inversor"
        verbose_name_plural = "Contratos de Inversores"
    
    def __str__(self):
        return f"{self.user.email} - {self.fund.name} ({self.status})"
        
        
class InvestmentApplication(models.Model):
    """
    Modelo para manejar solicitudes de inversión en fondos.
    Responsabilidad: Gestionar el proceso de solicitud y aprobación.
    """
    
    class ApplicationStatus(models.TextChoices):
        PENDING = 'pending', 'Solicitud Pendiente'
        UNDER_REVIEW = 'under_review', 'En Revisión'
        ADDITIONAL_INFO_REQUIRED = 'additional_info_required', 'Info Adicional Requerida'
        CONTRACT_SENT = 'contract_sent', 'Contrato Enviado'
        PENDING_USER_SIGNATURE = 'pending_user_signature', 'Pendiente Firma Usuario'
        CONTRACT_SIGNED = 'contract_signed', 'Contrato Firmado'
        APPROVED = 'approved', 'Aprobada'
        REJECTED = 'rejected', 'Rechazada'
        WITHDRAWN = 'withdrawn', 'Retirada por Usuario'
        EXPIRED = 'expired', 'Expirada'
    
    class RejectionCategory(models.TextChoices):
        INSUFFICIENT_FUNDS = 'insufficient_funds', 'Fondos Insuficientes'
        INVALID_DOCUMENTATION = 'invalid_documentation', 'Documentación Inválida'
        RISK_PROFILE_MISMATCH = 'risk_profile_mismatch', 'Perfil de Riesgo No Compatible'
        REGULATORY_COMPLIANCE = 'regulatory_compliance', 'Cumplimiento Regulatorio'
        INVESTMENT_LIMITS = 'investment_limits', 'Límites de Inversión'
        FUND_CAPACITY = 'fund_capacity', 'Capacidad del Fondo'
        OTHER = 'other', 'Otro'
    
    # ========================================
    # RELACIONES BÁSICAS
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="Fondo"
    )
    
    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name="fund_applications",
        verbose_name="Solicitante"
    )
    
    # ========================================
    # INFORMACIÓN DE LA SOLICITUD
    # ========================================
    requested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Monto solicitado",
        help_text="Monto inicial solicitado por el usuario"
    )
    
    application_status = models.CharField(
        max_length=25,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        verbose_name="Estado de la solicitud"
    )
    
    # ========================================
    # CAMPOS DE REVISIÓN
    # ========================================
    reviewed_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_fund_applications",
        verbose_name="Revisado por"
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de revisión"
    )
    
    review_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas de revisión"
    )
    
    # ========================================
    # CAMPOS DE CONTRATO
    # ========================================
    contract_url = models.URLField(
        null=True,
        blank=True,
        verbose_name="URL del contrato de inversión"
    )
    
    contract_sent_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sent_fund_contracts",
        verbose_name="Contrato enviado por"
    )
    
    contract_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de envío del contrato"
    )
    
    contract_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de firma del contrato"
    )
    
    contract_signature_deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha límite para firmar"
    )
    
    # ========================================
    # CAMPOS DE RECHAZO
    # ========================================
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Razón del rechazo"
    )
    
    rejection_category = models.CharField(
        max_length=25,
        choices=RejectionCategory.choices,
        null=True,
        blank=True,
        verbose_name="Categoría de rechazo"
    )
    
    rejected_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rejected_fund_applications",
        verbose_name="Rechazado por"
    )
    
    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de rechazo"
    )
    
    can_reapply_after = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Puede volver a aplicar después de"
    )
    
    # ========================================
    # CAMPOS DE RETIRO
    # ========================================
    withdrawn_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="withdrawn_fund_applications",
        verbose_name="Retirado por"
    )
    
    withdrawn_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de retiro"
    )
    
    withdrawal_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de retiro"
    )
    
    # ========================================
    # ACEPTACIONES Y CONFIRMACIONES DE INVERSIÓN
    # ========================================
    accepts_terms_and_conditions = models.BooleanField(
        default=False,
        verbose_name="Acepta términos y condiciones de la inversión",
        help_text="Confirmación específica para esta inversión"
    )
    
    accepts_risk_disclosure = models.BooleanField(
        default=False,
        verbose_name="Acepta declaración de riesgos de la inversión",
        help_text="Confirmación específica de riesgos para esta inversión"
    )       
    
    # ========================================
    # METADATOS
    # ========================================
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )
    
    ip_address = models.CharField(
        null=True,
        blank=True,
        verbose_name="Dirección IP"
    )
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name="User Agent del navegador"
    )
    
    # ========================================
    # MÉTODOS DE VALIDACIÓN
    # ========================================
    def can_be_withdrawn(self):
        """Verificar si la solicitud puede ser retirada"""
        withdrawable_statuses = [
            self.ApplicationStatus.PENDING,
            self.ApplicationStatus.UNDER_REVIEW,
            self.ApplicationStatus.PRE_APPROVED,
            self.ApplicationStatus.CONTRACT_SENT,
            self.ApplicationStatus.PENDING_USER_SIGNATURE
        ]
        return self.application_status in withdrawable_statuses
    
    def can_be_approved(self):
        """Verificar si puede ser convertida en inversión"""
        return self.application_status == self.ApplicationStatus.CONTRACT_SIGNED
    
    @property
    def is_contract_expired(self):
        """Verificar si el contrato ha expirado"""
        return (
            self.contract_signature_deadline and 
            timezone.now() > self.contract_signature_deadline
        )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Solicitud de Inversión"
        verbose_name_plural = "Solicitudes de Inversión"
        indexes = [
            models.Index(fields=['application_status', 'created_at']),
            models.Index(fields=['fund', 'user']),
            models.Index(fields=['user', 'application_status']),
        ]
    
    def __str__(self):
        return f"{self.user.email} → {self.fund.name} (${self.requested_amount}) - {self.application_status}"


class FundInvestment(models.Model):
    """
    Modelo para manejar las inversiones activas en fondos.
    Responsabilidad: Gestionar la inversión activa y su rendimiento.
    """
    
    class InvestmentStatus(models.TextChoices):
        ACTIVE = 'active', 'Activa'
        MATURED = 'matured', 'Vencida'
        PARTIAL_WITHDRAWAL = 'partial_withdrawal', 'Retiro Parcial'
        FULLY_WITHDRAWN = 'fully_withdrawn', 'Totalmente Retirada'
        SUSPENDED = 'suspended', 'Suspendida'
        CLOSED = 'closed', 'Cerrada'
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PARTIAL = 'partial', 'Parcial'
        COMPLETED = 'completed', 'Completado'
        FAILED = 'failed', 'Fallido'
        REFUNDED = 'refunded', 'Reembolsado'
    
    # ========================================
    # RELACIÓN CON LA SOLICITUD APROBADA
    # ========================================
    application = models.OneToOneField(
        InvestmentApplication,
        on_delete=models.PROTECT,
        related_name="investment",
        verbose_name="Solicitud origen",
        null=True,
        blank=True
    )
    
    # ========================================
    # ACCESO DIRECTO A RELACIONES (Para convenience)
    # ========================================
    @property
    def fund(self):
        """Acceso directo al fondo"""
        return self.application.fund.id
    
    @property
    def fund_name(self):
        return self.application.fund.name
    
    @property
    def user(self):
        """Acceso directo al usuario"""
        return self.application.user.id
    
    @property
    def financial_institution_name(self):
        """Nombre del administrador del fondo"""
        if self.application and self.application.fund and self.application.fund.financial_institution:
            return self.application.fund.financial_institution.name
        return "N/A"
    
    # ========================================
    # INFORMACIÓN FINANCIERA DE LA INVERSIÓN
    # ========================================
    final_invested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Monto invertido final",
        null=True,
        blank=True
    )
    
    units_owned = models.IntegerField(
        default=0,
        verbose_name="Unidades poseídas"
    )
    
    purchase_price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio de compra por unidad"
    )
    
    current_unit_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valor actual por unidad"
    )
    
    # ========================================
    # RENDIMIENTOS Y GANANCIAS
    # ========================================
    total_dividends_received = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Total dividendos recibidos"
    )
    
    pending_dividends = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Dividendos pendientes"
    )
    
    realized_capital_gains = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Ganancias realizadas"
    )
    
    unrealized_capital_gains = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Ganancias no realizadas"
    )
    
    # ========================================
    # ESTADO Y FECHAS DE INVERSIÓN
    # ========================================
    investment_status = models.CharField(
        max_length=20,
        choices=InvestmentStatus.choices,
        default=InvestmentStatus.ACTIVE,
        verbose_name="Estado de la inversión"
    )
    
    maturity_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento"
    )
    
    # ========================================
    # INFORMACIÓN DE PAGO
    # ========================================
    payment_status = models.CharField(
        max_length=15,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="Estado del pago"
    )
    
    payment_method = models.CharField(
        max_length=30,
        choices=[
            ('bank_transfer', 'Transferencia Bancaria'),
            ('credit_card', 'Tarjeta de Crédito'),
            ('wire_transfer', 'Transferencia Internacional'),
            ('other', 'Otro'),
        ],
        null=True,
        blank=True,
        verbose_name="Método de pago"
    )
    
    payment_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Referencia de pago"
    )
    
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de pago confirmado"
    )
    
    # ========================================
    # CONFIGURACIONES DE INVERSIÓN
    # ========================================
    auto_reinvest_dividends = models.BooleanField(
        default=True,
        verbose_name="Reinversión automática de dividendos"
    )
    
    dividend_payment_preference = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Efectivo'),
            ('reinvest', 'Reinversión'),
            ('mixed', 'Mixto'),
        ],
        default='reinvest',
        verbose_name="Preferencia de pago de dividendos"
    )
    
    # ========================================
    # DOCUMENTACIÓN
    # ========================================
    payment_receipt = models.FileField(
        upload_to='investments/receipts/',
        null=True,
        blank=True,
        verbose_name="Comprobante de pago"
    ) 
    
    # ========================================
    # METADATOS
    # ========================================
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación de la inversión"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )
    
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name="created_fund_investments",
        verbose_name="Creado por"
    )
    
    # ========================================
    # MÉTODOS DE CÁLCULO
    # ========================================
    @property
    def current_total_value(self):
        """Valor total actual de la inversión"""
        if self.current_unit_value:
            return self.units_owned * self.current_unit_value
        return self.final_invested_amount
    
    @property
    def total_return(self):
        """Retorno total (realizado + no realizado + dividendos)"""
        return (
            self.realized_capital_gains + 
            self.unrealized_capital_gains + 
            self.total_dividends_received
        )
    
    @property
    def return_percentage(self):
        """Porcentaje de retorno"""
        if self.final_invested_amount > 0:
            return (self.total_return / self.final_invested_amount) * 100
        return 0
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Inversión en Fondo"
        verbose_name_plural = "Inversiones en Fondos"
        indexes = [
            models.Index(fields=['investment_status', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['maturity_date']),
        ]
    
    def __str__(self):
        return f"Inversión: {self.application.user.email} → {self.application.fund.name} (${self.final_invested_amount})"