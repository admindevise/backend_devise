from apps.utils.models import base_model
from apps.info_financial.models import Financial
from cities_light.models import Country, Region, SubRegion

from django.db import models
from os import path

# Create your models here.
def fiducia_file_path(instance, filename):
    try:#in apirest is here
        folder_user_document = '{}_{}'.format(instance.name, instance.nit)
    except:#in back oficce is here
        folder_user_document = '{}_{}'.format(instance.name, instance.nit)
    return path.join('fiducia_docs', folder_user_document, filename)

class Fiducia(base_model.BaseModel):
    
    name = models.CharField(
        max_length=128
        )
    country = models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        )
    region = models.ForeignKey(
        Region,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        )
    city = models.ForeignKey(
        SubRegion,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        )
    phone = models.CharField(
        max_length=128,
        null = True,
        blank = True
        )
    address = models.CharField(
        max_length=128,
        null = True,
        blank = True
        )
    zip_code = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        )
    nit = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        unique=True
        )
    camara_comercio = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        unique=True
        )
    logo = models.ImageField(
        upload_to = fiducia_file_path,
        )
    informacion = models.TextField(
        null = True,
        blank = True
        )
    area = models.CharField(
        max_length=128,
        null = True,
        blank = True
        )
    financial_profile = models.ForeignKey(
        Financial,
        related_name='cuenta_fiducia',
        on_delete = models.PROTECT,
        null = True,
        blank = True,
    )
    def __str__(self):
        return str(self.name)

    def get_country_display(self):
        if self.company_country:
            return self.company_country.name
        return ''

    def get_region_display(self):
        if self.company_region:
            return self.company_region.name
        return ''

    def get_city_display(self):
        if self.company_city:
            return self.company_city.name
        return ''


    
