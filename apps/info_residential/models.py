from apps.utils.models import base_model
from apps.user.models import User
from cities_light.models import Country, Region, SubRegion
from django.db import models


class Residentialplace(base_model.BaseModel):
    user = models.OneToOneField(
        User,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        
    )
    #Resident Info
    resident_country = models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        related_name ='resident_country'
        )
    resident_region = models.ForeignKey(
        Region,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        related_name ='resident_region'
        )
    resident_city = models.ForeignKey(
        SubRegion,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        related_name ='resident_city'
        )
    resident_address = models.CharField(
        max_length=128,
        null = True,
        blank = True,
        )
    resident_phone = models.CharField(
        max_length=128,
        null = True,
        blank = True
        )
    resident_zip = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        )
    