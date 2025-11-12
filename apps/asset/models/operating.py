from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.utils.models import base_model

class AssetOperatingIncome(base_model.BaseModel):
    """
    Ingresos operativos del activo por período.
    Permite registrar y calcular ingresos en diferentes períodos.
    """
    
    class PeriodType(models.TextChoices):
        MONTHLY = 'monthly', 'Mensual'
        QUARTERLY = 'quarterly', 'Trimestral'
        SEMI_ANNUAL = 'semi_annual', 'Semestral'
        ANNUAL = 'annual', 'Anual'
    
    # ========================================
    # RELACIONES
    # ========================================
    asset = models.ForeignKey(
        'asset.Asset',
        on_delete=models.CASCADE,
        related_name='operating_incomes',
        verbose_name="Activo"
    )
    
    # ========================================
    # PERÍODO
    # ========================================
    period_type = models.CharField(
        max_length=20,
        choices=PeriodType.choices,
        default=PeriodType.MONTHLY,
        verbose_name="Tipo de período"
    )
    
    period_year = models.PositiveIntegerField(
        verbose_name="Año"
    )
    
    period_month = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="Mes (1-12)"
    )
    
    period_quarter = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="Trimestre (1-4)"
    )
    
    # ========================================
    # INGRESOS OPERATIVOS TOTALES
    # ========================================
    total_operating_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Total ingresos operativos (COP)",
        help_text="Suma total de todos los ingresos operativos del período"
    )
    
    # ========================================
    # DESGLOSE (OPCIONAL)
    # ========================================
    rental_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Ingresos por arrendamiento (COP)"
    )
    
    other_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Otros ingresos (COP)"
    )
    
    # ========================================
    # INGRESOS NO OPERATIVOS
    # ========================================    
    non_operating_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Ingresos no operativos (COP)",
        help_text="Ingresos ocasionales: multas de arrendamiento, indemnizaciones, etc."
    )    
    
    # ========================================
    # METADATOS
    # ========================================
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )
    
    recorded_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='recorded_operating_incomes',
        verbose_name="Registrado por"
    )
    
    class Meta:
        verbose_name = "Ingreso Operativo del Activo"
        verbose_name_plural = "Ingresos Operativos del Activo"
        ordering = ['-period_year', '-period_month', '-created_at']
        unique_together = [
            ['asset', 'period_type', 'period_year', 'period_month', 'period_quarter']
        ]
    
    def __str__(self):
        period = f"{self.period_year}"
        if self.period_month:
            period += f"-{self.period_month:02d}"
        elif self.period_quarter:
            period += f" Q{self.period_quarter}"
        return f"{self.asset.asset_code} - Ingresos {period}"
    
    @property
    def period_display(self):
        """Formato legible del período"""
        if self.period_type == self.PeriodType.MONTHLY and self.period_month:
            months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            return f"{months[self.period_month - 1]} {self.period_year}"
        elif self.period_type == self.PeriodType.QUARTERLY and self.period_quarter:
            return f"Q{self.period_quarter} {self.period_year}"
        elif self.period_type == self.PeriodType.SEMI_ANNUAL:
            return f"Semestre {self.period_year}"
        elif self.period_type == self.PeriodType.ANNUAL:
            return f"Año {self.period_year}"
        return f"{self.period_year}"


class AssetOperatingExpense(base_model.BaseModel):
    """
    Gastos operativos del activo por período.
    Permite registrar y calcular gastos en diferentes períodos.
    """
    
    class PeriodType(models.TextChoices):
        MONTHLY = 'monthly', 'Mensual'
        QUARTERLY = 'quarterly', 'Trimestral'
        SEMI_ANNUAL = 'semi_annual', 'Semestral'
        ANNUAL = 'annual', 'Anual'
    
    # ========================================
    # RELACIONES
    # ========================================
    asset = models.ForeignKey(
        'asset.Asset',
        on_delete=models.CASCADE,
        related_name='operating_expenses',
        verbose_name="Activo"
    )
    
    # ========================================
    # PERÍODO
    # ========================================
    period_type = models.CharField(
        max_length=20,
        choices=PeriodType.choices,
        default=PeriodType.MONTHLY,
        verbose_name="Tipo de período"
    )
    
    period_year = models.PositiveIntegerField(
        verbose_name="Año"
    )
    
    period_month = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="Mes (1-12)"
    )
    
    period_quarter = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="Trimestre (1-4)"
    )
    
    # ========================================
    # GASTOS OPERATIVOS TOTALES
    # ========================================
    total_operating_expense = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Total gastos operativos (COP)",
        help_text="Suma total de todos los gastos operativos del período (mantenimiento, administración, impuestos, seguros, servicios)"
    )
    
    # ========================================
    # DESGLOSE (OPCIONAL)
    # ========================================
    maintenance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Mantenimiento (COP)"
    )
    
    administration = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Administración (COP)"
    )
    
    property_taxes = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Impuestos prediales (COP)"
    )
    
    insurance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Seguros (COP)"
    )
    
    utilities = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Servicios públicos (COP)"
    )
    
    other_expenses = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Otros gastos (COP)"
    )
    
    # ========================================
    # GASTOS NO OPERATIVOS Y OTROS (para FCF)
    # ========================================
    non_operating_expenses = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Gastos no operativos (COP)",
        help_text="Gastos que no son necesarios para mantener el inmueble: 4x1000, bancarios, asset management fees, etc."
    )
    
    capex = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="CAPEX - Gastos de capital (COP)",
        help_text="Gastos de capital: mejoras mayores, remodelaciones, equipamiento nuevo, etc."
    )
    
    debt_payment = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Pago de deuda (COP)",
        help_text="Pago total de deuda del período (principal + intereses)"
    )    
    
    # ========================================
    # METADATOS
    # ========================================
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )
    
    recorded_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='recorded_operating_expenses',
        verbose_name="Registrado por"
    )
    
    class Meta:
        verbose_name = "Gasto Operativo del Activo"
        verbose_name_plural = "Gastos Operativos del Activo"
        ordering = ['-period_year', '-period_month', '-created_at']
        unique_together = [
            ['asset', 'period_type', 'period_year', 'period_month', 'period_quarter']
        ]
    
    def __str__(self):
        period = f"{self.period_year}"
        if self.period_month:
            period += f"-{self.period_month:02d}"
        elif self.period_quarter:
            period += f" Q{self.period_quarter}"
        return f"{self.asset.asset_code} - Gastos {period}"
    
    @property
    def period_display(self):
        """Formato legible del período"""
        if self.period_type == self.PeriodType.MONTHLY and self.period_month:
            months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            return f"{months[self.period_month - 1]} {self.period_year}"
        elif self.period_type == self.PeriodType.QUARTERLY and self.period_quarter:
            return f"Q{self.period_quarter} {self.period_year}"
        elif self.period_type == self.PeriodType.SEMI_ANNUAL:
            return f"Semestre {self.period_year}"
        elif self.period_type == self.PeriodType.ANNUAL:
            return f"Año {self.period_year}"
        return f"{self.period_year}"