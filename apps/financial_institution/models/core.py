from django.db import models
from cities_light.models import Country, Region, City
from django.utils import timezone

class FinancialInstitution(models.Model):
    """
    Entidades reguladoras que pueden operar en la plataforma
    """
    
    class FinancialInstitutionType(models.TextChoices):
        FUND_MANAGER = 'fund_manager', 'Administradora de Fondos'
        BROKER_DEALER = 'broker_dealer', 'Comisionista de Bolsa'
        FIDUCIARY = 'fiduciary', 'Fiduciaria'
        INSURANCE = 'insurance', 'Aseguradora'
        BANK = 'bank', 'Banco'
        PENSION_FUND = 'pension_fund', 'Fondo de Pensiones'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activa'
        SUSPENDED = 'suspended', 'Suspendida'
        UNDER_REVIEW = 'under_review', 'En Revisión'
        INACTIVE = 'inactive', 'Inactiva'
    
    # ========================================
    # INFORMACIÓN BÁSICA
    # ========================================
    name = models.CharField(max_length=200, verbose_name="Nombre de la entidad")
    short_name = models.CharField(max_length=50, verbose_name="Nombre corto")
    institution_type = models.CharField(max_length=20, choices=FinancialInstitutionType.choices)
    nit = models.CharField(max_length=20, unique=True, verbose_name="NIT")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    logo = models.ImageField(upload_to='financial_institution/logos/', blank=True, null=True, verbose_name="Logo")
    entity_code = models.CharField(max_length=50, unique=True, verbose_name="Código de la entidad")
    established_date = models.DateField(verbose_name="Fecha de constitución")
    country = models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        related_name='country_financial_institutions',
        blank=True, null=True
        )
    region = models.ForeignKey(
        Region,
        on_delete = models.PROTECT,
        related_name='region_financial_institutions',
        blank=True, null=True
    )
    city = models.ForeignKey(
        City,
        on_delete = models.PROTECT,
        related_name='city_financial_institutions',
        blank=True, null=True
        )
    registration_number = models.CharField(max_length=50, unique=True, verbose_name="Número de registro")
    tax_id = models.CharField(max_length=50, verbose_name="ID Fiscal")
    
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE, 
        related_name='created_financial_institutions',
        verbose_name="Creado por"
    )
    
    # ========================================
    # INFORMACIÓN REGULATORIA
    # ========================================
    superfinanciera_code = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Código Superfinanciera"
    )
    license_number = models.CharField(max_length=50, verbose_name="Número de licencia")
    license_expiry_date = models.DateField(verbose_name="Fecha de vencimiento de licencia")
    
    # ========================================
    # CONFIGURACIÓN OPERATIVA
    # ========================================
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    max_funds_allowed = models.PositiveIntegerField(default=50, verbose_name="Máximo fondos permitidos")
    
    # ========================================
    # CONFIGURACIÓN DE USUARIOS
    # ========================================
    requires_kyc_validation = models.BooleanField(
        default=True, 
        verbose_name="Requiere validación KYC"
    )
    auto_approve_threshold = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Umbral de auto-aprobación",
        help_text="Monto bajo el cual se auto-aprueban inversiones"
    )
    
    # ========================================
    # CONTACTO E INFORMACIÓN
    # ========================================
    contact_email = models.EmailField(verbose_name="Email de contacto")
    indicative = models.CharField(max_length=32, verbose_name="Indicativo telefónico", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono")
    address = models.TextField(verbose_name="Dirección")
    website = models.URLField(blank=True, null=True, verbose_name="Sitio web")
    
    # ========================================
    # CONFIGURACIÓN TÉCNICA
    # ========================================
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key")
    webhook_url = models.URLField(blank=True, null=True, verbose_name="URL de webhook")
    notification_email = models.EmailField(verbose_name="Email para notificaciones")
    
    # ========================================
    # FECHAS
    # ========================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Financial Institution"
        verbose_name_plural = "Instituciones Financieras"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_institution_type_display()})"
    
    @property
    def is_license_valid(self):
        """Verifica si la licencia está vigente"""
        from datetime import date
        return self.license_expiry_date >= date.today()
    
    @property
    def can_operate(self):
        """Verifica si la entidad puede operar"""
        return self.status == self.Status.ACTIVE and self.is_license_valid
    
    
class FinancialInstitutionApplication(models.Model):
    """
    Solicitudes de membresía en instituciones financieras
    """
    
    class ApplicationStatus(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        UNDER_REVIEW = 'under_review', 'En Revisión'
        ADDITIONAL_INFO_REQUIRED = 'additional_info', 'Información Adicional Requerida'
        PENDING_USER_SIGNATURE = 'pending_user_signature', 'Pendiente de Firma del Usuario'
        UNDER_REVIEW_FINAL = 'under_review_final', 'En Revisión Final'
        APPROVED = 'approved', 'Aprobada'
        REJECTED = 'rejected', 'Rechazada'
    
    class RejectionCategory(models.TextChoices):
        DOCUMENTATION = 'documentation', 'Documentación Incompleta'
        FINANCIAL_PROFILE = 'financial_profile', 'Perfil Financiero No Cumple'
        COMPLIANCE = 'compliance', 'Incumplimiento Normativo'
        FRAUD = 'fraud', 'Sospecha de Fraude'
        CAPACITY = 'capacity', 'Capacidad de Inversión Insuficiente'
        OTHER = 'other', 'Otros'
    
    class InvestorProfile(models.TextChoices):
        CONSERVATIVE = 'conservative', 'Conservador'
        MODERATE = 'moderate', 'Moderado'
        AGGRESSIVE = 'aggressive', 'Agresivo'
        SOPHISTICATED = 'sophisticated', 'Sofisticado'
        INSTITUTIONAL = 'institutional', 'Institucional'
    
    # ========================================
    # CAMPOS BÁSICOS
    # ========================================
    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='fi_applications',
        verbose_name="Usuario Aplicante"
    )
    financial_institution = models.ForeignKey(
        'FinancialInstitution',
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="Institución Financiera"
    )
    
    # ========================================
    # INFORMACIÓN DE LA SOLICITUD
    # ========================================
    requested_investor_profile = models.CharField(
        max_length=20,
        choices=InvestorProfile.choices,
        verbose_name="Perfil de Inversor Solicitado"
    )
    requested_investment_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto de Inversión Solicitado"
    )
    application_notes = models.TextField(
        blank=True,
        verbose_name="Notas de la Solicitud"
    )
    kyc_documents = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Documentos KYC"
    )
    
    # ========================================
    # ESTADO Y SEGUIMIENTO
    # ========================================
    status = models.CharField(
        max_length=30,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        verbose_name="Estado"
    )
    
    # ========================================
    # INFORMACIÓN DE REVISIÓN
    # ========================================
    reviewed_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_fi_applications',
        verbose_name="Revisado Por"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Revisión"
    )
    review_notes = models.TextField(
        blank=True,
        verbose_name="Notas de Revisión"
    )
    
    # ========================================
    # DECLARACIONES Y CONFIRMACIONES
    # ========================================
    accepts_terms_and_conditions = models.BooleanField(
        default=False,
        verbose_name="Acepta términos y condiciones"
    )
    accepts_risk_disclosure = models.BooleanField(
        default=False,
        verbose_name="Acepta declaración de riesgos"
    )
    confirms_information_accuracy = models.BooleanField(
        default=False,
        verbose_name="Confirma veracidad de la información"
    )
    authorizes_background_check = models.BooleanField(
        default=False,
        verbose_name="Autoriza verificación de antecedentes"
    )
    
    # ========================================
    # INFORMACIÓN DE RECHAZO
    # ========================================
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Razón de Rechazo"
    )
    rejection_category = models.CharField(
        max_length=20,
        choices=RejectionCategory.choices,
        null=True,
        blank=True,
        verbose_name="Categoría de Rechazo"
    )
    can_reapply_after = models.DateField(
        null=True,
        blank=True,
        verbose_name="Puede Volver a Aplicar Después De"
    )
    
    # ========================================
    # TIMESTAMPS
    # ========================================
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Solicitud de Membresía FI"
        verbose_name_plural = "Solicitudes de Membresía FI"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'financial_institution', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['reviewed_by', 'reviewed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.financial_institution.name} ({self.status})"


class FinancialInstitutionApproval(models.Model):
    """
    Aprobaciones de membresía en instituciones financieras
    """
    
    class ApprovalStatus(models.TextChoices):
        PRE_APPROVED = 'pre_approved', 'Pre-Aprobada'
        PRE_APPROVED_WITH_CHANGES = 'pre_approved_with_changes', 'Pre-Aprobada con Cambios'
        CONTRACT_SENT = 'contract_sent', 'Contrato Enviado'
        CONTRACT_SIGNED = 'contract_signed', 'Contrato Firmado'
        ACTIVE = 'active', 'Activa'  
        SUSPENDED = 'suspended', 'Suspendida'
        EXPIRED = 'expired', 'Expirada'
        REVOKED = 'revoked', 'Revocada'
    
    # ========================================
    # RELACIÓN CON LA SOLICITUD
    # ========================================
    application = models.OneToOneField(
        'FinancialInstitutionApplication',
        on_delete=models.CASCADE,
        related_name='approval',
        verbose_name="Solicitud"
    )
    
    # ========================================
    # INFORMACIÓN DE APROBACIÓN
    # ========================================
    approved_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='fi_approvals_made',
        verbose_name="Aprobado Por"
    )
    status = models.CharField(
        max_length=30,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PRE_APPROVED,
        verbose_name="Estado de Aprobación"
    )
    
    # ========================================
    # PERFIL Y LÍMITES APROBADOS
    # ========================================
    investor_profile = models.CharField(
        max_length=20,
        choices=FinancialInstitutionApplication.InvestorProfile.choices,
        verbose_name="Perfil de Inversor Aprobado"
    )
    max_investment_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto Máximo de Inversión"
    )
    allowed_fund_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Tipos de Fondos Permitidos"
    )
    
    # ========================================
    # FECHAS DEL PROCESO
    # ========================================
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación Final"
    )
    
    # ========================================
    # PROCESO DE CONTRATO (NUEVO)
    # ========================================
    contract_url = models.URLField(
        blank=True,
        verbose_name="URL del Contrato"
    )
    contract_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Contrato Generado En"
    )
    contract_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Contrato Enviado En"
    )
    contract_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Contrato Firmado En"
    )
    contract_notes = models.TextField(
        blank=True,
        verbose_name="Notas del Contrato"
    )
    signature_method = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Método de Firma"
    )
    user_signature_notes = models.TextField(
        blank=True,
        verbose_name="Notas de Firma del Usuario"
    )
    
    # ========================================
    # TÉRMINOS Y CONDICIONES
    # ========================================
    approval_notes = models.TextField(
        blank=True,
        verbose_name="Notas de Aprobación"
    )
    conditions = models.TextField(
        blank=True,
        verbose_name="Condiciones Especiales"
    )
    terms_modified = models.BooleanField(
        default=False,
        verbose_name="Términos Modificados"
    )
    changes_summary = models.TextField(
        blank=True,
        verbose_name="Resumen de Cambios"
    )
    
    # ========================================
    # VIGENCIA Y CONTROL
    # ========================================
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Expiración"
    )
    suspension_reason = models.TextField(
        blank=True,
        verbose_name="Razón de Suspensión"
    )
    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Suspendido En"
    )
    suspended_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fi_suspensions_made',
        verbose_name="Suspendido Por"
    )
    
    # ========================================
    # TIMESTAMPS
    # ========================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ========================================
    # PROPERTIES ÚTILES
    # ========================================
    @property
    def user(self):
        """Acceso directo al usuario a través de la aplicación"""
        return self.application.user if self.application else None
    
    @property
    def is_active(self):
        """Verificar si la membresía está activa"""
        if self.status != self.ApprovalStatus.ACTIVE:
            return False
        
        if self.expiry_date and timezone.now().date() > self.expiry_date:
            return False
        
        return True
    
    @property
    def days_until_expiry(self):
        """Días hasta la expiración"""
        if not self.expiry_date:
            return None
        
        delta = self.expiry_date - timezone.now().date()
        return delta.days if delta.days > 0 else 0
    
    def can_invest_in_fund_type(self, fund_type: str) -> bool:
        """Verificar si puede invertir en un tipo de fondo específico"""
        if not self.is_active:
            return False
        
        if not self.allowed_fund_types:
            return True  # Sin restricciones
        
        return fund_type in self.allowed_fund_types
    
    def can_invest_amount(self, amount: float) -> bool:
        """Verificar si puede invertir un monto específico"""
        if not self.is_active:
            return False
        
        if not self.max_investment_amount:
            return True  # Sin límite
        
        return amount <= float(self.max_investment_amount)
    
    class Meta:
        verbose_name = "Aprobación de Membresía FI"
        verbose_name_plural = "Aprobaciones de Membresía FI"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'expiry_date']),
            models.Index(fields=['approved_by', 'approval_date']),
            models.Index(fields=['investor_profile', 'status']),
        ]
    
    def __str__(self):
        user_name = self.user.email if self.user else "Usuario Desconocido"
        fi_name = self.application.financial_institution.name if self.application else "FI Desconocida"
        return f"{user_name} - {fi_name} ({self.status})"