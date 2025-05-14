from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.kaleido.models import Wallet, InstanceOfTokenContract721
from apps.user.models import User
from apps.kaleido.utils import create_wallet_for_user, create_instance_token_contract_721
from apps.utils.models import base_model
from django.db import transaction

class Fund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    hd_wallet = models.OneToOneField(Wallet, on_delete=models.CASCADE, null=True, blank=True)
    token_contract_721 = models.OneToOneField(InstanceOfTokenContract721, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    amount_units = models.PositiveIntegerField(default=0, help_text="Cantidad de unidades del fondo")
    amount_tokens = models.PositiveIntegerField(default=0, help_text="Cantidad de tokens del fondo")
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
    number_of_investors = models.PositiveIntegerField(blank=True, null=True)


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

class FundInvestment(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="investments")
    investor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fund_investments")
    invested_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.investor.username} in {self.fund.name}"
    
    """ @classmethod
    def create_investment(cls, fund, investor, amount):
        
        Método de clase que gestiona todo el proceso de crear una inversión:
        1. Verifica disponibilidad de unidades
        2. Resta las unidades del fondo
        3. Crea el registro de inversión
        4. Todo en una sola transacción atómica
        
        Args:
            fund (Fund): El fondo donde se invertirá
            investor (User): El usuario que realiza la inversión
            amount (Decimal): La cantidad a invertir
            
        Returns:
            FundInvestment: La inversión creada
            
        Raises:
            ValueError: Si no hay suficientes unidades disponibles
        
        
        with transaction.atomic():
            # Bloquear el fondo para evitar condiciones de carrera
            fund_for_update = Fund.objects.select_for_update().get(pk=fund.pk)
            
            # Verificar disponibilidad
            if fund_for_update.amount < amount:
                raise ValueError(f"No hay suficientes unidades disponibles. Disponible: {fund_for_update.amount}")
            
            # Restar las unidades del fondo
            fund_for_update.amount -= amount
            fund_for_update.save(update_fields=['amount'])
            
            # Crear o actualizar la inversión
            investment, created = cls.objects.get_or_create(
                fund=fund_for_update,
                investor=investor,
                defaults={'invested_amount': 0}
            )
            
            # Actualizar monto invertido (acumulativo)
            investment.invested_amount += amount
            investment.save(update_fields=['invested_amount'])
            
            return investment """    
    
    class Meta:
        unique_together = ('fund', 'investor')
    

class TransferReceipt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transfer_receipts")
    transfer_id = models.CharField(max_length=255)
    fund = models.ForeignKey('Fund', on_delete=models.CASCADE, related_name="transfer_receipts", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transfer_id}"
    
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
    
    class Meta:
        verbose_name = "Token de Fondo"
        verbose_name_plural = "Tokens de Fondos"
        unique_together = ('fund', 'token_id')
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Token {self.token_id} del fondo {self.fund.name}"