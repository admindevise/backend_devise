from apps.utils.models import base_model
from cities_light.models import Country, Region, SubRegion

from django.db import models
from os import path

# Create your models here.
def notaria_file_path(instance, filename):
    try:#in apirest is here
        folder_user_document = '{}_{}'.format(instance.name, instance.nit)
    except:#in back oficce is here
        folder_user_document = '{}_{}'.format(instance.name, instance.nit)
    return path.join('notaria_docs', folder_user_document, filename)

class Notaria(base_model.BaseModel):
    
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
    mobile = models.CharField(
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
    codigo = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        unique=True
        )
    numero = models.CharField(
        max_length=64,
        null = True,
        blank = True,
        unique=True
        )
    email = models.EmailField(
        max_length=256,
        null=True,
        blank=True,
        )
    
    
    def __str__(self):
        return str(self.name)

    def get_country_display(self):
        if self.country:
            return self.country.name
        return ''

    def get_region_display(self):
        if self.region:
            return self.region.name
        return ''

    def get_city_display(self):
        if self.city:
            return self.city.name
        return ''


    
