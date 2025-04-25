from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.kaleido.models import Wallet, InstanceOfTokenContract721
from apps.user.models import User
from apps.kaleido.utils import create_wallet_for_user, create_instance_token_contract_721

class Fund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    hd_wallet = models.OneToOneField(Wallet, on_delete=models.CASCADE, null=True, blank=True)
    token_contract_721 = models.OneToOneField(InstanceOfTokenContract721, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    secret = models.CharField(max_length=255, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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

class FundInvestment(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="investments")
    investor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fund_investments")
    invested_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.investor.username} in {self.fund.name}"
    
    class Meta:
        unique_together = ('fund', 'investor')

class TransferReceipt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transfer_receipts")
    transfer_id = models.CharField(max_length=255)
    fund = models.ForeignKey('Fund', on_delete=models.CASCADE, related_name="transfer_receipts", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transfer_id}"
    
class FundPrice(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE)
    unitPrice = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.fund.name} - {self.timestamp}"
