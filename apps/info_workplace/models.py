from apps.utils.models import base_model
from apps.user.models import User
from cities_light.models import Country, Region, SubRegion
from django.db import models


class Workplace(base_model.BaseModel):
    user = models.OneToOneField(
        User,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        
    )
    #Work info
    OCCUPATION = [
        ('INDEPENDIENTE', 'Independiente'),
        ('EMPLEADO', 'Empleado'),
        ('OTRO', 'Otro'),
    ]
    occupation = models.CharField(
        max_length = 126,
        choices = OCCUPATION,
        blank=True,
        null=True,
    )
    company_name = models.CharField(
        blank=True,
        null=True,
        max_length=128
        )
    company_position = models.CharField(
        blank=True,
        null=True,
        max_length=128
        )
    company_country = models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        related_name ='workplace_country'
        )
    company_region = models.ForeignKey(
        Region,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        related_name ='workplace_region'
        )
    company_city = models.ForeignKey(
        SubRegion,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        related_name ='workplace_city'
        )
    company_phone = models.CharField(
        max_length=128,
        null = True,
        blank = True
        )
    company_address = models.CharField(
        max_length=128,
        null = True,
        blank = True
        )
    company_zip = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        )
    