from apps.utils.models import base_model

from cities_light.models import Country, Region, SubRegion
from config import settings
from config.settings import WEETRUST_URL, WEETRUST_USER_ID, WEETRUST_API_KEY

from django.contrib.auth.models import (AbstractUser, BaseUserManager, Group)
from django.core.mail import EmailMessage
from django.db import models
from django.template.loader import render_to_string
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
import datetime as dt
from datetime import timedelta

import random

import string
import uuid


from os import path

def owner_file_path(instance, filename):
    try:#in apirest is here
        folder_user_document = '{}_{}'.format(instance.user.document_number, instance.user.last_name)
    except:#in back oficce is here
        folder_user_document = '{}_{}'.format(instance.document_number, instance.last_name)
    return path.join('user_docs', folder_user_document, filename)

class Role(base_model.BaseModel):
    name = models.CharField(max_length=126)
    groups = models.ManyToManyField(
        Group,
        blank = True,
    )
    class Meta:
        ordering = ['name']

    def __str__(self):
        return str(self.name)

class IdType(base_model.BaseModel): #æccording to DRUO config
    value = models.CharField(max_length=126)
    name = models.CharField(max_length=126)
    description = models.CharField(max_length=126)
    
    def __str__(self):
        return str(self.name)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users require an email field')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)
    
class User(AbstractUser,):
    #We use first name as names
    #We use last_name as surnames
    # username = None
    username = models.CharField('usuario', max_length=150, blank=True, unique=True, null=True)
    email = models.EmailField('correo electrónico', unique=True)
    USERNAME_FIELD = 'email'
    """Use the email as unique username."""
    REQUIRED_FIELDS = ['phone']
    indicative = models.CharField("indicativo", max_length=32)
    phone = models.CharField("teléfono", max_length=64)
    #after validate email
    is_natural_person = models.BooleanField(default=True)
    juridic_xlsx = models.FileField( upload_to=owner_file_path,
        blank=True,
        null=True,)
    first_name = models.CharField(max_length=128, blank= True, null=True)
    last_name = models.CharField(max_length=128, blank= True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    birth_country = models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        blank=True,
        null=True,
        related_name='birth_country'
        )
    birth_region = models.ForeignKey(
        Region,
        on_delete = models.PROTECT,
        blank=True,
        null=True,
        related_name='birth_region'
        )
    birth_city = models.ForeignKey(
        SubRegion,
        on_delete = models.PROTECT,
        blank=True,
        null=True,
        related_name='birth_city'
        )
    # Document info
    local_id_type = models.ForeignKey(
        IdType,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    document_number = models.CharField(
        blank=True,
        null=True,
        max_length=128,
        unique=True
        )
    document_front_image = models.ImageField(upload_to=owner_file_path)
    document_back_image = models.ImageField(
        upload_to=owner_file_path,
        blank=True,
        null=True,
        )
    selfie = models.ImageField(
        upload_to=owner_file_path,
        blank=True,
        null=True,
        )
    doc_country_expedition =  models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        blank=True,
        null=True
        )
    doc_region_expedition = models.ForeignKey(
        Region,
        on_delete = models.PROTECT,
        blank=True,
        null=True
        )
    doc_city_expedition = models.ForeignKey(
        SubRegion,
        on_delete = models.PROTECT,
        blank=True,
        null=True
        )
    expedition_date = models.DateField( blank=True, null=True)
    # KYC 
    STATUS_KYC = [
        ('pending_document', 'Pendiente por cargar documento'),
        ('ready_for_kyc', 'Pendiente por subir a WeeTrust'),
        ('validating_document', 'Documento en Validación'),
        ('fail_document', 'Fallo en Documento'),
        ('sucessfull_document', 'KYC Validado'),

    ]
    kyc_validated = models.CharField(   #validated by Weetrust
        max_length = 64,
        choices = STATUS_KYC,
        default='pending_document'
    )
    
    #
    DELIVERY_METHOD = [
        ('E-MAIL', 'Correo Electronico'),
        ('DOMICILIO', 'A la Dirección del Domicilio'),
        ('TRABAJO', 'A la Direccion del Trabajo'),
    ]
    mail_delivery = models.CharField(
        max_length = 126,
        choices = DELIVERY_METHOD,
        blank=True,
        null=True,
    )
    #
    code = models.CharField(
            max_length=128,
            blank = True,
            null = True,
            unique=True,
            )
    referred_by_code = models.CharField(
        max_length=128,
        blank = True,
        null = True,
        )
    #
    role = models.ForeignKey(
        Role,
        on_delete = models.PROTECT,
        null = True,
        blank = True,
    )
    
    slug = models.SlugField(blank=True)
    fiducia = models.ForeignKey( #Si es Sponsor o Fiducia debemos saber a cual pertenece
        'fiducia.Fiducia',
        on_delete = models.PROTECT,
        null = True,
        blank = True,
    )
    notaria = models.ForeignKey( #Si es Notaria debemos saber a cual pertenece
        'notaria.Notaria',
        on_delete = models.PROTECT,
        null = True,
        blank = True,
    )
    last_password_change = models.DateField(blank=True, null=True)
    last_failed_access = models.DateTimeField(blank=True, null=True)
    last_frontend_access = models.DateTimeField(auto_now_add=True)

    failed_attempts = models.IntegerField(default=0)
    objects = UserManager()

    

    class Meta:
        unique_together = ['indicative', 'phone']

    def __str__(self):
        return f"{self.email}"

    def verification_process_mail(self):

        status = self.get_status_verified()

        email_info = {
            'subject': 'Devise - Proceso de Verificacion.',
            'template': 'verification_process',
            'to': [self.email],
            'context': {
                'user': f'{self.first_name} {self.last_name}' if self.first_name else self.email,
                'status_verification': status
            },
        }

        self.send_mail(**email_info)

    def verify_email(self):
        print('token', self.slug)
        email_info = {
            'subject': 'Devise - Confirmación de cuenta.',
            'template': 'initial_verify_email',
            'to': [self.email],
            'context': {
                'user': f'{self.first_name} {self.last_name}' if self.first_name else self.email,
                'token': f'https://devise.com/home-public/?verify_email={self.slug}'
            },
        }

        self.send_mail(**email_info)

    def send_mail(self, subject: str, to: list, template: str, context: dict) -> None:
        body = render_to_string(
            f'mail/{template}.html',
            context
        )

        email_message = EmailMessage(
            **{
                'subject': subject,
                'from_email': settings.EMAIL_FROM_DIR,
                'to': to,
                'body': body,
                'headers': {"X-MT-Category":"Sended Email"},
            }
        )

        email_message.content_subtype = 'html'
        email_message.send()

    def password_reset_mail(self, password_reset_slug:str ) -> None:
        url_password_reset_done = f'{settings.URL_PASSWORD_RESET}{password_reset_slug}'

        email_info = {
            'subject': 'Devise - Cambio de contraseña.',
            'template': 'password_reset',
            'to': [self.email],
            'context': {
                'user': f'{self.first_name} {self.last_name}' if self.first_name else self.email,
                'url_password_reset_done': url_password_reset_done,
                
            },
        }

        self.send_mail(**email_info)

    def user_has_residential_info(self):
        from apps.info_residential.models import Residentialplace
        if Residentialplace.objects.filter(user=self).exists():
            return True
        return  False
    
    def user_has_workplace_info(self):
        from apps.info_workplace.models import Workplace
        if Workplace.objects.filter(user=self).exists():
            return True
        return  False
    
    def user_has_financial_info(self):
        from apps.info_financial.models import Financial
        if Financial.objects.filter(user=self).exists():
            return True
        return  False
    
    def user_get_full_name(self):
        return f'{self.first_name} {self.last_name}'
    #Druo Dict
    def user_type_druo(self):
        if self.is_natural_person :
            return "INDIVIDUAL"
        else:
            return "ORGANIZATION"
    
    def user_organization_druo(self):
        if self.is_natural_person :
            return "NA ORGANIZATION"
        else:
            return self.first_name
    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'
    
    def get_phone_number(self):
        if self.phone:
            return self.phone
        else:
            return ''
    def get_phone_indicative(self):
        if self.indicative:
            return self.indicative
        else:
            return ''
    
    def get_address_info(self):
        from apps.info_residential.models import Residentialplace
        if Residentialplace.objects.filter(user=self).exists():
            resident_data = Residentialplace.objects.get(user=self)
            dict = {
                "address_line_1": resident_data.resident_address,
                "address_line_2": "",
                "address_line_3": "",
                "locality": resident_data.resident_region.name,
                "sublocality": resident_data.resident_city.name,
                "administrative_district": "NA",
                "postal_code": resident_data.resident_zip,
                "country": resident_data.resident_country.code3
                }
            return dict
        else:
            dict = {
                "address_line_1": "Address 1",
                "address_line_2": "Address 2",
                "address_line_3": "Address 3",
                "locality": "Locality",
                "sublocality": "Locality",
                "administrative_district": "Testing",
                "postal_code": "110110",
                "country": "COL"
                }
            return dict
    
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    user = instance
    if user.code == None:
        user.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        user.last_password_change = dt.date.today()
        user.save()
        
from apps.security.security_settings import PASSWORD_MAX_DELTA_CHANGE

class PasswordReset(base_model.BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, blank=True)
    recovery_code = models.IntegerField(blank=True,null=True)

    def get_recovery_code_str(self):
        str_recovery_code = ''
        for l in str(self.recovery_code):
            str_recovery_code += f'{l}'

        return str_recovery_code.strip()
    
    def get_is_valid_time(self):
        today = dt.datetime.now(dt.timezone.utc)
        delta = today - self.created_at
        if delta > PASSWORD_MAX_DELTA_CHANGE:
            print("Si Delta es mayor que el parametro, entonces ya vencio")
            return True
        else:
            print("Si procede el cambio")
            return False
    
@receiver(pre_save, sender=PasswordReset)
@receiver(pre_save, sender=User)
def slug_handler(sender, **kwargs):
    instance = kwargs.get('instance')

    if not instance.slug:
        for _ in range(16):
            slug = uuid.uuid4()

            if not sender.objects.filter(slug=slug).exists():
                instance.slug = slug
                return

