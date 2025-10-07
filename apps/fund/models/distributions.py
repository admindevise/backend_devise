from django.db import models
from django.utils import timezone
from decimal import Decimal
from apps.utils.models import base_model
from django.core.exceptions import ValidationError

class DistributionPeriod(base_model.BaseModel):
    """
    Período de distribución a nivel de fondo.
    Representa una distribución específica (mensual, trimestral, etc.)
    """
    
    class DistributionType(models.TextChoices):
        MONTHLY = 'monthly', 'Mensual'
        QUARTERLY = 'quarterly', 'Trimestral'
        SEMI_ANNUALLY = 'semi_annually', 'Semestral'
        ANNUALLY = 'annually', 'Anual'
        EXTRAORDINARY = 'extraordinary', 'Extraordinaria'
    
    class DistributionStatus(models.TextChoices):
        DRAFT = 'draft', 'Borrador'
        PENDING_APPROVAL = 'pending_approval', 'Pendiente de Aprobación'
        APPROVED = 'approved', 'Aprobado'
        PROCESSING = 'processing', 'Procesando'
        COMPLETED = 'completed', 'Completado'
        FAILED = 'failed', 'Fallido'
        CANCELLED = 'cancelled', 'Cancelado'
    
    # ========================================
    # RELACIONES PRINCIPALES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name='distribution_periods',
        verbose_name="Fondo"
    )
    
    # ========================================
    # INFORMACIÓN DEL PERÍODO
    # ========================================
    distribution_type = models.CharField(
        max_length=20,
        choices=DistributionType.choices,
        default=DistributionType.MONTHLY
    )
    
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveIntegerField(null=True, blank=True)
    period_quarter = models.PositiveIntegerField(null=True, blank=True)
    
    # ========================================
    # MONTOS Y CÁLCULOS
    # ========================================
    total_distribution_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Monto total a distribuir"
    )
    
    net_operating_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Ingreso operativo neto del período"
    )
    
    distribution_yield_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Porcentaje de rendimiento distribuido"
    )
    
    # ========================================
    # SNAPSHOT DE TOKENS AL MOMENTO DE DISTRIBUCIÓN
    # ========================================
    total_tokens_outstanding = models.PositiveIntegerField(
        verbose_name="Total tokens en circulación"
    )
    
    distribution_per_token = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Distribución por token"
    )
    
    # ========================================
    # FECHAS IMPORTANTES
    # ========================================
    record_date = models.DateField(
        verbose_name="Fecha de registro (snapshot de propietarios)"
    )
    
    ex_dividend_date = models.DateField(
        verbose_name="Fecha ex-dividendo"
    )
    
    payment_date = models.DateField(
        verbose_name="Fecha de pago programada"
    )
    
    # ========================================
    # ESTADO Y APROBACIONES
    # ========================================
    status = models.CharField(
        max_length=20,
        choices=DistributionStatus.choices,
        default=DistributionStatus.DRAFT
    )
    
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_distributions'
    )
    
    approved_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approved_distributions'
    )
    
    approved_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # ========================================
    # METADATOS Y AUDITORÍA
    # ========================================
    distribution_notes = models.TextField(blank=True)
    calculation_metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = [
            ('fund', 'period_year', 'period_month', 'distribution_type'),
        ]
        ordering = ['-period_year', '-period_month', '-created_at']
        verbose_name = "Período de Distribución"
        verbose_name_plural = "Períodos de Distribución"
        indexes = [
            models.Index(fields=['fund', 'status']),
            models.Index(fields=['record_date', 'status']),
            models.Index(fields=['payment_date']),
        ]
    
    def clean(self):
        """Validaciones de negocio"""
        if self.distribution_type == self.DistributionType.MONTHLY and not self.period_month:
            raise ValidationError("Distribuciones mensuales requieren especificar el mes")
        
        if self.distribution_type == self.DistributionType.QUARTERLY and not self.period_quarter:
            raise ValidationError("Distribuciones trimestrales requieren especificar el trimestre")
    
    def __str__(self):
        period = f"{self.period_year}-{self.period_month:02d}" if self.period_month else str(self.period_year)
        return f"{self.fund.name} - {period} (${self.total_distribution_amount:,.2f})"
    
    @property
    def period_display(self):
        """Formato legible del período"""
        if self.distribution_type == self.DistributionType.MONTHLY:
            months = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            return f"{months[self.period_month]} {self.period_year}"
        elif self.distribution_type == self.DistributionType.QUARTERLY:
            return f"Q{self.period_quarter} {self.period_year}"
        return str(self.period_year)

class InvestmentDistributionRecord(base_model.BaseModel):
    """
    Registro de distribución específico por inversión.
    Vincula distribuciones con inversiones individuales.
    """
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        CALCULATED = 'calculated', 'Calculado'
        VERIFIED = 'verified', 'Verificado'
        PROCESSING = 'processing', 'Procesando'
        PAID = 'paid', 'Pagado'
        FAILED = 'failed', 'Fallido'
        CANCELLED = 'cancelled', 'Cancelado'
        REINVESTED = 'reinvested', 'Reinvertido'
    
    class DistributionType(models.TextChoices):
        COP_AMOUNT = 'cop_amount', 'Monto en COP'
        TOKEN_TRANSFER = 'token_transfer', 'Transferencia de Tokens'
    
    # ========================================
    # RELACIONES PRINCIPALES
    # ========================================
    distribution_period = models.ForeignKey(
        DistributionPeriod,
        on_delete=models.CASCADE,
        related_name='investment_records'
    )
    
    investment = models.ForeignKey(
        'fund.FundInvestment',
        on_delete=models.CASCADE,
        related_name='distribution_records'
    )
    
    # ========================================
    # DISTRIBUCIÓN EN PESOS COP
    # ========================================
    distribution_type = models.CharField(
        max_length=20,
        choices=DistributionType.choices,
        default=DistributionType.COP_AMOUNT,
        verbose_name="Tipo de distribución"
    )
    
    # Distribución calculada en pesos COP
    gross_distribution_amount_cop = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto bruto distribución (COP)",
        help_text="Monto calculado en pesos colombianos"
    )
    
    withholding_tax_cop = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,        
        default=Decimal('0.00'),
        verbose_name="Retención en la fuente (COP)"
    )
    
    net_distribution_amount_cop = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,        
        verbose_name="Monto neto distribución (COP)",
        help_text="Monto neto a distribuir en pesos colombianos"
    )
    
    # ========================================
    # CONVERSIÓN A TOKENS (VERIFICACIÓN)
    # ========================================
    cop_to_token_exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Tasa de cambio COP a tokens",
        help_text="Tokens por cada peso COP"
    )
    
    equivalent_tokens_calculated = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Tokens equivalentes calculados",
        help_text="Cantidad de tokens equivalente al monto COP"
    )
    
    tokens_to_transfer = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Tokens a transferir",
        help_text="Número entero de tokens que se transferirán"
    )
    
    remaining_cop_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto COP remanente",
        help_text="Monto en COP que no se pudo convertir a tokens enteros"
    )
    
    # ========================================
    # SNAPSHOT DE TOKENS EN EL RECORD DATE (EXISTENTE)
    # ========================================
    tokens_held_on_record_date = models.PositiveIntegerField(
        verbose_name="Tokens poseídos en fecha de registro"
    )
    
    token_ids_snapshot = models.JSONField(
        verbose_name="IDs de tokens específicos",
        help_text="Lista de token_ids que poseía en la fecha de registro"
    )
    
    # ========================================
    # CÁLCULOS DE PARTICIPACIÓN
    # ========================================
    participation_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Porcentaje de participación"
    )
    
    # ========================================
    # INFORMACIÓN DE VERIFICACIÓN Y PAGO
    # ========================================
    verification_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de verificación"
    )
    
    verified_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='verified_distributions',
        verbose_name="Verificado por"
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CALCULATED
    )
    
    payment_method = models.CharField(
        max_length=30,
        choices=[
            ('cop_transfer', 'Transferencia COP'),
            ('token_transfer', 'Transferencia de Tokens'),
            ('bank_transfer', 'Transferencia Bancaria'),
            ('digital_wallet', 'Billetera Digital'),
            ('mixed', 'Mixto'),
            ('other', 'Otro'),
        ],
        null=True,
        blank=True
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
        verbose_name="Fecha efectiva de pago"
    )
    
    # ========================================
    # METADATOS Y AUDITORÍA
    # ========================================
    calculation_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos de cálculo"
    )
    
    verification_notes = models.TextField(
        blank=True,
        verbose_name="Notas de verificación"
    )
    
    payment_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = [
            ('distribution_period', 'investment'),
        ]
        ordering = ['-created_at']
        verbose_name = "Registro de Distribución por Inversión"
        verbose_name_plural = "Registros de Distribución por Inversión"
    
    def __str__(self):
        return f"Distribución {self.distribution_period.period_display} - {self.investment.application.user.email} - ${self.net_distribution_amount_cop:,.2f} COP"
    
    @property
    def has_cop_distribution(self):
        """Verifica si tiene distribución en COP"""
        return self.net_distribution_amount_cop > 0
    
    @property
    def is_verified_for_tokens(self):
        """Verifica si está listo para transferir tokens"""
        return (
            self.payment_status == self.PaymentStatus.VERIFIED and
            self.equivalent_tokens_calculated is not None and
            self.tokens_to_transfer is not None
        )
    
    def calculate_token_equivalent(self, token_price_cop: Decimal) -> dict:
        """
        Calcula equivalencia en tokens del monto COP
        
        Args:
            token_price_cop: Precio de 1 token en pesos COP
            
        Returns:
            dict: Información de la conversión
        """
        if token_price_cop <= 0:
            raise ValueError("El precio del token debe ser mayor a cero")
        
        # Calcular tokens exactos (con decimales)
        exact_tokens = self.net_distribution_amount_cop / token_price_cop
        
        # Tokens enteros que se pueden transferir
        whole_tokens = int(exact_tokens)
        
        # Monto COP equivalente a tokens enteros
        cop_for_tokens = Decimal(str(whole_tokens)) * token_price_cop
        
        # Monto COP remanente
        remaining_cop = self.net_distribution_amount_cop - cop_for_tokens
        
        return {
            'exact_tokens_calculated': exact_tokens,
            'whole_tokens_to_transfer': whole_tokens,
            'cop_amount_for_tokens': cop_for_tokens,
            'remaining_cop_amount': remaining_cop,
            'token_price_used': token_price_cop,
            'conversion_efficiency': (cop_for_tokens / self.net_distribution_amount_cop) * 100 if self.net_distribution_amount_cop > 0 else 0
        }

class TokenDistributionDetail(base_model.BaseModel):
    """
    Detalle granular por token individual en cada distribución.
    Permite trazabilidad completa y cálculos específicos por token.
    """
    
    # ========================================
    # RELACIONES
    # ========================================
    investment_distribution = models.ForeignKey(
        InvestmentDistributionRecord,
        on_delete=models.CASCADE,
        related_name='token_details'
    )
    
    token = models.ForeignKey(
        'fund.FundToken',
        on_delete=models.CASCADE,
        related_name='distribution_details'
    )
    
    # ========================================
    # INFORMACIÓN DEL TOKEN
    # ========================================
    token_nickname = models.CharField(max_length=255)
    
    owner_on_record_date = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        verbose_name="Propietario en fecha de registro"
    )
    
    # ========================================
    # CÁLCULOS POR TOKEN
    # ========================================
    distribution_amount = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        verbose_name="Monto distribuido a este token"
    )
    
    days_held_in_period = models.PositiveIntegerField(
        verbose_name="Días poseído en el período"
    )
    
    acquisition_date = models.DateTimeField(
        verbose_name="Fecha de adquisición del token"
    )
    
    # ========================================
    # METADATOS
    # ========================================
    calculation_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = [
            ('investment_distribution', 'token'),
        ]
        ordering = ['-created_at']
        verbose_name = "Detalle de Distribución por Token"
        verbose_name_plural = "Detalles de Distribución por Token"
        indexes = [
            models.Index(fields=['token', 'investment_distribution']),
            models.Index(fields=['owner_on_record_date', 'investment_distribution']),
        ]
    
    def __str__(self):
        return f"Token {self.token_id} - ${self.distribution_amount:,.8f}"