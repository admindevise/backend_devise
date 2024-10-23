from apps.utils.models import base_model
from apps.user.models import User
from cities_light.models import Country
from django.db import models

from os import path


def owner_file_path(instance, filename):
    folder_user_document = '{}_{}'.format(instance.user.document_number, instance.user.last_name)
    return path.join('socioeconomic_info', folder_user_document, filename)

class OriginFund(base_model.BaseModel):
    name = models.CharField(max_length=128)
    def __str__(self):
        return str(self.name)


class Socioeconomic(base_model.BaseModel):
    user = models.OneToOneField(User, on_delete= models.PROTECT)
    monthly_income = models.DecimalField(max_digits=15, decimal_places=3) #ingresos mensuales
    other_income = models.BooleanField(default=False) #otros ingresos?
    value_other_income = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True) #Valor otros ingresos
    monthly_expenses = models.DecimalField(max_digits=15, decimal_places=3) #egresos mensuales
    total_assets = models.DecimalField(max_digits=15, decimal_places=3) #Activos totales
    total_liabilities = models.DecimalField(max_digits=15, decimal_places=3) #Pasivos totales
    origin_of_funds = models.ForeignKey(
        OriginFund,
        on_delete=models.PROTECT,
    )
    income_explanation = models.TextField(blank=True, null=True) #explicacion de ingresos
    manage_public_resources = models.BooleanField(default=False)
    links_with_pep = models.BooleanField(default=False) #Viculos con PEP
    foreign_currency_operations = models.BooleanField(default=False) #Operaciones en moneda extranjera
    foreign_operations_country = models.ForeignKey( #Pais dodne hace las transacciones
        Country,
        on_delete = models.PROTECT,
        related_name='country_foreign_operations',
        blank=True, null=True
        )
    foreign_operations_value = models.DecimalField(
        max_digits=15, decimal_places=3,
        blank=True, null=True,
        )
    outside_tax_obligation = models.BooleanField(default=False)
    country_of_tax_residence = models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        related_name='country_tax_residence',
        blank=True, null=True,
        )
    tin_number_or_equivalent = models.CharField(max_length=128, blank=True, null=True)
    is_declarant = models.BooleanField(default=False)
    last_year_income_statement = models.FileField( #declaracion renta ultimo año
        upload_to=owner_file_path,
        blank=True,
        null=True,
    )
    economic_dependency_letter = models.FileField(
        upload_to=owner_file_path,
        blank=True,
        null=True,
    )
    certified_public_accountant = models.FileField(
        upload_to=owner_file_path,
        blank=True,
        null=True,
    )
    profesional_accountant_card = models.FileField(
        upload_to=owner_file_path,
        blank=True,
        null=True,
    )
    pension_payment_receipt = models.FileField(
        upload_to=owner_file_path,
        blank=True,
        null=True,
    )
    source_funds_support = models.FileField(
        upload_to=owner_file_path,
        blank=True,
        null=True,
    )