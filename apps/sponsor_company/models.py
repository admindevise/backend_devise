from apps.utils.models import base_model
from apps.user.models import User
from cities_light.models import Country, Region, SubRegion
from django.db import models

from os import path

from django.db.models import Sum


def owner_file_path(instance, filename):
    folder_user_document = '{}_{}'.format(instance.user.document_number, instance.user.last_name)
    return path.join('business_info', folder_user_document, filename)

class SponsorCompany(base_model.BaseModel):
    user = models.OneToOneField(
        User,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
    )
    #Own Company Info
    company_name = models.CharField(
        blank=True,
        null=True,
        max_length=128
        )
    company_country = models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        related_name ='company_country'
        )
    company_region = models.ForeignKey(
        Region,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        related_name ='company_region'
        )
    company_city = models.ForeignKey(
        SubRegion,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
        related_name ='company_city'
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
    company_zip_code = models.CharField(
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
    logo_empresa = models.ImageField(
        upload_to = owner_file_path,
        )
    info_empresa = models.TextField(
        null = True,
        blank = True
        )
    area_registro = models.CharField(
        max_length=128,
        null = True,
        blank = True
        )
    admin_approved = models.BooleanField(
        default=False
        )
    def __str__(self):
        return str(self.company_name)

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

    def get_user_full_name(self):
        if self.user:
            return self.user.get_full_name()
        return ''
    

    def get_activos_administrados(self):
        from apps.asset.models import ActivoInversion
        return ActivoInversion.objects.filter(sponsor = self).count()
    
    def get_clientes(self):
        from apps.asset.models import ActivoInversion
        activos = ActivoInversion.objects.filter(sponsor = self)
        return activos.values('propietario').distinct().count()
    
    def get_total_inversiones(self):
        from apps.asset.models import ActivoInversion
        activos = ActivoInversion.objects.filter(sponsor = self)
        total_inversiones = activos.aggregate(total=Sum('valor_activo'))['total']
        if total_inversiones is None:
            total_inversiones = 0
        return total_inversiones
    
