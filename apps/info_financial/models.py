from django.db import models

from apps.user.models import User
from apps.druo.models import Bank, AccountType, AccountSubtype

from apps.utils.models import base_model
from apps.utils.models.file_helpers import info_financial_certification_file_path

class Financial(base_model.BaseModel):
    user = models.OneToOneField(
        User,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
    )
    """ fiducia = models.ForeignKey(
        'fiducia.Fiducia',
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        related_name = 'pertenece_a_fiducia',
    ) """
    #Account info
    bank = models.ForeignKey(
        Bank,
        on_delete = models.PROTECT,
        related_name ='banking_entity'
        )
    account_number = models.CharField(
        max_length=128,
        null = True,
        blank = True,
        )
    account_type = models.ForeignKey(
        AccountType,
        on_delete = models.PROTECT,
        related_name ='account_type'
        )
    account_subtype = models.ForeignKey(
        AccountSubtype,
        on_delete = models.PROTECT,
        related_name ='account_type'
        )
    certification_file = models.FileField(
        upload_to = info_financial_certification_file_path
        )
    aba_code = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        )
    swift_code = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        )
    
    