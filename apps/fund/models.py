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

""" @receiver(post_save, sender=Fund)
def create_wallet_for_fund(sender, instance, created, **kwargs):
    if created and not instance.hd_wallet:
        secret = instance.secret
        if not secret:
            print("Error: Secret not provided for Fund creation.")
            return
        wallet, error = create_wallet_for_user(instance.user, secret)
        if wallet:
            instance.hd_wallet = wallet
            instance.save()
        else:
            print(f"Error creating wallet: {error}")

@receiver(post_save, sender=Fund)
def create_instance_token_contract_for_fund(sender, instance, created, **kwargs):
    if created:
        # Verificamos que se haya proporcionado un secret
        if not instance.secret:
            print("Error: Secret not provided for token contract instance creation.")
            instance.delete()
            return

        # Llamamos a la función para crear la instancia del contrato token.
        # Aquí asumo que usarás el secret del Fund como "instance_id" para la llamada; adáptalo según tu lógica.
        token_instance, error = create_intance_token_contract_721(instance.user, instance.secret, instance.name, instance.name[:3].upper())
        if token_instance:
            # Almacenamos el instance_id (u otra información) en el campo opcional del Fund
            instance.instance_token_contract = token_instance.instance_id
            try:
                instance.save()
            except Exception as e:
                print(f"Error saving Fund after token contract creation: {e}")
                token_instance.delete()  # Si fuera posible eliminar la instancia creada
                instance.delete()
        else:
            print(f"Error creating token contract instance: {error}")
            instance.delete() """