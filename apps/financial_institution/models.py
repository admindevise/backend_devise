from django.db import models
from cities_light.models import Country, Region, City

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
    Solicitudes de usuarios para ser aprobados por instituciones financieras
    """
    
    class ApplicationStatus(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        UNDER_REVIEW = 'under_review', 'En Revisión'
        ADDITIONAL_INFO_REQUIRED = 'additional_info', 'Información Adicional Requerida'
        APPROVED = 'approved', 'Aprobado'
        REJECTED = 'rejected', 'Rechazado'
        WITHDRAWN = 'withdrawn', 'Retirada'
        EXPIRED = 'expired', 'Expirada'
    
    class InvestorProfile(models.TextChoices):
        RETAIL = 'retail', 'Minorista'
        PROFESSIONAL = 'professional', 'Profesional'
        HIGH_NET_WORTH = 'high_net_worth', 'Alto Patrimonio'
    
    class RejectionCategory(models.TextChoices):
        DOCUMENTATION = 'documentation', 'Documentación Incompleta'
        INFORMATION = 'information', 'Información Incorrecta'
        COMPLIANCE = 'compliance', 'Problemas de Cumplimiento'
        FRAUD = 'fraud', 'Sospecha de Fraude'
        POLICY = 'policy', 'No Cumple Políticas Internas'
    
    # ===========================================
    # RELACIONES PRINCIPALES
    # ===========================================
    user = models.ForeignKey(
        'user.User', 
        on_delete=models.CASCADE, 
        related_name='financial_institution_applications'
    )
    financial_institution = models.ForeignKey(
        FinancialInstitution, 
        on_delete=models.CASCADE, 
        related_name='user_applications'
    )
    
    # ===========================================
    # INFORMACIÓN DE LA SOLICITUD
    # ===========================================
    status = models.CharField(
        max_length=20, 
        choices=ApplicationStatus.choices, 
        default=ApplicationStatus.PENDING
    )
    
    requested_investor_profile = models.CharField(
        max_length=15,
        choices=InvestorProfile.choices,
        default=InvestorProfile.RETAIL
    )
    
    requested_investment_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Monto de inversión solicitado"
    )
    
    # ===========================================
    # DOCUMENTACIÓN Y PROCESO
    # ===========================================
    application_notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Notas de la aplicación"
    )
    
    kyc_documents = models.JSONField(
        default=dict, 
        verbose_name="Documentos KYC presentados"
    )
    
    # ===========================================
    # PROCESO DE REVISIÓN
    # ===========================================
    reviewed_by = models.ForeignKey(
        'user.User', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='reviewed_financial_applications'
    )
    review_notes = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # EN CASO DE RECHAZO
    rejection_category = models.CharField(
        max_length=20, 
        choices=RejectionCategory.choices, 
        blank=True, 
        null=True
    )
    rejection_reason = models.TextField(blank=True, null=True)
    can_reapply_after = models.DateField(blank=True, null=True)
    
    # ===========================================
    # METADATOS Y AUDITORÍA
    # ===========================================
    requested_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=60, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    source_application = models.CharField(max_length=50, default='devise_platform')
    
    class Meta:
        verbose_name = "Financial Institution Application"
        verbose_name_plural = "Solicitudes a Instituciones Financieras"
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'financial_institution']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"Solicitud: {self.user.email} → {self.financial_institution.short_name}"


class FinancialInstitutionApproval(models.Model):
    """
    Aprobaciones activas otorgadas por instituciones financieras
    Solo existe cuando la solicitud fue APROBADA
    """
    
    class ApprovalStatus(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        SUSPENDED = 'suspended', 'Suspendido'
        EXPIRED = 'expired', 'Expirado'
        REVOKED = 'revoked', 'Revocado'
    
    # ===========================================
    # RELACIÓN CON LA SOLICITUD
    # ===========================================
    application = models.OneToOneField(
        FinancialInstitutionApplication,
        on_delete=models.CASCADE,
        related_name='approval'
    )
    
    # ===========================================
    # INFORMACIÓN DE LA APROBACIÓN
    # ===========================================
    status = models.CharField(
        max_length=15, 
        choices=ApprovalStatus.choices, 
        default=ApprovalStatus.ACTIVE
    )
    
    investor_profile = models.CharField(
        max_length=15, 
        choices=FinancialInstitutionApplication.InvestorProfile.choices
    )
    
    
    # ===========================================
    # LÍMITES Y RESTRICCIONES OTORGADOS
    # ===========================================
    max_investment_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    allowed_fund_types = models.JSONField(default=list)
    restricted_fund_types = models.JSONField(default=list)
    
    # ===========================================
    # INFORMACIÓN DE APROBACIÓN
    # ===========================================
    approved_by = models.ForeignKey(
        'user.User', 
        on_delete=models.PROTECT,
        related_name='financial_institution_approvals_given'
    )
    
    approval_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    approval_notes = models.TextField(blank=True, null=True)
    conditions = models.TextField(blank=True, null=True)
    
    # ===========================================
    # VALIDACIONES REALIZADAS
    # ===========================================
    kyc_score = models.PositiveSmallIntegerField(null=True, blank=True)
    aml_check_passed = models.BooleanField(default=False)
    
    # ===========================================
    # AUDITORÍA DE LA APROBACIÓN
    # ===========================================
    last_review_date = models.DateTimeField(null=True, blank=True)
    last_activity_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Financial Institution Approval"
        verbose_name_plural = "Aprobaciones a Instituciones Financieras"
        ordering = ['-approval_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
        ]
    
    # ===========================================
    # PROPIEDADES Y MÉTODOS
    # ===========================================
    @property
    def user(self):
        """Acceso directo al usuario a través de la aplicación"""
        return self.application.user
    
    @property
    def financial_institution(self):
        """Acceso directo a la institución a través de la aplicación"""
        return self.application.financial_institution
    
    @property
    def is_active(self):
        """Verifica si la aprobación está activa"""
        from datetime import date
        
        if self.status != self.ApprovalStatus.ACTIVE:
            return False
        
        if self.expiry_date and self.expiry_date < date.today():
            return False
        
        return True
    
    def can_invest_in_fund(self, fund):
        """Verifica si puede invertir en un fondo específico"""
        if not self.is_active:
            return False
        
        if self.allowed_fund_types and fund.fund_type not in self.allowed_fund_types:
            return False
        
        if self.restricted_fund_types and fund.fund_type in self.restricted_fund_types:
            return False
        
        return True
    
    def can_invest_amount(self, amount):
        """Verifica si puede invertir un monto específico"""
        if not self.is_active:
            return False
        
        if self.max_investment_amount and amount > self.max_investment_amount:
            return False
        
        return True