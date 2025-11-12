from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.utils.models import base_model


class FundOperatingIncome(base_model.BaseModel):
    """
    Ingresos operativos del fondo por período.
    
    Representa los ingresos generados por los activos del fondo:
    - Rentas de arrendamiento
    - Ingresos por servicios
    - Otros ingresos operativos
    
    Nota: NO confundir con distribuciones a inversores.
    """
    
    class PeriodType(models.TextChoices):
        MONTHLY = 'monthly', 'Mensual'
        QUARTERLY = 'quarterly', 'Trimestral'
        SEMI_ANNUAL = 'semi_annual', 'Semestral'
        ANNUAL = 'annual', 'Anual'
    
    # ========================================
    # RELACIONES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name='operating_incomes',
        verbose_name="Fondo"
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
    # DESGLOSE DE INGRESOS (OPCIONAL)
    # ========================================
    rental_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Ingresos por arrendamiento (COP)",
        help_text="Suma de rentas de todos los activos del fondo"
    )
    
    parking_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Ingresos por parqueaderos (COP)"
    )
    
    storage_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Ingresos por bodegas (COP)"
    )
    
    amenities_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Ingresos por amenidades (COP)",
        help_text="Salones de eventos, gimnasio, co-working, etc."
    )
    
    late_fees = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Multas por mora (COP)"
    )
    
    other_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Otros ingresos operativos (COP)"
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
        help_text="Ingresos ocasionales: indemnizaciones, intereses bancarios, venta de activos, etc."
    )
    
    # ========================================
    # DESGLOSE POR ASSET (OPCIONAL)
    # ========================================
    income_breakdown_by_asset = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Desglose por activo",
        help_text="Diccionario con asset_id: monto para trazabilidad"
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
        related_name='recorded_fund_operating_incomes',
        verbose_name="Registrado por"
    )
    
    verified_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='verified_fund_operating_incomes',
        verbose_name="Verificado por"
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de verificación"
    )
    
    class Meta:
        verbose_name = "Ingreso Operativo del Fondo"
        verbose_name_plural = "Ingresos Operativos del Fondo"
        ordering = ['-period_year', '-period_month', '-created_at']
        unique_together = [
            ['fund', 'period_type', 'period_year', 'period_month', 'period_quarter']
        ]
        indexes = [
            models.Index(fields=['fund', 'period_year', 'period_month']),
            models.Index(fields=['period_type', 'period_year']),
        ]
    
    def __str__(self):
        period = f"{self.period_year}"
        if self.period_month:
            period += f"-{self.period_month:02d}"
        elif self.period_quarter:
            period += f" Q{self.period_quarter}"
        return f"{self.fund.name} - Ingresos {period}: ${self.total_operating_income:,.2f}"
    
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
            semester = 1 if self.period_month and self.period_month <= 6 else 2
            return f"Semestre {semester} {self.period_year}"
        elif self.period_type == self.PeriodType.ANNUAL:
            return f"Año {self.period_year}"
        return f"{self.period_year}"
    
    @property
    def is_verified(self):
        """Indica si el registro ha sido verificado"""
        return self.verified_by is not None and self.verified_at is not None


class FundOperatingExpense(base_model.BaseModel):
    """
    Gastos operativos del fondo por período.
    
    Representa los gastos necesarios para operar los activos del fondo:
    - Mantenimiento
    - Administración
    - Impuestos
    - Seguros
    - Servicios públicos
    - Asset management fees
    
    Nota: NO confundir con distribuciones a inversores.
    """
    
    class PeriodType(models.TextChoices):
        MONTHLY = 'monthly', 'Mensual'
        QUARTERLY = 'quarterly', 'Trimestral'
        SEMI_ANNUAL = 'semi_annual', 'Semestral'
        ANNUAL = 'annual', 'Anual'
    
    # ========================================
    # RELACIONES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name='operating_expenses',
        verbose_name="Fondo"
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
        help_text="Suma total de todos los gastos operativos del período"
    )
    
    # ========================================
    # DESGLOSE DE GASTOS OPERATIVOS (OPCIONAL)
    # ========================================
    maintenance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Mantenimiento (COP)",
        help_text="Mantenimiento preventivo y correctivo de activos"
    )
    
    administration = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Administración (COP)",
        help_text="Gastos de administración de propiedades"
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
        verbose_name="Seguros (COP)",
        help_text="Seguros de los activos del fondo"
    )
    
    utilities = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Servicios públicos (COP)",
        help_text="Agua, luz, gas, aseo, etc."
    )
    
    security = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Seguridad (COP)"
    )
    
    legal_accounting = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Legal y contabilidad (COP)"
    )
    
    asset_management_fee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Asset Management Fee (COP)",
        help_text="Comisión de administración del fondo"
    )
    
    property_management_fee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Property Management Fee (COP)",
        help_text="Comisión de gestión de propiedades"
    )
    
    other_expenses = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Otros gastos operativos (COP)"
    )
    
    # ========================================
    # GASTOS NO OPERATIVOS (PARA FCF)
    # ========================================
    non_operating_expenses = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Gastos no operativos (COP)",
        help_text="4x1000, bancarios, multas, intereses no relacionados con deuda, etc."
    )
    
    # ========================================
    # CAPEX - GASTOS DE CAPITAL (PARA FCF)
    # ========================================
    capex = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="CAPEX - Gastos de capital (COP)",
        help_text="Mejoras mayores, remodelaciones, equipamiento nuevo, expansiones"
    )
    
    # ========================================
    # SERVICIO DE DEUDA (PARA FCF)
    # ========================================
    debt_principal_payment = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Pago de principal de deuda (COP)",
        help_text="Amortización de capital de préstamos"
    )
    
    debt_interest_payment = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Pago de intereses de deuda (COP)",
        help_text="Intereses pagados sobre préstamos"
    )
    
    @property
    def total_debt_service(self):
        """Total de servicio de deuda (principal + intereses)"""
        principal = self.debt_principal_payment or Decimal('0.00')
        interest = self.debt_interest_payment or Decimal('0.00')
        return principal + interest
    
    # ========================================
    # DESGLOSE POR ASSET (OPCIONAL)
    # ========================================
    expense_breakdown_by_asset = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Desglose por activo",
        help_text="Diccionario con asset_id: monto para trazabilidad"
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
        related_name='recorded_fund_operating_expenses',
        verbose_name="Registrado por"
    )
    
    verified_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='verified_fund_operating_expenses',
        verbose_name="Verificado por"
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de verificación"
    )
    
    class Meta:
        verbose_name = "Gasto Operativo del Fondo"
        verbose_name_plural = "Gastos Operativos del Fondo"
        ordering = ['-period_year', '-period_month', '-created_at']
        unique_together = [
            ['fund', 'period_type', 'period_year', 'period_month', 'period_quarter']
        ]
        indexes = [
            models.Index(fields=['fund', 'period_year', 'period_month']),
            models.Index(fields=['period_type', 'period_year']),
        ]
    
    def __str__(self):
        period = f"{self.period_year}"
        if self.period_month:
            period += f"-{self.period_month:02d}"
        elif self.period_quarter:
            period += f" Q{self.period_quarter}"
        return f"{self.fund.name} - Gastos {period}: ${self.total_operating_expense:,.2f}"
    
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
            semester = 1 if self.period_month and self.period_month <= 6 else 2
            return f"Semestre {semester} {self.period_year}"
        elif self.period_type == self.PeriodType.ANNUAL:
            return f"Año {self.period_year}"
        return f"{self.period_year}"
    
    @property
    def is_verified(self):
        """Indica si el registro ha sido verificado"""
        return self.verified_by is not None and self.verified_at is not None
    
    @property
    def total_non_operating_and_capex(self):
        """Total de gastos no operativos + CAPEX (para cálculo de FCF)"""
        non_op = self.non_operating_expenses or Decimal('0.00')
        capex = self.capex or Decimal('0.00')
        return non_op + capex