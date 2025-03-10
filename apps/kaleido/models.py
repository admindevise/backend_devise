from django.db import models
from apps.utils.models import base_model
from apps.user.models import User
from apps.asset.models import ActivoInversion

class AppContract(base_model.BaseModel):
    """
    This class represents to app contract application.
    """
    app_contract_id = models.CharField(max_length=255, blank=False, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False, null=False)
    
    def __str__(self):
        return f"{self.name} - {self.app_contract_id}"

class CompileContract(base_model.BaseModel):
    """
    This class represents a compiled contract associated with an app contract.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    app_contract = models.ForeignKey(AppContract, on_delete=models.CASCADE, related_name='compilations', null=True, blank=True)
    description = models.TextField(max_length=255, blank=False, null=False)
    contract_url = models.URLField(max_length=255, blank=False, null=False)
    compiled_contract_id = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.app_contract.name} - {self.description}"
    
class PromoteContract(base_model.BaseModel):
    """
    This class represents a promoted contract associated with an app contract.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    app_contract = models.ForeignKey(AppContract, on_delete=models.CASCADE, related_name='promotions', null=False, blank=False)
    compiled_contract = models.ForeignKey(CompileContract, on_delete=models.CASCADE, related_name='promotions', null=False, blank=False)
    endpoint = models.CharField(max_length=255, blank=False, null=False)
    
    def __str__(self):
        return self.endpoint
    

# Create your models here.
class Wallet(base_model.BaseModel):
    user = models.ForeignKey(
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
    
    def __str__(self):
        return f"{self.id_wallet}"
    
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
    
class InstanceOfTokenContract721(base_model.BaseModel):
    """
    This class represents an instance of a Token Contract 721.
    It is used to manage the details of a specific token contract, including the user who created it,
    the name of the contract, and its symbol.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    promote_contract = models.ForeignKey(PromoteContract, on_delete=models.CASCADE, related_name='token_instances', null=True)
    name = models.CharField(max_length=255, blank=False, null=False)
    symbol = models.CharField(max_length=255, blank=False, null=False)
    contract_address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.symbol}"
        
    @property
    def endpoint(self):
        """
        Accede al endpoint a través de la relación con PromoteContract
        """
        return self.promote_contract.endpoint if self.promote_contract else None