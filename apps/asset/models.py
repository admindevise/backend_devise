from apps.fiducia.models import Fiducia
from apps.notaria.models import Notaria
from apps.utils.models import base_model
from apps.user.models import User
from apps.sponsor_company.models import SponsorCompany
from django.core.validators import FileExtensionValidator
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.utils.translation import gettext_lazy as _

from cities_light.models import Country, Region, SubRegion


from os import path
import os


def asset_file_path(instance, filename):
    try:#in apirest is here
        folder_asset_code = 'activo_codigo_{}'.format(instance.codigo)
    except:#in back oficce is here
        folder_asset_code = 'activo_codigo_{}'.format(instance.codigo)
    return path.join('asset_docs', folder_asset_code, filename)

def asset_minuta_path(instance, filename):
    try:#in apirest is here
        folder_asset_code = 'activo_codigo_{}'.format(instance.activo.codigo)
    except:#in back oficce is here
        folder_asset_code = 'activo_codigo_{}'.format(instance.activo.codigo)
    return path.join('asset_docs', folder_asset_code, filename)

def asset_file_path_feedback(instance, filename):
    try:#in apirest is here
        folder_asset_code = 'activo_codigo_{}'.format(instance.activo.codigo)
    except:#in back oficce is here
        folder_asset_code = 'activo_codigo_{}'.format(instance.activo.codigo)
    return path.join('asset_docs', folder_asset_code, filename)

def asset_fideicomiso_file_path(instance, filename):
    try:#in apirest is here
        folder_asset_code = 'activo_codigo_{}'.format(instance.activo.codigo)
    except:#in back oficce is here
        folder_asset_code = 'activo_codigo_{}'.format(instance.activo.codigo)
    return path.join('asset_docs', folder_asset_code, filename)

class TipoProyecto(base_model.BaseModel): # Residencial comercial....
    nombre = models.CharField(max_length=126)
    imagen = models.ImageField(
        upload_to='asset/tipoproyecto/',
        blank=True,
        null=True,
        )
    color = models.CharField(max_length=16) #value on Hexadecimal
    
    def __str__(self):
        return str(self.nombre)

class Categoria(base_model.BaseModel): # Residencial comercial....
    nombre = models.CharField(max_length=126)
    imagen = models.ImageField(
        upload_to='asset/categoria/',
        blank=True,
        null=True,
        )
    color = models.CharField(max_length=16) #value on Hexadecimal
    
    def __str__(self):
        return str(self.nombre)
class EstadoAprobacion(base_model.BaseModel):
    nombre = models.CharField(max_length=125)
    paso = models.DecimalField(
        max_digits=3,  # Número máximo de dígitos, incluyendo los decimales
        decimal_places=1)
    codigo =models.CharField(max_length=125)
    color = models.CharField(max_length=125)
    
    def __str__(self):
        return str(self.nombre)
    class Meta:
        ordering = ['paso']

    def porcentaje(self):
        return int((self.paso*100)/13)

class ActivoInversion(base_model.BaseModel):
    propietario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='propietario'
    )
    codigo = models.CharField(max_length=126, unique=True)
    nombre = models.CharField(max_length=126)
    tipo_proyecto = models.ForeignKey(
        TipoProyecto,
        on_delete=models.PROTECT,
    )
    descripcion_proyecto = models.TextField(blank=True, null=True)
    dimension_m2 = models.DecimalField(max_digits=12, decimal_places=2)
    pais = models.ForeignKey(
        Country,
        on_delete = models.PROTECT,
        blank=True,
        null=True,
        )
    region = models.ForeignKey(
        Region,
        on_delete = models.PROTECT,
        blank=True,
        null=True,
        )
    ciudad = models.ForeignKey(
        SubRegion,
        on_delete = models.PROTECT,
        blank=True,
        null=True,
        )
    direccion = models.CharField(max_length=126)
    latitud = models.FloatField(blank=True, null=True)
    longitud = models.FloatField(blank=True, null=True)
    descripcion_ubicacion =  models.TextField(blank=True, null=True)
    area_construida_m2 = models.DecimalField(max_digits=12, decimal_places=2)
    area_gla_m2 = models.DecimalField(max_digits=12, decimal_places=2)
    area_vendible_m2 = models.DecimalField(max_digits=12, decimal_places=2)
    area_lote_m2 = models.DecimalField(max_digits=12, decimal_places=2)
    ano_construccion = models.IntegerField()
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        blank=True, null=True
        )
    #Segundo paso informacion legal
    matricula_inmobiliaria = models.CharField(max_length=126, blank=True, null=True)
    cedula_catastral = models.CharField(max_length=126, blank=True, null=True)
    certificado_tradicion_libertad = models.FileField(null=True, blank=True, validators=[FileExtensionValidator(['pdf'])], upload_to=asset_file_path)
    canon_arriendo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True) #VAR SMARTCONTRACT
    contrato_arriendo = models.FileField(null=True, blank=True, validators=[FileExtensionValidator(['pdf'])], upload_to=asset_file_path)
    nombre_arrendatario = models.CharField(max_length=126, blank=True, null=True)
    informacion_arrendatario = models.TextField(blank=True, null=True)
    vencimiento_contrato_arrendamiento = models.DateField(blank=True, null=True) #VAR SMARTCONTRACT
    imagen_1 = models.ImageField(blank=True, null=True, upload_to=asset_file_path)
    imagen_2 = models.ImageField(blank=True, null=True, upload_to=asset_file_path)
    imagen_3 = models.ImageField(blank=True, null=True, upload_to=asset_file_path)
    imagen_4 = models.ImageField(blank=True, null=True, upload_to=asset_file_path)
    imagen_5 = models.ImageField(blank=True, null=True, upload_to=asset_file_path)
    valor_activo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True,) #VAR SMARTCONTRACT
    sponsor = models.ForeignKey( 
        SponsorCompany,
        on_delete=models.PROTECT,
        blank=True, null=True,
        )
    fiducia = models.ForeignKey(
        Fiducia,
        on_delete=models.PROTECT,
        blank=True, null=True,
        )
    notaria = models.ForeignKey(
        Notaria,
        on_delete=models.PROTECT,
        blank=True, null=True,
        )
    #Campos que sustentan la transferencia del dominio del activo
    nuevo_certificado_tradicion_libertad = models.FileField(null=True, blank=True, validators=[FileExtensionValidator(['pdf'])], upload_to=asset_file_path)
    nueva_escritura = models.FileField(null=True, blank=True, validators=[FileExtensionValidator(['pdf'])], upload_to=asset_file_path) #VAR SMARTCONTRACT COMO CODIGO UNICO? VALIDAR
    fideicomiso_revisado = models.BooleanField(blank=True, null=True)
    #Estado del visto bueno del Sponsor
    estado_aprobacion = models.ForeignKey(
        EstadoAprobacion,
        on_delete=models.PROTECT,
        blank=True, null=True
    )
    #Una vez sea constituido el fideicomiso asume el
    gerente_negocio = models.ForeignKey( #VAR SMARTCONTRACT
        User,
        on_delete = models.PROTECT,
        blank=True,
        null=True,
        related_name='gerente_negocio'
        )
    #Campos del KPI a diligenciar por el Sponsor
    valor_token = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True) #VAR SMARTCONTRACT
    tokens_totales = models.IntegerField(blank=True, null=True)
    tokens_disponibles = models.IntegerField(blank=True, null=True) #VAR SMARTCONTRACT
    tir_ea = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True) #VAR SMARTCONTRACT
    pago_rendimiento = models.CharField(max_length=255, blank=True, null=True) #VAR SMARTCONTRACT
    tenencia_sugerida = models.CharField(max_length=255, blank=True, null=True) #VAR SMARTCONTRACT
    renta_mensual = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True) #VAR SMARTCONTRACT
    renta_por_m2 = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True) #VAR SMARTCONTRACT
    incremento_anual = models.CharField(max_length=255, blank=True, null=True) #VAR SMARTCONTRACT
    modelo_financiero = models.FileField(null=True, blank=True, validators=[FileExtensionValidator(['pdf', 'xls', 'xlsx'])], upload_to=asset_file_path)
    clase_inversion = models.CharField(max_length=255, blank=True, null=True) #VAR SMARTCONTRACT
    plazo_contrato = models.CharField(max_length=255, blank=True, null=True) #VAR SMARTCONTRACT
    teaser = models.FileField(null=True, blank=True, validators=[FileExtensionValidator(['pdf'])], upload_to=asset_file_path)
    no_id_fideicomiso = models.CharField(max_length=255, blank=True, null=True, unique=True)
    nombre_fideicomiso = models.CharField(max_length=255, blank=True, null=True, unique=True)
    inmueble_publicado = models.BooleanField(blank=True, null=True) #Solo Cambia cuando el Devise Manager aprueba
    id_smartcontract = models.CharField(max_length=255, blank=True, null=True, unique=True) #Cuando se configura en kaleido ES FIJO CUANDO SE CONFIGURA EL CONTRATO Y UNICO
    #8vo paso Documento de Cesion
    metadata_smartcontract = models.JSONField(null=True, blank=True)
    documento_cesion = models.FileField(null=True, blank=True, upload_to=asset_file_path)


    class Meta:
        permissions =[
            ("approved_activo_devise", "Puede aprobar activo para la Devise"),
            ("approved_activo_fiducia", "Puede aprobar activo para la Fiducia"),
        ]

class ActivoInversionSmartContract2(base_model.BaseModel):
    activo_inversion = models.ForeignKey(
        ActivoInversion,
        on_delete=models.CASCADE,
        related_name='activo_inversion_id'
    )
    contract_address = models.CharField(max_length=84, unique=True)
    metadata_smartcontract = models.JSONField(null=False, blank=False)
    environment_id = models.CharField(max_length=255, unique=False)
    node_id = models.CharField(max_length=255, unique=False)
    zone_domain = models.CharField(max_length=255, unique=False)
    gateway_api = models.CharField(max_length=255, unique=False)
    kld_from = models.CharField(max_length=255, unique=False)
    kld_sync = models.BooleanField(blank=True, null=True)
    


@receiver(pre_save, sender=ActivoInversion)
def create_asset_code(sender, **kwargs):
    instance = kwargs.get('instance')
    abc = ["0", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L",
           "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]

    if ActivoCode.objects.exists():
        pkey = ActivoCode.objects.latest('id').pk + 1
    else:
        pkey = 1

    if not instance.codigo: 
        
        if pkey <= 99999999:
            code = str(pkey).zfill(8)
            if len(code) < 2:
                code = code.zfill(7)
            else:
                code = code.zfill(6)
        else:
            index = pkey // 100000000
            code = str(pkey - (100000000*(pkey//100000000)))
            if len(code) < 2:
                code = code.zfill(7)
            else:
                code = code.zfill(6)
            code = abc[index] + code

        identifier_asset = str('ACT-'+code)
        instance.codigo = identifier_asset
        ActivoCode.objects.create(name=str(identifier_asset))
        return

    else:
        print("El asset ya tiene codigo")
        return

class ActivoCode(base_model.BaseModel):
    name = models.CharField(max_length=126, unique=True)

    def __str__(self):
        return str(self.pk)
# 3er paso constitucion del fideicomiso
class FeedbackActivoInversion(base_model.BaseModel):
    activo = models.ForeignKey(
        ActivoInversion,
        on_delete=models.PROTECT,
    )
    mensaje = models.TextField(blank=True, null=True)
    remitente = models.ForeignKey(
        User,
        on_delete = models.PROTECT,
        related_name='FeedbackActivoInversion_remitente'
    )
    destinatario = models.ForeignKey(
        User,
        on_delete = models.PROTECT,
        related_name='FeedbackActivoInversion_destinatario'
    )
    archivo_adjunto = models.FileField(null=True, blank=True, upload_to=asset_file_path_feedback)
    estado_actual = models.CharField(max_length=126)

    class Meta:
        ordering = ['-created_at']

    def filename(self):
        return os.path.basename(self.archivo_adjunto.name)


class Fideicomiso(base_model.BaseModel):
    activo = models.ForeignKey(
        ActivoInversion,
        on_delete=models.PROTECT,
    )
    fideicomiso = models.FileField( validators=[FileExtensionValidator(['pdf'])], upload_to=asset_fideicomiso_file_path)
    gerente_negocio = models.ForeignKey(User, on_delete=models.PROTECT)
    email_fiducia = models.EmailField(null=True, blank=True, max_length=128)
    name_fiducia = models.CharField(null=True, blank=True, max_length=128)
    aprobado_fiducia = models.BooleanField(blank=True, null=True)
    fiducia_sesion = models.CharField(null=True, blank=True, max_length=128)
    fiducia_json = models.JSONField(null=True, blank=True)
    fiducia_biometric_url = models.CharField(null=True, blank=True, max_length=512)
    fiducia_signing_url = models.CharField(null=True, blank=True, max_length=512)


    email_devise = models.EmailField(null=True, blank=True, max_length=128)
    name_devise = models.CharField(null=True, blank=True, max_length=128)
    aprobado_devise = models.BooleanField(blank=True, null=True)
    devise_sesion = models.CharField(null=True, blank=True, max_length=128)
    devise_json = models.JSONField(null=True, blank=True)
    devise_biometric_url = models.CharField(null=True, blank=True, max_length=512)
    devise_signing_url = models.CharField(null=True, blank=True, max_length=512)


    email_sponsor = models.EmailField(null=True, blank=True, max_length=128)
    name_sponsor = models.CharField(null=True, blank=True, max_length=128)
    aprobado_sponsor = models.BooleanField(blank=True, null=True)
    sponsor_sesion = models.CharField(null=True, blank=True, max_length=128)
    sponsor_json = models.JSONField(null=True, blank=True)
    sponsor_biometric_url = models.CharField(null=True, blank=True, max_length=512)
    sponsor_signing_url = models.CharField(null=True, blank=True, max_length=512)


    email_propietario = models.EmailField(null=True, blank=True, max_length=128)
    name_propietario = models.CharField(null=True, blank=True, max_length=128)
    aprobado_propietario = models.BooleanField(blank=True, null=True)
    propietario_sesion = models.CharField(null=True, blank=True, max_length=128)
    propietario_json = models.JSONField(null=True, blank=True)
    propietario_biometric_url = models.CharField(null=True, blank=True, max_length=512)
    propietario_signing_url = models.CharField(null=True, blank=True, max_length=512)


    enviado_weetrust = models.BooleanField(default=False)
    firmado_todos = models.BooleanField(default=False)
    id_weetrust_document = models.CharField(max_length=126, blank=True, null=True)
    response_weetrust = models.JSONField(null=True,blank=True)
    fideicomiso_firmado = models.FileField(null=True, blank=True, validators=[FileExtensionValidator(['pdf'])], upload_to=asset_fideicomiso_file_path)
    class Meta:
        unique_together = ('activo',)
    def __str__(self):
        return str(self.id_weetrust_document)

# 4to paso diligencio Minuta de Escrituracion


class MinutaEscrituracion(base_model.BaseModel):
    activo = models.ForeignKey(
        ActivoInversion,
        on_delete=models.PROTECT,
    )
    archivo = models.FileField(null=True, blank=True, upload_to=asset_minuta_path)
    aprobado_fiducia = models.BooleanField(blank=True, null=True)
    aprobado_notario = models.BooleanField(blank=True, null=True)
    aprobado_sponsor = models.BooleanField(blank=True, null=True)
    aprobado_propietario = models.BooleanField(blank=True, null=True)
    minuta_aprobada = models.BooleanField(blank=True, null=True)
    class Meta:
        unique_together = ('activo',)

class FeedbackMinutaEscrituracion(base_model.BaseModel):
    minuta = models.ForeignKey(
        MinutaEscrituracion,
        on_delete=models.PROTECT,
        blank=True, null=True
    )
    mensaje = models.TextField(blank=True, null=True)
    remitente = models.ForeignKey(
        User,
        on_delete = models.PROTECT,
        related_name='FeedbackMinuta_remitente',
        
    )
    destinatario = models.ForeignKey(
        User,
        on_delete = models.PROTECT,
        related_name='FeedbackMinuta_destinatario'
    )

# 6to paso diligenciando KPI del activo
class FeedbackKPI(base_model.BaseModel):
    activo = models.ForeignKey(
        ActivoInversion,
        on_delete=models.PROTECT,
    )
    mensaje = models.TextField(blank=True, null=True)
    remitente = models.ForeignKey(
        User,
        on_delete = models.PROTECT,
        related_name='FeedbackKPI_remitente'
    )
    destinatario = models.ForeignKey(
        User,
        on_delete = models.PROTECT,
        related_name='FeedbackKPI_destinatario'
    )




