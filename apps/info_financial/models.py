from apps.utils.models import base_model
from apps.user.models import User
from apps.druo.models import Bank, AccountType, AccountSubtype
from django.db import models

from os import path

def owner_file_path(instance, filename):
    if instance.user :
        folder_user_document = '{}_{}'.format(instance.user.document_number, instance.user.last_name)
    else:
        folder_user_document = 'fiducia'
    return path.join('financial_certs', folder_user_document, filename)

class Financial(base_model.BaseModel):
    user = models.OneToOneField(
        User,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
    )
    fiducia = models.ForeignKey(
        'fiducia.Fiducia',
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        related_name = 'pertenece_a_fiducia',
    )
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
        upload_to = owner_file_path
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
    
    