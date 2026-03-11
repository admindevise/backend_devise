import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from apps.utils.models import base_model
from apps.utils.models.file_helpers import (
    fund_image_path,
    fund_image_admin_path,
    fund_terms_and_conditions_path,
    fund_data_processing_policy_path,
    fund_fiduciary_draft_path,
    fund_mercantile_trust_agreement_path,
    fund_other_documents_path,
    fund_assignment_contract_path,
    fund_operating_contract_path,
    fund_semestral_document_path,
    othersi_document_path,
    trust_agreement_signed_document_path,
    trust_agreement_electronic_envelope_path,
)

from apps.user.models import User
from apps.kaleido.models import Wallet, InstanceOfTokenContract721

# ============================================================================
# FIDEICOMISOS
# ============================================================================

class FundCategory(models.Model):
    """
    Modelo para categorizar fondos de inversión
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre de la categoría"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción de la categoría"
    )
    
    class Meta:
        verbose_name = "Categoría de Fondo"
        verbose_name_plural = "Categorías de Fondos"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Fund(models.Model):
    """
    Modelo principal para gestionar fondos de inversión
    """
    
    # ========================================
    # RELACIONES EXTERNAS
    # ========================================
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='fund_core',
        verbose_name="Usuario propietario"
    )
    
    category = models.ForeignKey(
        FundCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Categoría del fondo"
    )
    
    financial_institution = models.ForeignKey(
        'financial_institution.FinancialInstitution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Institución financiera"
    )

    hd_wallet = models.OneToOneField(
        Wallet, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Wallet HD"
    )
    token_contract_721 = models.OneToOneField(
        InstanceOfTokenContract721, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Contrato de Token 721"
    )
    
    # ========================================
    # INFORMACIÓN BÁSICA
    # ========================================
    name = models.CharField(
        max_length=100,
        verbose_name="Nombre del fondo"
    )
    description = models.TextField(
        verbose_name="Descripción"
    )
    description_admin = models.TextField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="Descripción administrativa"
    )
    evolution_description = models.TextField(
        max_length=500,
        blank=True, 
        null=True,
        verbose_name="Evolución del fondo"
    )
    
    # Imágenes
    image = models.ImageField(
        upload_to=fund_image_path, 
        null=True, 
        blank=True,
        verbose_name="Imagen principal"
    )
    image_admin = models.ImageField(
        upload_to=fund_image_admin_path, 
        null=True, 
        blank=True,
        verbose_name="Imagen administrativa"
    )
    
    # Estado y fechas
    STATUS_CHOICES = (
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
    )
    status = models.CharField(
        choices=STATUS_CHOICES, 
        max_length=10, 
        default='active',
        verbose_name="Estado"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    
    # ========================================
    # CONFIGURACIÓN DE TOKENS Y UNIDADES
    # ========================================
    amount_units = models.PositiveIntegerField(
        default=0, 
        help_text="Cantidad de unidades del fondo",
        verbose_name="Cantidad de unidades"
    )
    amount_tokens = models.PositiveIntegerField(
        default=0, 
        help_text="Cantidad de tokens del fondo",
        verbose_name="Cantidad de tokens"
    )
    last_token_seq = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Última secuencia numérica utilizada para generar token IDs",
        verbose_name="Última secuencia de token"
    )
    nickname_tokens = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Nombre de los tokens"
    )
    secret = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        verbose_name="Clave secreta"
    )
    
    # ========================================
    # PARÁMETROS FINANCIEROS - PRECIOS
    # ========================================
    price_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Precio por unidad actual"
    )
    initial_price_per_unit = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Valor inicial por unidad"
    )
    
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Comisión por unidad",
    )
    
    # ========================================
    # PARÁMETROS FINANCIEROS - ACTIVOS Y COMISIONES
    # ========================================
    initial_capex = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Valor de compra o inversion",
        help_text="Valor total de compra/inversion total del fondo"
    )        
    total_assets = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Activos totales"
    )
    management_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Porcentaje de comisión de administración",
        verbose_name="Comisión de administración (%)"
    )
    success_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Porcentaje de comisión por desempeño",
        verbose_name="Comisión de éxito (%)"
    )
    
    # ========================================
    # ÁREAS Y DIMENSIONES (PARA NOI, CASH ON CASH)
    # ========================================    
    total_area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Área total (m²)",
        help_text="Suma del área total de todos los activos del fondo"
    )        
    rentable_area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Área arrendable (m²)",
        help_text="Suma del área arrendable de todos los activos del fondo"
    )  
    
    # ========================================
    # INFORMACIÓN REGULATORIA
    # ========================================
    superintendency_registry = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Número de registro en Superintendencia Financiera",
        verbose_name="Registro superintendencia"
    )
    tax_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        help_text="Número de identificación tributaria",
        verbose_name="NIT"
    )
    risk_rating = models.CharField(
        max_length=10, 
        blank=True, 
        null=True, 
        help_text="Ej.: AAA, AA+, BBB, etc.",
        verbose_name="Calificación de riesgo"
    )
    
    # ========================================
    # CLASIFICACIÓN DEL FONDO
    # ========================================
    FUND_TYPE_CHOICES = (
        ('real_estate', 'Fondo Inmobiliario'),
        ('securities', 'Fondo de Valores'),
        ('private_equity', 'Capital Privado'),
        ('pension', 'Pensión Voluntaria'),
        ('other', 'Otro'),
    )
    fund_type = models.CharField(
        choices=FUND_TYPE_CHOICES, 
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Tipo de fondo"
    )
    management_company = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Compañía administradora"
    )
    
    # ========================================
    # POLÍTICAS DE INVERSIÓN
    # ========================================
    RISK_PROFILE_CHOICES = (
        ('conservative', 'Conservador'),
        ('moderate', 'Moderado'),
        ('aggressive', 'Agresivo'),
    )
    risk_profile = models.CharField(
        choices=RISK_PROFILE_CHOICES, 
        max_length=15, 
        blank=True, 
        null=True,
        verbose_name="Perfil de riesgo"
    )
    investment_horizon = models.PositiveSmallIntegerField(
        blank=True, 
        null=True, 
        help_text="Tiempo recomendado en años",
        verbose_name="Horizonte de inversión (años)"
    )
    suggested_trend = models.PositiveSmallIntegerField(
        blank=True, 
        null=True, 
        help_text="Tiempo sugerido para mantener la inversión en años",
        verbose_name="Tendencia sugerida (años)"
    )
    asset_composition = models.JSONField(
        blank=True, 
        null=True, 
        help_text="Distribución porcentual por tipo de activo",
        verbose_name="Composición de activos"
    )
    
    # ========================================
    # POLÍTICAS DE DIVIDENDOS
    # ========================================
    DIVIDEND_DISTRIBUTION_CHOICES = (
        ('automatic_reinvestment', 'Reinversión Automática'),
        ('periodic_distribution', 'Distribución Periódica'),
        ('mixed', 'Mixto'),
    )
    dividend_distribution = models.CharField(
        choices=DIVIDEND_DISTRIBUTION_CHOICES, 
        max_length=25, 
        blank=True, 
        null=True,
        verbose_name="Distribución de dividendos"
    )
    
    PERFORMANCE_PAYMENT_FREQUENCY_CHOICES = (
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('semi_annually', 'Semestral'),
        ('annually', 'Anual'),
    )
    performance_payment_frequency = models.CharField(
        choices=PERFORMANCE_PAYMENT_FREQUENCY_CHOICES,
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Frecuencia de pago de rendimientos"
    )
    
    # ========================================
    # PARÁMETROS OPERACIONALES
    # ========================================
    minimum_investment = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Inversión mínima"
    )
    permanence_period = models.PositiveSmallIntegerField(
        blank=True, 
        null=True, 
        help_text="Tiempo mínimo en días",
        verbose_name="Período de permanencia (días)"
    )
    early_withdrawal_penalty = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Porcentaje de penalización por retiro anticipado",
        verbose_name="Penalización retiro anticipado (%)"
    )
    trading_hours = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Ej.: 8:00 a.m. - 1:00 p.m.",
        verbose_name="Horario de operaciones"
    )
    operations_start_date = models.DateField(
        blank=True, 
        null=True,
        verbose_name="Fecha de inicio de operaciones"
    )
    operations_closing_date = models.DateField(
        blank=True, 
        null=True,
        verbose_name="Fecha de cierre de operaciones"
    )
    
    # ========================================
    # GESTIÓN Y ADMINISTRACIÓN
    # ========================================
    main_manager = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Gerente principal"
    )
    description_main_manager = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Descripción del gerente principal"
    )
    trustor = models.TextField(
        max_length=40,
        blank=True, 
        null=True,
        verbose_name="Fideicomitente"
    )
    
    # ========================================
    # DOCUMENTOS Y POLÍTICAS
    # ========================================
    terms_and_conditions = models.FileField(
        upload_to=fund_terms_and_conditions_path, 
        blank=True, 
        null=True, 
        help_text="Documento de términos y condiciones",
        verbose_name="Términos y condiciones"
    )
    data_processing_policy = models.FileField(
        upload_to=fund_data_processing_policy_path, 
        blank=True, 
        null=True, 
        help_text="Documento de política de tratamiento de datos",
        verbose_name="Política de tratamiento de datos"
    )
    fiduciary_draft = models.FileField(
        upload_to=fund_fiduciary_draft_path,
        blank=True,
        null=True,
        help_text="Documento de Minuta Fiduciaria",
        verbose_name="Minuta Fiduciaria"
    )
    mercantile_trust_agreement = models.FileField(
        upload_to=fund_mercantile_trust_agreement_path,
        blank=True,
        null=True,
        help_text="Documento de contrato de fiducia mercantil",
        verbose_name="Contrato de fiducia mercantil"
    )
    
    assignment_contract = models.FileField(
        upload_to=fund_assignment_contract_path,
        blank=True,
        null=True,
        help_text="Contrato de cesión",
        verbose_name="Contrato de cesión"
    )
    operating_contract = models.FileField(
        upload_to=fund_operating_contract_path,
        blank=True,
        null=True,
        help_text="Contrato de operación",
        verbose_name="Contrato de operación"
    )
    
    # ========================================
    # META CONFIGURACIÓN
    # ========================================
    class Meta:
        verbose_name = "Fideicomiso"
        verbose_name_plural = "Fideicomisos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'fund_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['name']),
        ]
    
    # ========================================
    # MÉTODOS ESPECIALES
    # ========================================
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    # ========================================
    # PROPIEDADES
    # ========================================
    @property
    def wallet_id(self):
        """ID de la wallet asociada"""
        return self.hd_wallet.id_wallet if self.hd_wallet else None
    
    @property
    def contract_address(self):
        """Dirección del contrato de token"""
        return self.token_contract_721.contract_address if self.token_contract_721 else None
    
    @property
    def amount_total(self):
        """Monto total del fondo (cantidad × precio por unidad)"""
        return self.amount_units * self.price_per_unit if self.price_per_unit else 0


# ============================================================================
# DOCUMENTOS SEMESTRALES
# ============================================================================
class TypeSemestralDocument(models.Model):
    """
    Tipos de documentos semestrales asociados a un fondo
    """
    code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Código del tipo de documento"
    )
    name = models.CharField(
        max_length=100, 
        verbose_name="Nombre del tipo de documento"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Descripción del tipo de documento"
    )
    
    class Meta:
        verbose_name = "Tipo de Documento Semestral"
        verbose_name_plural = "Tipos de Documentos Semestrales"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class FundSemestralDocument(models.Model):
    """
    Modelo para manejar documentos semestrales asociados a un fondo
    """
    
    class PeriodicityChoices(models.TextChoices):
        MONTHLY = 'monthly', 'Mensual'
        QUARTERLY = 'quarterly', 'Trimestral'
        SEMI_ANNUALLY = 'semi_annually', 'Semestral'
        ANNUALLY = 'annually', 'Anual'
    
    class CycleChoices(models.IntegerChoices):
        CYCLE_1 = 1, 'Ciclo 1'
        CYCLE_2 = 2, 'Ciclo 2'
        CYCLE_3 = 3, 'Ciclo 3'
        CYCLE_4 = 4, 'Ciclo 4'
        CYCLE_5 = 5, 'Ciclo 5'
        CYCLE_6 = 6, 'Ciclo 6'
        CYCLE_7 = 7, 'Ciclo 7'
        CYCLE_8 = 8, 'Ciclo 8'
        CYCLE_9 = 9, 'Ciclo 9'
        CYCLE_10 = 10, 'Ciclo 10'
        CYCLE_11 = 11, 'Ciclo 11'
        CYCLE_12 = 12, 'Ciclo 12' 
        
    PERIODICITY_CYCLES = {
        'monthly': 12,
        'quarterly': 4,
        'semi_annually': 2,
        'annually': 1,
    }
    
    fund = models.ForeignKey(
        Fund, 
        on_delete=models.CASCADE, 
        related_name="semestral_documents",
        verbose_name="Fondo"
    )
    
    document_type = models.ForeignKey(
        TypeSemestralDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tipo de documento",
        related_name="semestral_documents"
    )
    
    # Información de periodicidad
    periodicity = models.CharField(
        max_length=20,
        choices=PeriodicityChoices.choices,
        verbose_name="Periodicidad del documento"
    )
    
    cycle = models.PositiveSmallIntegerField(
        choices=CycleChoices.choices,
        verbose_name="Número de ciclo",
        help_text="Número del ciclo dentro de la periodicidad (Ej: 1-12 para mensual, 1-4 para trimestral, etc.)",
    )
    
    # Documento y metadatos
    document = models.FileField(
        upload_to=fund_semestral_document_path, 
        verbose_name="Documento semestral"
    )
    title = models.CharField(
        max_length=255, 
        verbose_name="Título del documento"
    )
    description = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Descripción del documento"
    )
    
    # Fechas
    period_start_date = models.DateField(
        verbose_name="Fecha de inicio del período"
    )
    period_end_date = models.DateField(
        verbose_name="Fecha de fin del período"
    )
    uploaded_date = models.DateField(
        auto_now_add=True,
        verbose_name="Fecha de subida"
    )
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Subido por"
    )
    
    class Meta:
        verbose_name = "Documento Semestral"
        verbose_name_plural = "Documentos Semestrales"
        ordering = ['-uploaded_date']
        indexes = [
            models.Index(fields=['fund', 'uploaded_date']),
        ]
    
    def __str__(self):
        return f"Documento Semestral - {self.fund.name}"

    @property
    def period_display(self):
        """Retorna una representación legible del período"""
        return f"{self.year} - Semestre {self.semester}"
    
    @property
    def cycles_per_year(self):
        """Retorna la cantidad de ciclos por año según la periodicidad"""
        return self.PERIODICITY_CYCLES.get(self.periodicity, 1)
    
    @property
    def periodicity_cycles(self):
        """Retorna el numero de ciclos por año"""
        cycles_map = {
            'monthly': 12,
            'quarterly': 4,
            'semi_annually': 2,
            'annually': 1,
        }
        
        return cycles_map.get(self.periodicity, 1)
    

# ============================================================================
# OTROSÍES
# ============================================================================
class OthersI(base_model.BaseModel):
    """
    Documentos de Otrosí adjuntos al fondo.
    Modificaciones o adiciones al contrato original.
    """
    fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        related_name="othersi",
        verbose_name="Fondo"
    )
    doc_number = models.CharField(
        max_length=100,
        verbose_name="Número del documento",
        help_text="Ej: No.1, No.2"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre del otrosí",
        help_text="Descripción breve del contenido"
    )
    document = models.FileField(
        upload_to=othersi_document_path,
        verbose_name="Documento"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Detalle de las modificaciones incluidas"
    )
    effective_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de vigencia",
        help_text="Fecha desde la cual aplica el otrosí"
    )

    class Meta:
        verbose_name = "Otrosí"
        verbose_name_plural = "Otrosíes"
        ordering = ['fund', 'doc_number']
        unique_together = ['fund', 'doc_number']

    def __str__(self):
        return f"Otrosí {self.doc_number} - {self.fund.name}"


class FundPriceHistory(models.Model):
    """
    Modelo para almacenar el historial de precios por unidad de los fondos.
    """
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='price_history')
    price_per_unit = models.DecimalField(max_digits=14, decimal_places=4)
    effective_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    notes = models.TextField(blank=True, null=True, help_text="Razón para el cambio de precio")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Historial de Precio de Fondo"
        verbose_name_plural = "Historial de Precios de Fondos"


class TrustAgreement(base_model.BaseModel):
    """
    Modelo para gestionar contratos fiduciarios asociados a un fondo. Es decir el dueño le entrega el fi a la institucion financiera
    """
    class TypesAgreement(models.TextChoices):
        ADMINISTRATION = 'administration', 'Administración'
        PAYMENTS = 'payments', 'Pagos'
        OTHER = 'other', 'Otro'
    
    class CurrencyChoices(models.TextChoices):
        USD = 'USD', 'Dólar Estadounidense'
        EUR = 'EUR', 'Euro'
        COP = 'COP', 'Peso Colombiano'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='trust_agreements')
    
    #========================================
    # INFORMACIÓN DEL CONTRATO
    #========================================
    agreement_number = models.CharField(max_length=100, unique=True)
    agreement_type = models.CharField(max_length=50, choices=TypesAgreement.choices)
    trust_code = models.CharField(max_length=100, blank=True, null=True)
    trust_name = models.CharField(max_length=255, blank=True, null=True)
    trust_nit = models.CharField(max_length=50, blank=True, null=True)
    
    #========================================
    # PARTES DEL CONTRATO
    #========================================
    trustor_name = models.CharField(max_length=255, help_text="Nombre del fideicomitente")
    trustor_nit = models.CharField(max_length=50, help_text="NIT del fideicomitente")
    trustor_legal_representative = models.CharField(max_length=255, help_text="Representante legal del fideicomitente")
    trustor_document_id = models.CharField(max_length=50, help_text="Documento de identidad del representante legal")
    
    trustee_name = models.CharField(max_length=255, help_text="Nombre de la fiduciaria")
    trustee_nit = models.CharField(max_length=50, help_text="NIT de la fiduciaria")
    trustee_legal_representative = models.CharField(max_length=255, help_text="Representante legal de la fiduciaria")
    
    beneficiary_name = models.CharField(max_length=255, help_text="Nombre del acreedor")
    beneficiary_document_id = models.CharField(max_length=50, help_text="Documento de identidad del acreedor")
    beneficiary_country = models.CharField(max_length=100, help_text="País del acreedor")
    
    #========================================
    # FECHAS
    #========================================
    construction_date = models.DateField(blank=True, null=True, help_text="Fecha de constitución del contrato")
    effective_date = models.DateField(help_text="Fecha de inicio de vigencia del contrato")
    expiration_date = models.DateField(blank=True, null=True, help_text="Fecha de expiración del contrato")
    
    #========================================
    # FINANCIERO
    #========================================
    approved_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True, help_text="Monto credito aprobado")
    currency = models.CharField(max_length=10, choices=CurrencyChoices.choices, default=CurrencyChoices.COP)
    
    #========================================
    # ESTADO Y DOCUMENTOS
    #========================================
    signed_document_url = models.FileField(upload_to=trust_agreement_signed_document_path, blank=True, null=True, help_text="Documento firmado del contrato fiduciario")
    electronic_envelope = models.FileField(upload_to=trust_agreement_electronic_envelope_path, blank=True, null=True, help_text="Sobre electrónico del contrato fiduciario")
    
    class Meta:
        verbose_name = "Contrato fiduciario"
        verbose_name_plural = "Contratos fiduciarios"
        ordering = ['-created_at']
        
