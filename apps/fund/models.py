from apps.kaleido.models import Wallet, InstanceOfTokenContract721
from apps.utils.models import base_model
from apps.user.models import User

from django.db import models
from django.utils import timezone
import uuid

class Fund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    hd_wallet = models.OneToOneField(Wallet, on_delete=models.CASCADE, null=True, blank=True)
    token_contract_721 = models.OneToOneField(InstanceOfTokenContract721, on_delete=models.CASCADE, null=True, blank=True)
    
    # Basic Information
    name = models.CharField(max_length=100)
    description = models.TextField()
    amount_units = models.PositiveIntegerField(default=0, help_text="Cantidad de unidades del fondo")
    amount_tokens = models.PositiveIntegerField(default=0, help_text="Cantidad de tokens del fondo")
    nickname_tokens = models.CharField(max_length=255, blank=True, null=True)
    secret = models.CharField(max_length=255, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    image = models.ImageField(upload_to='funds/images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        )
    status = models.CharField(choices=STATUS_CHOICES, max_length=10, default='active')
    
    # Regulatory Information
    superintendency_registry = models.CharField(max_length=50, blank=True, null=True, help_text="Financial Superintendency registry number")
    tax_id = models.CharField(max_length=20, blank=True, null=True, help_text="Tax identification number")
    
    FUND_TYPE_CHOICES = (
        ('real_estate', 'Real Estate'),
        ('securities', 'Securities'),
        ('private_equity', 'Private Equity'),
        ('pension', 'Voluntary Pension'),
        ('other', 'Other'),
    )
    fund_type = models.CharField(choices=FUND_TYPE_CHOICES, max_length=20, blank=True, null=True)
    management_company = models.CharField(max_length=100, blank=True, null=True)

    # Financial Parameters
    annual_return = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Annualized return percentage")
    initial_unit_value = models.DecimalField(max_digits=14, decimal_places=4, blank=True, null=True)
    total_assets = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    management_fee = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Management fee percentage")
    success_fee = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Performance fee percentage")
    risk_rating = models.CharField(max_length=10, blank=True, null=True, help_text="E.g.: AAA, AA+, BBB, etc.")

    # Investment Policies
    RISK_PROFILE_CHOICES = (
        ('conservative', 'Conservative'),
        ('moderate', 'Moderate'),
        ('aggressive', 'Aggressive'),
    )
    risk_profile = models.CharField(choices=RISK_PROFILE_CHOICES, max_length=15, blank=True, null=True)
    investment_horizon = models.PositiveSmallIntegerField(blank=True, null=True, help_text="Recommended time in years")
    asset_composition = models.JSONField(blank=True, null=True, help_text="Percentage distribution by asset type")
    
    DIVIDEND_DISTRIBUTION_CHOICES = (
        ('automatic_reinvestment', 'Automatic Reinvestment'),
        ('periodic_distribution', 'Periodic Distribution'),
        ('mixed', 'Mixed'),
    )
    dividend_distribution = models.CharField(choices=DIVIDEND_DISTRIBUTION_CHOICES, max_length=25, blank=True, null=True)

    # Operations
    minimum_investment = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    permanence_period = models.PositiveSmallIntegerField(blank=True, null=True, help_text="Minimum time in days")
    early_withdrawal_penalty = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Penalty percentage for early withdrawal")
    trading_hours = models.CharField(max_length=100, blank=True, null=True, help_text="E.g.: 8:00 a.m. - 1:00 p.m.")
    operations_closing_date = models.DateField(blank=True, null=True)

    # Other Relevant Fields
    main_manager = models.CharField(max_length=100, blank=True, null=True)
    operations_start_date = models.DateField(blank=True, null=True)


    def __str__(self):
        return self.name
    
    @property
    def wallet_id(self):
        return self.hd_wallet.id_wallet if self.hd_wallet else None
    
    @property
    def contract_address(self):
        return self.token_contract_721.contract_address if self.token_contract_721 else None
    
    @property
    def amount_total(self):
        """Retorna el monto total del fondo (cantidad * precio por unidad)"""
        return self.amount_units * self.price_per_unit if self.price_per_unit else 0
    
    @property
    def current_price(self):
        """Retorna el precio actual desde el historial (más reciente)"""
        latest_price = self.price_history.first()  # Ordenado por -effective_date
        return latest_price.price_per_unit if latest_price else self.price_per_unit

    def update_price(self, new_price, user=None, notes=None, effective_date=None):
        """
        Actualiza el precio del fondo y guarda el cambio en el historial.
        """
        # Guardar valor actual en el historial
        FundPriceHistory.objects.create(
            fund=self,
            price_per_unit=new_price,
            effective_date=effective_date or timezone.now(),
            created_by=user,
            notes=notes
        )
        
        # Actualizar el precio actual del fondo
        self.price_per_unit = new_price
        self.save(update_fields=['price_per_unit'])
        
        return self.price_per_unit

    def get_price_at(self, date):
        """
        Obtiene el precio del fondo en una fecha específica.
        """
        price = self.price_history.filter(effective_date__lte=date).order_by('-effective_date').first()
        return price.price_per_unit if price else None

    def get_price_history(self, start_date=None, end_date=None):
        """
        Obtiene el historial de precios en un rango de fechas.
        """
        queryset = self.price_history.all()
        
        if start_date:
            queryset = queryset.filter(effective_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(effective_date__lte=end_date)
            
        return queryset

    @property
    def total_investors(self):
        """
        Retorna el número total de inversores únicos en este fondo.
        Calcula este valor en tiempo real consultando las inversiones relacionadas.
        """
        return self.investments.values('investor').distinct().count()

class FundApplication(models.Model):
    """
    Modelo para manejar las solicitudes de ingreso a fondos y el proceso de verificación.
    Responsabilidad: Gestionar el proceso de aplicación y verificación inicial.
    """
    
    class ApplicationStatus(models.TextChoices):
        """Enum para estados de la aplicación usando TextChoices (Django 3.0+)"""
        PENDING = 'pending', 'Solicitud Pendiente'
        UNDER_REVIEW = 'under_review', 'En Revisión'
        APPROVED = 'approved', 'Aprobada'
        REJECTED = 'rejected', 'Rechazada'
        CANCELLED = 'cancelled', 'Cancelada'
    
    # Relaciones
    fund = models.ForeignKey(
        Fund, 
        on_delete=models.CASCADE, 
        related_name="applications",
        verbose_name="Fondo"
    )
    applicant = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="fund_applications",
        verbose_name="Solicitante"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_applications",
        verbose_name="Revisado por"
    )
    
    # Información de la aplicación
    status = models.CharField(
        max_length=15,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        verbose_name="Estado"
    )
    requested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Monto solicitado",
        help_text="Monto que el solicitante desea invertir"
    )
    
    # Fechas del proceso
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de solicitud")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    reviewed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de revisión"
    )
    
    # Notas y observaciones
    applicant_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas del solicitante",
        help_text="Información adicional proporcionada por el solicitante"
    )
    review_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas de revisión",
        help_text="Observaciones del proceso de revisión"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de rechazo"
    )
    
    class Meta:
        unique_together = ('fund', 'applicant')
        ordering = ['-created_at']
        verbose_name = "Solicitud de Fondo"
        verbose_name_plural = "Solicitudes de Fondos"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['fund', 'status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.applicant.email} → {self.fund.name} ({self.get_status_display()})"
    
    @property
    def is_approved(self) -> bool:
        """Verifica si la aplicación está aprobada."""
        return self.status == self.ApplicationStatus.APPROVED
    
    @property
    def can_proceed_to_investment(self) -> bool:
        """Verifica si puede proceder al proceso de inversión."""
        return self.is_approved

class FundInvestment(models.Model):
    """
    Modelo para manejar las inversiones activas en fondos.
    Responsabilidad: Gestionar el proceso de compra de tokens e inversión final.
    """
    
    class InvestmentStatus(models.TextChoices):
        APPROVED = 'approved', 'Verificación Aprobada'
        ACTIVE = 'active', 'Activa'
        INACTIVE = 'inactive', 'Inactiva'
        CANCELLED = 'cancelled', 'Cancelada'
        SUSPENDED = 'suspended', 'Suspendida'
    
    # Relaciones
    application = models.OneToOneField(
        FundApplication,
        on_delete=models.CASCADE,
        related_name="investment",
        verbose_name="Solicitud asociada",
        null=True,
        blank=True
    )
    fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        related_name="investments",
        verbose_name="Fondo"
    )
    investor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="fund_investments",
        verbose_name="Inversor"
    )
    
    # Estado y montos
    status = models.CharField(
        max_length=25,
        choices=InvestmentStatus.choices,
        default=InvestmentStatus.APPROVED,
        verbose_name="Estado"
    )
    invested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Monto invertido",
        help_text="Monto realmente invertido"
    )
    
    # Fechas del proceso
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación", null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    
    # Información adicional
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de cancelación"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Inversión en Fondo"
        verbose_name_plural = "Inversiones en Fondos"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['fund', 'investor']),
            models.Index(fields=['investor', 'status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.investor.email} → {self.fund.name} ({self.get_status_display()})"
    
    @property
    def investment_return(self) -> float:
        """Retorno de la inversión (ganancia/pérdida)."""
        if self.invested_amount > 0:
            current_value = self.current_fund_value
            return current_value - float(self.invested_amount)
        return 0.0
    
    @property
    def investment_return_percentage(self) -> float:
        """Porcentaje de retorno de la inversión."""
        if self.invested_amount > 0:
            return (self.investment_return / float(self.invested_amount)) * 100
        return 0.0
    
    @property
    def is_completed(self) -> bool:
        """Verifica si la inversión está completada."""
        return self.status == self.InvestmentStatus.INVESTMENT_COMPLETED 

class TransferReceipt(base_model.BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transfer_receipts")
    transaction_id = models.CharField(max_length=255)
    fund = models.ForeignKey('Fund', on_delete=models.CASCADE, related_name="transfer_receipts", null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_id} - {self.fund.name if self.fund else 'N/A'}"
    
class FundPriceHistory(base_model.BaseModel):
    """
    Modelo para almacenar el historial de precios por unidad de los fondos.
    """
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='price_history')
    price_per_unit = models.DecimalField(max_digits=14, decimal_places=4)
    effective_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    notes = models.TextField(blank=True, null=True, help_text="Razón para el cambio de precio")
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Historial de Precio de Fondo"
        verbose_name_plural = "Historial de Precios de Fondos"
        
    def __str__(self):
        return f"{self.fund.name}: {self.price_per_unit} ({self.effective_date.strftime('%Y-%m-%d %H:%M')})"

class FundToken(base_model.BaseModel):
    """
    Modelo para almacenar los tokens asociados a un fondo.
    """
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='tokens')
    token_id = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    nickname = models.CharField(max_length=255, blank=True, null=True)
    owner_user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name="owned_tokens")
    
    reserved_for_sale = models.BooleanField(default=False)
    reserved_for_purchase = models.BooleanField(default=False)
    reserved_at = models.DateTimeField(null=True, blank=True)
    reservation_expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Token de Fondo"
        verbose_name_plural = "Tokens de Fondos"
        unique_together = ('fund', 'token_id')
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Token {self.token_id} del fondo {self.fund.name}"
    
class TokenTransaction(base_model.BaseModel):
    """
    Modelo para registrar todos los movimientos de tokens a nivel global
    """
    
    class TransactionStatus(models.TextChoices):
        COMPLETED = 'COMPLETED', 'Completada'
        PENDING = 'PENDING', 'Pendiente'
        FAILED = 'FAILED', 'Fallida'
    
    class TransactionTypes(models.TextChoices):
        MINT = 'MINTED', 'Creación de Token'
        BURN = 'BURNED', 'Quema de Token'
        TRANSFER = 'TRANSFER', 'Transferencia de Token'
        PURCHASE = 'PURCHASE', 'Compra de Token'
        SALE = 'SOLD', 'Venta de Token'
        INDEX_TRANSFER = 'INDEX_TRANSFER', 'Transferencia Index-to-Index'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Información del token
    fund = models.ForeignKey(Fund, on_delete=models.PROTECT, related_name='token_transactions')
    token = models.ForeignKey(FundToken, on_delete=models.PROTECT, related_name='transactions')
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionTypes.choices,
        default=TransactionTypes.TRANSFER,)
    
    # Participantes
    from_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='token_transactions_sent', null=True, blank=True)
    to_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='token_transactions_received', null=True, blank=True)
    
    # Detalles de la transacción
    kaleido_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount = models.IntegerField(default=0, help_text="Cantidad de tokens involucrados en la transacción")
    
    # Relación con trading (si aplica)
    trading_transaction = models.ForeignKey('trading.Transaction', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Estado y metadatos
    status = models.CharField(
        max_length=20, 
        choices=TransactionStatus.choices, 
        default=TransactionStatus.COMPLETED)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transacción de Token"
        verbose_name_plural = "Transacciones de Tokens"