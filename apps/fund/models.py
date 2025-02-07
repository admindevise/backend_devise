from django.db import models
from apps.kaleido.models import Wallet
from apps.user.models import User

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.kaleido.views.kaleido_fund import create_wallet_for_user

class Fund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    hd_wallet = models.OneToOneField(Wallet, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class FundPrice(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE)
    unitPrice = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.fund.name} - {self.timestamp}"

@receiver(post_save, sender=Fund)
def create_wallet_for_fund(sender, instance, created, **kwargs):
    if created and not instance.hd_wallet:
        # Define el secret, por ejemplo, con un valor predeterminado o generado por otra fuente
        secret = "the bed in the sea is blue color in the night right"
        wallet, error = create_wallet_for_user(instance.user, secret)
        if wallet:
            instance.hd_wallet = wallet
            instance.save()
        else:
            # Aquí puedes registrar el error
            print(f"Error creando wallet: {error}")