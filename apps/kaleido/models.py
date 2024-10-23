from django.db import models
from apps.utils.models import base_model
from apps.user.models import User
from apps.asset.models import ActivoInversion

# Create your models here.
class Wallet(base_model.BaseModel):
    user = models.OneToOneField(
        User,
        on_delete = models.CASCADE,
        null = True,
        blank = True,
    )
    #Wallet Info
    id_wallet = models.CharField(
        max_length=50,
        null = False,
        blank = False,
        )
    secret = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    environment_id = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    wallet_service = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    zone_domain = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    consortia = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    


class WalletSmartContract(base_model.BaseModel):
    activo_inversion = models.ForeignKey(ActivoInversion, on_delete=models.CASCADE)
    id_wallet = models.CharField(
        max_length=50,
        null = False,
        blank = False,
        )
    secret = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    environment_id = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    wallet_service = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    zone_domain = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    consortia = models.CharField(
        max_length=255,
        null = False,
        blank = False,
        )
    metadata_wallet = models.JSONField(null=True, blank=True)
    type_wallet = models.CharField(
        max_length=20,
        null = True,
        blank = True,
        )