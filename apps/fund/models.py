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
    created_at = models.DateTimeField(auto_now_add=True)

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
