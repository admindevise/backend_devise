from django.db import models
from django.utils import timezone

class InvestorContract(models.Model):
    """
    Modelo para manejar contratos de vinculaciones a fondos.
    Responsabilidad: Gestionar el estado del contrato entre el usuario y el fondo.
    """
    class FundApprovalStatus(models.TextChoices):
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
        choices=FundApprovalStatus.choices,
        default=FundApprovalStatus.PENDING_SIGNATURE,
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
    