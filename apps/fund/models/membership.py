from django.db import models
from django.utils import timezone

class FundApplication(models.Model):
    """
    Modelo para manejar las solicitudes de ingreso a fondos y el proceso de verificación.
    Responsabilidad: Gestionar el proceso de aplicación y verificación inicial.
    """
    
    class ApplicationStatus(models.TextChoices):
        """Enum para estados de la aplicación usando TextChoices (Django 3.0+)"""
        PENDING = 'pending', 'Solicitud Pendiente'
        UNDER_REVIEW = 'under_review', 'En Revisión'
        ADDITIONAL_INFO_REQUIRED = 'additional_info_required', 'Información Adicional Requerida'
        APPROVED = 'approved', 'Aprobada'
        REJECTED = 'rejected', 'Rechazada'
        WITHDRAWN = 'withdrawn', 'Retirada'
        EXPIRED = 'expired', 'Expirada'
        
    class RejectionCategory(models.TextChoices):
        """Categorías de rechazo para análisis estadístico."""
        INSUFFICIENT_FUNDS = 'insufficient_funds', 'Fondos Insuficientes'
        FAILED_KYC = 'failed_kyc', 'Fallo en KYC'
        FAILED_BACKGROUND_CHECK = 'failed_background_check', 'Fallo en Verificación de Antecedentes'
        HIGH_RISK_PROFILE = 'high_risk_profile', 'Perfil de Alto Riesgo'
        INCOMPLETE_APPLICATION = 'incomplete_application', 'Aplicación Incompleta'
        
    class InvestmentObjective(models.TextChoices):
        """Objetivos de inversión del solicitante."""
        CAPITAL_GROWTH = 'capital_growth', 'Crecimiento de Capital'
        INCOME_GENERATION = 'income_generation', 'Generación de Ingresos'
        CAPITAL_PRESERVATION = 'capital_preservation', 'Preservación de Capital'
        RETIREMENT = 'retirement', 'Jubilación'
        EDUCATION = 'education', 'Educación'
        OTHER = 'other', 'Otro'
    
    class SourceOfFunds(models.TextChoices):
        """Fuente de los fondos del solicitante."""
        SALARY = 'salary', 'Salario'
        BUSINESS_INCOME = 'business_income', 'Ingresos de Negocio'
        INVESTMENTS = 'investments', 'Inversiones'
        INHERITANCE = 'inheritance', 'Herencia'
        LOAN = 'loan', 'Préstamo'
        SAVINGS = 'savings', 'Ahorros'
        OTHER = 'other', 'Otro'
    
    class ReferralSource(models.TextChoices):
        """Cómo se enteró el solicitante del fondo."""
        WEBSITE = 'website', 'Sitio Web'
        SOCIAL_MEDIA = 'social_media', 'Redes Sociales'
        REFERRAL = 'referral', 'Referido'
        ADVISOR = 'advisor', 'Asesor Financiero'
        ADVERTISEMENT = 'advertisement', 'Publicidad'
        EVENT = 'event', 'Evento'
        OTHER = 'other', 'Otro'
    
    class PreferredPaymentMethod(models.TextChoices):
        """Método de pago preferido del solicitante."""
        BANK_TRANSFER = 'bank_transfer', 'Transferencia Bancaria'
        CREDIT_CARD = 'credit_card', 'Tarjeta de Crédito'
        DEBIT_CARD = 'debit_card', 'Tarjeta Débito'
        CHECK = 'check', 'Cheque'
        CRYPTO = 'crypto', 'Criptomonedas'
        OTHER = 'other', 'Otro'
    
    class InvestmentExperience(models.TextChoices):
        """Nivel de experiencia en inversión del solicitante."""
        BEGINNER = 'beginner', 'Principiante'
        INTERMEDIATE = 'intermediate', 'Intermedio'
        ADVANCED = 'advanced', 'Avanzado'
        PROFESSIONAL = 'professional', 'Profesional'
    
    # ========================================
    # RELACIONES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund', 
        on_delete=models.CASCADE, 
        related_name="applications",
        verbose_name="Fondo"
    )
    applicant = models.ForeignKey(
        'user.User', 
        on_delete=models.CASCADE, 
        related_name="fund_applications",
        verbose_name="Solicitante"
    )
    
    # ========================================
    # INFORMACIÓN FINANCIERA DE LA SOLICITUD
    # ========================================
    requested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Monto solicitado",
        help_text="Monto que el solicitante desea invertir"
    )
    
    requested_units = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Unidades solicitadas",
        help_text="Número específico de unidades que desea adquirir"
    )
    
    maximum_acceptable_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio máximo aceptable por unidad",
        help_text="Precio máximo que está dispuesto a pagar por unidad"
    )
    
    preferred_payment_method = models.CharField(
        max_length=30,
        choices=PreferredPaymentMethod.choices,
        null=True,
        blank=True
    )
    
    # ========================================
    # PERFIL DE INVERSIÓN
    # ========================================
    investment_objective = models.CharField(
        max_length=60,
        choices=InvestmentObjective.choices,
        null=True,
        blank=True,
    )
    
    risk_tolerance = models.CharField(
        max_length=15,
        choices=[
            ('low', 'Bajo'),
            ('medium', 'Medio'),
            ('high', 'Alto'),
        ],
        null=True,
        blank=True,
        verbose_name="Tolerancia al riesgo"
    )
    
    investment_experience = models.CharField(
        max_length=20,
        choices=InvestmentExperience.choices,
        null=True,
        blank=True
    )
    planned_investment_horizon = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Horizonte de inversión planeado (años)",
        help_text="Tiempo que planea mantener la inversión"
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
    # INFORMACIÓN ADICIONAL
    # ========================================
    source_of_funds = models.CharField(
        max_length=30,
        choices=SourceOfFunds.choices,
        null=True,
        blank=True
    )
    is_politically_exposed = models.BooleanField(default=False)
    referral_source = models.CharField(
        max_length=30,
        choices=ReferralSource.choices,
        null=True,
        blank=True
    )
    special_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name="Instrucciones especiales",
        help_text="Cualquier instrucción o requerimiento especial"
    )
    
    # ========================================
    # FECHAS Y ESTADO
    # ========================================
    status = models.CharField(
        max_length=50,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        verbose_name="Estado"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de revisión"
    )
    
    # ========================================
    # PROCESO DE REVISIÓN
    # ========================================
    reviewed_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_applications",
    )
    rejection_category = models.CharField(
        max_length=30,
        choices=RejectionCategory.choices,
        null=True,
        blank=True
    )
    rejection_reason = models.TextField(blank=True, null=True)
    can_reapply_after = models.DateField(blank=True, null=True)
        
    # ========================================
    # NOTAS Y OBSERVACIONES 
    # ========================================
    applicant_notes = models.TextField(blank=True, null=True)
    review_notes = models.TextField(blank=True, null=True)
    
    # ========================================
    # METADATOS
    # ========================================
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    application_version = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Versión de la aplicación",
        help_text="Versión del formulario usado"
    )
    
    @property
    def is_approved(self) -> bool:
        """Verifica si la aplicación está aprobada."""
        return self.status == self.ApplicationStatus.APPROVED
    
    @property
    def can_proceed_to_investment(self) -> bool:
        """Verifica si puede proceder al proceso de inversión."""
        return self.is_approved

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Solicitud de Fondo"
        verbose_name_plural = "Solicitudes de Fondos"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['fund', 'status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.applicant.email} → {self.fund.name} ({self.get_status_display()})"
    
    
class FundApproval(models.Model):
    """
    Modelo para registrar aprobaciones formales de ingreso a fondos.
    Responsabilidad: Documentar la aprobación final y los términos acordados.
    """
    
    class ApprovalStatus(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        SUSPENDED = 'suspended', 'Suspendido'
        EXPIRED = 'expired', 'Expirado'
        REVOKED = 'revoked', 'Revocado'
        
        PRE_APPROVED = 'pre_approved', 'Pre-aprobado'
        PRE_APPROVED_WITH_CHANGES = 'pre_approved_with_changes', 'Pre-aprobado con cambios'
        AWAITING_CONTRACT_SIGNATURE = 'awaiting_contract_signature', 'En espera de firma de contrato'
        CONTRACT_SIGNED = 'contract_signed', 'Contrato firmado'
    
    # ========================================
    # RELACIONES
    # ========================================
    application = models.OneToOneField(
        FundApplication, 
        on_delete=models.CASCADE, 
        related_name="approval",
        verbose_name="Solicitud Asociada"
    )
    approved_by = models.ForeignKey(
        'user.User', 
        on_delete=models.PROTECT, 
        related_name="fund_approvals",
        verbose_name="Aprobado por"
    )
    
    # ========================================
    # DETALLES DE LA APROBACIÓN
    # ========================================
    status = models.CharField(
        max_length=40,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PRE_APPROVED,
        verbose_name="Estado de la aprobación"
    )
    approved_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Monto aprobado",
        help_text="Monto que ha sido aprobado para inversión"
    )
    
    approved_units = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Unidades aprobadas",
        help_text="Número de unidades aprobadas para adquisición"
    )
    
    unit_price_at_approval = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio por unidad al momento de la aprobación",
        help_text="Precio unitario vigente al momento de la aprobación"
    )
    
    approval_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    
    terms_and_conditions_version = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Versión de términos y condiciones",
        help_text="Versión de los términos aceptados"
    )
    
    risk_disclosure_version = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Versión de declaración de riesgos",
        help_text="Versión de la declaración de riesgos aceptada"
    )
    
    # ========================================
    # GESTIÓN DE CONTRATOS Y TÉRMINOS
    # ========================================

    # Términos iniciales (de la aplicación)
    initial_terms_accepted_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha de aceptación de términos iniciales"
    )

    initial_terms_version = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Versión de términos iniciales aceptados"
    )

    # Proceso de pre-aprobación
    pre_approval_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha de pre-aprobación"
    )

    # Detección de cambios en términos
    terms_modified = models.BooleanField(
        default=False,
        verbose_name="Términos fueron modificados durante revisión"
    )

    changes_summary = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Resumen de cambios realizados",
        help_text="Descripción de los cambios entre lo solicitado y lo aprobado"
    )

    # Gestión del contrato final
    final_contract_generated_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha de generación del contrato final"
    )

    final_contract_sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha de envío del contrato final al usuario"
    )

    final_contract_signed_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha de firma del contrato final"
    )

    contract_signature_deadline = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha límite para firmar el contrato"
    )

    # Identificadores de documentos
    contract_document_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="ID del documento de contrato",
        help_text="Referencia al documento en el sistema de gestión documental"
    )

    digital_signature_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="ID de la firma digital",
        help_text="Referencia de la firma digital en el sistema"
    )
    
    # ========================================
    # NOTAS Y OBSERVACIONES
    # ========================================
    approval_notes = models.TextField(blank=True, null=True)
    conditions = models.TextField(blank=True, null=True)
    
    # ========================================
    # METADATOS
    # ========================================
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-approval_date']
        verbose_name = "Aprobación de Fondo"
        verbose_name
        

class FundInvestment(models.Model):
    """
    Modelo para manejar las inversiones activas en fondos.
    Responsabilidad: Gestionar el proceso de compra de tokens e inversión final.
    """
    
    class InvestmentStatus(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', 'Pago Pendiente'
        PAYMENT_VERIFIED = 'payment_verified', 'Pago Verificado'
        ACTIVE = 'active', 'Activa'
        SUSPENDED = 'suspended', 'Suspendida'
        MATURE = 'mature', 'Vencida'
        PARTIAL_REDEMPTION = 'partial_redemption', 'Redención Parcial'
        FULL_REDEMPTION = 'full_redemption', 'Redención Total'
        CANCELLED = 'cancelled', 'Cancelada'
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PARTIAL = 'partial', 'Parcial'
        COMPLETED = 'completed', 'Completado'
        FAILED = 'failed', 'Fallido'
        REFUNDED = 'refunded', 'Reembolsado'
    
    # ========================================
    # RELACIONES
    # ========================================
    application = models.OneToOneField(
        FundApplication,
        on_delete=models.CASCADE,
        related_name="investment",
        verbose_name="Solicitud asociada",
        null=True,
        blank=True
    )
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name="investments",
        verbose_name="Fondo"
    )
    investor = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name="fund_investments",
        verbose_name="Inversor"
    )
    
    # ========================================
    # INFORMACIÓN FINANCIERA PRINCIPAL
    # ========================================
    invested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Monto invertido",
        help_text="Monto realmente invertido confirmado"
    )
    
    units_owned = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        verbose_name="Unidades poseídas",
        help_text="Número de unidades del fondo que posee"
    )
    
    purchase_price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Precio de compra por unidad",
        help_text="Precio al cual compró las unidades"
    )
    
    current_unit_value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Valor actual por unidad",
        help_text="Precio actual de mercado por unidad"
    )
    
    # ========================================
    # RENDIMIENTOS Y GANANCIAS
    # ========================================
    total_dividends_received = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Total dividendos recibidos",
        help_text="Suma total de dividendos recibidos históricamente"
    )
    
    pending_dividends = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Dividendos pendientes",
        help_text="Dividendos declarados pero no pagados"
    )
    
    realized_capital_gains = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Ganancias de capital realizadas",
        help_text="Ganancias por ventas parciales ya realizadas"
    )
    
    unrealized_capital_gains = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Ganancias de capital no realizadas",
        help_text="Ganancias en papel basadas en precio actual"
    )
    
    accrued_interest = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Intereses acumulados",
        help_text="Intereses devengados pero no pagados"
    )
    
    performance_fees_paid = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Comisiones de performance pagadas",
        help_text="Total de comisiones por desempeño pagadas"
    )
    
    management_fees_paid = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Comisiones de administración pagadas",
        help_text="Total de comisiones de administración pagadas"
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
            ('debit_card', 'Tarjeta Débito'),
            ('check', 'Cheque'),
            ('wire_transfer', 'Transferencia Internacional'),
            ('crypto', 'Criptomonedas'),
            ('ach', 'ACH'),
            ('cash', 'Efectivo'),
            ('other', 'Otro'),
        ],
        null=True,
        blank=True,
        verbose_name="Método de pago utilizado"
    )
    
    payment_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Referencia de pago",
        help_text="Número de transacción, cheque, etc."
    )
    
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de pago confirmado"
    )
    
    # ========================================
    # FECHAS IMPORTANTES
    # ========================================
    status = models.CharField(
        max_length=25,
        choices=InvestmentStatus.choices,
        default=InvestmentStatus.PENDING_PAYMENT,
        verbose_name="Estado"
    )
    
    investment_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de inicio de inversión",
        help_text="Fecha cuando la inversión se activa oficialmente"
    )
    
    maturity_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento",
        help_text="Fecha de vencimiento del período de permanencia"
    )
    
    last_valuation_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última fecha de valoración",
        help_text="Última vez que se calculó el valor de la inversión"
    )
    
    last_dividend_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Última fecha de dividendo",
        help_text="Última vez que recibió dividendos"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Última actualización"
    )
    
    # ========================================
    # CONFIGURACIONES DE INVERSIÓN
    # ========================================
    auto_reinvest_dividends = models.BooleanField(
        default=True,
        verbose_name="Reinversión automática de dividendos",
        help_text="Si los dividendos se reinvierten automáticamente"
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
    
    tax_withholding_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Porcentaje de retención fiscal (%)",
        help_text="Porcentaje de impuestos retenidos automáticamente"
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
    # INFORMACIÓN BANCARIA PARA PAGOS
    # ========================================
    bank_account_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Número de cuenta bancaria",
        help_text="Para pagos de dividendos y redenciones"
    )
    
    bank_routing_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Código de enrutamiento bancario"
    )
    
    bank_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Nombre del banco"
    )
    
    # ========================================
    # DOCUMENTACIÓN
    # ========================================
    investment_agreement = models.FileField(
        upload_to='investments/agreements/',
        null=True,
        blank=True,
        verbose_name="Contrato de inversión firmado"
    )
    
    payment_receipt = models.FileField(
        upload_to='investments/receipts/',
        null=True,
        blank=True,
        verbose_name="Comprobante de pago"
    )
    
    tax_documents = models.FileField(
        upload_to='investments/tax/',
        null=True,
        blank=True,
        verbose_name="Documentos fiscales"
    )
    
    # ========================================
    # NOTAS Y OBSERVACIONES
    # ========================================
    investment_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas de la inversión",
        help_text="Observaciones específicas de esta inversión"
    )
    
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de cancelación"
    )
    
    suspension_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de suspensión"
    )
    
    # ========================================
    # METADATOS DE AUDITORÍA
    # ========================================
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_investments",
        verbose_name="Creado por"
    )
    
    last_modified_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="modified_investments",
        verbose_name="Última modificación por"
    )
    
    audit_trail = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Historial de cambios",
        help_text="Log de cambios importantes en la inversión"
    )
    
    # ========================================
    # PROPIEDADES CALCULADAS
    # ========================================
    @property
    def current_investment_value(self):
        """Valor actual total de la inversión"""
        if self.units_owned and self.current_unit_value:
            return self.units_owned * self.current_unit_value
        return self.invested_amount
    
    @property
    def total_return_amount(self):
        """Rendimiento total en pesos (realizado + no realizado + dividendos)"""
        return (
            self.realized_capital_gains + 
            self.unrealized_capital_gains + 
            self.total_dividends_received
        )
    
    @property
    def total_return_percentage(self):
        """Porcentaje total de rendimiento"""
        if self.invested_amount > 0:
            return float((self.total_return_amount / self.invested_amount) * 100)
        return 0.0
    
    @property
    def annualized_return(self):
        """Rendimiento anualizado desde la inversión inicial"""
        if not self.investment_start_date or self.invested_amount <= 0:
            return 0.0
        
        from datetime import date
        from decimal import Decimal
        
        days_invested = (date.today() - self.investment_start_date).days
        if days_invested <= 0:
            return 0.0
        
        total_return_ratio = float(self.total_return_amount / self.invested_amount)
        years_invested = days_invested / 365.25
        
        if years_invested <= 0:
            return 0.0
        
        # Fórmula: (1 + total_return)^(1/años) - 1
        annualized = ((1 + total_return_ratio) ** (1 / years_invested)) - 1
        return annualized * 100
    
    @property
    def dividend_yield(self):
        """Rendimiento por dividendos sobre la inversión inicial"""
        if self.invested_amount > 0:
            return float((self.total_dividends_received / self.invested_amount) * 100)
        return 0.0
    
    @property
    def unrealized_gain_loss(self):
        """Ganancia/pérdida no realizada actual"""
        current_value = self.current_investment_value
        return current_value - self.invested_amount
    
    @property
    def can_redeem(self):
        """Verifica si puede solicitar redención"""
        if not self.maturity_date:
            return True
        
        from datetime import date
        return date.today() >= self.maturity_date
    
    @property
    def is_active(self):
        """Verifica si la inversión está activa"""
        return self.status == self.InvestmentStatus.ACTIVE
    
    @property
    def days_until_maturity(self):
        """Días hasta el vencimiento"""
        if not self.maturity_date:
            return None
        
        from datetime import date
        delta = self.maturity_date - date.today()
        return max(0, delta.days)
    
    # ========================================
    # MÉTODOS DE NEGOCIO
    # ========================================
    def calculate_current_value(self):
        """Recalcula el valor actual basado en el precio del fondo"""
        if self.units_owned and self.fund.price_per_unit:
            self.current_unit_value = self.fund.price_per_unit
            self.unrealized_capital_gains = (
                (self.current_unit_value - self.purchase_price_per_unit) * 
                self.units_owned
            )
            self.last_valuation_date = timezone.now()
            self.save(update_fields=[
                'current_unit_value', 
                'unrealized_capital_gains', 
                'last_valuation_date'
            ])
    
    def record_dividend_payment(self, amount, payment_date=None):
        """Registra un pago de dividendos"""
        from decimal import Decimal
        
        self.total_dividends_received += Decimal(str(amount))
        self.last_dividend_date = payment_date or timezone.now().date()
        
        # Registrar en audit trail
        self.audit_trail.append({
            'action': 'dividend_payment',
            'amount': str(amount),
            'date': str(self.last_dividend_date),
            'timestamp': timezone.now().isoformat()
        })
        
        self.save(update_fields=[
            'total_dividends_received', 
            'last_dividend_date', 
            'audit_trail'
        ])
    
    def record_fee_payment(self, fee_type, amount):
        """Registra el pago de comisiones"""
        from decimal import Decimal
        
        amount_decimal = Decimal(str(amount))
        
        if fee_type == 'management':
            self.management_fees_paid += amount_decimal
        elif fee_type == 'performance':
            self.performance_fees_paid += amount_decimal
        
        # Registrar en audit trail
        self.audit_trail.append({
            'action': f'{fee_type}_fee_payment',
            'amount': str(amount),
            'timestamp': timezone.now().isoformat()
        })
        
        self.save()
    
    def calculate_maturity_date(self):
        """Calcula la fecha de vencimiento basada en el período de permanencia"""
        if self.investment_start_date and self.fund.permanence_period:
            from datetime import timedelta
            self.maturity_date = (
                self.investment_start_date + 
                timedelta(days=self.fund.permanence_period)
            )
            self.save(update_fields=['maturity_date'])
    
    # ========================================
    # VALIDACIONES
    # ========================================
    def clean(self):
        """Validaciones personalizadas"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # Validar que el monto invertido sea positivo
        if self.invested_amount <= 0:
            errors['invested_amount'] = 'El monto invertido debe ser mayor a cero'
        
        # Validar consistencia entre unidades y monto
        if (self.units_owned and self.purchase_price_per_unit and 
            self.invested_amount):
            calculated_amount = self.units_owned * self.purchase_price_per_unit
            if abs(calculated_amount - self.invested_amount) > 1:
                errors['units_owned'] = 'Las unidades no coinciden con el monto invertido'
        
        # Validar fechas
        if (self.investment_start_date and self.maturity_date and 
            self.investment_start_date >= self.maturity_date):
            errors['maturity_date'] = 'La fecha de vencimiento debe ser posterior al inicio'
        
        if errors:
            raise ValidationError(errors)
    
    # ========================================
    # META CONFIGURACIÓN
    # ========================================
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Inversión en Fondo"
        verbose_name_plural = "Inversiones en Fondos"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['fund', 'investor']),
            models.Index(fields=['investor', 'status']),
            models.Index(fields=['investment_start_date']),
            models.Index(fields=['maturity_date']),
            models.Index(fields=['payment_status']),
        ]
        unique_together = [('fund', 'investor', 'created_at')]
    
    def __str__(self):
        return f"{self.investor.email} → {self.fund.name} (${self.invested_amount})"
    