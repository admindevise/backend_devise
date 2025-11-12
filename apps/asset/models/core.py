from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator
from decimal import Decimal
from apps.utils.models import base_model


def asset_file_path(instance, filename):
    """Genera la ruta para archivos del activo"""
    return f'assets/{instance.asset_code}/{filename}'


class AssetType(base_model.BaseModel):
    """Tipos de activos inmobiliarios"""
    name = models.CharField(max_length=100, verbose_name="Nombre del tipo")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    icon = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ícono")
    color = models.CharField(max_length=20, blank=True, null=True, verbose_name="Color")
    
    class Meta:
        verbose_name = "Tipo de Activo"
        verbose_name_plural = "Tipos de Activos"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Asset(base_model.BaseModel):
    """
    Modelo principal para activos inmobiliarios vinculados a fondos.
    Campos clave para la información básica del activo.
    """
    
    class AssetStatus(models.TextChoices):
        DRAFT = 'draft', 'Borrador'
        UNDER_REVIEW = 'under_review', 'En Revisión'
        APPROVED = 'approved', 'Aprobado'
        ACTIVE = 'active', 'Activo'
        SUSPENDED = 'suspended', 'Suspendido'
        SOLD = 'sold', 'Vendido'
        INACTIVE = 'inactive', 'Inactivo'
    
    # ========================================
    # RELACIONES PRINCIPALES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='assets',
        verbose_name="Fondo asociado"
    )
    
    asset_type = models.ForeignKey(
        AssetType,
        on_delete=models.PROTECT,
        related_name='assets',
        verbose_name="Tipo de activo"
    )
    
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_assets',
        verbose_name="Creado por"
    )
    
    # ========================================
    # IDENTIFICACIÓN Y DATOS BÁSICOS
    # ========================================
    asset_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Código del activo"
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre del activo"
    )
    
    description = models.TextField(
        verbose_name="Descripción del activo"
    )
    
    status = models.CharField(
        max_length=20,
        choices=AssetStatus.choices,
        default=AssetStatus.DRAFT,
        verbose_name="Estado"
    )
    
    # ========================================
    # UBICACIÓN
    # ========================================
    address = models.CharField(
        max_length=255,
        verbose_name="Dirección"
    )
    
    city = models.CharField(
        max_length=100,
        verbose_name="Ciudad"
    )
    
    state = models.CharField(
        max_length=100,
        verbose_name="Departamento/Estado"
    )
    
    country = models.CharField(
        max_length=100,
        default='Colombia',
        verbose_name="País"
    )
    
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Código postal"
    )
    
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        blank=True,
        null=True,
        verbose_name="Latitud"
    )
    
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        blank=True,
        null=True,
        verbose_name="Longitud"
    )
    
    # ========================================
    # CARACTERÍSTICAS FÍSICAS
    # ========================================
    total_area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Área total (m²)"
    )
    
    built_area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Área construida (m²)"
    )
    
    rentable_area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Área arrendable (m²)"
    )
    
    year_built = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Año de construcción"
    )
    
    # ========================================
    # INFORMACIÓN LEGAL Y REGISTRAL
    # ========================================
    property_registration = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Matrícula inmobiliaria"
    )
    
    cadastral_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Cédula catastral"
    )
    
    title_deed_document = models.FileField(
        upload_to=asset_file_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])],
        verbose_name="Escritura pública"
    )
    
    property_certificate = models.FileField(
        upload_to=asset_file_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])],
        verbose_name="Certificado de tradición y libertad"
    )
    
    # ========================================
    # VALORACIÓN DEL ACTIVO
    # ========================================
    acquisition_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Valor de adquisición (COP)"
    )
    
    current_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Valor actual de mercado (COP)"
    )
    
    acquisition_date = models.DateField(
        verbose_name="Fecha de adquisición"
    )
    
    last_appraisal_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha último avalúo"
    )
    
    appraisal_document = models.FileField(
        upload_to=asset_file_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])],
        verbose_name="Documento de avalúo"
    )
    
    # ========================================
    # INFORMACIÓN DE ARRENDAMIENTO (SI APLICA)
    # ========================================
    is_leased = models.BooleanField(
        default=False,
        verbose_name="¿Está arrendado?"
    )
    
    tenant_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nombre del arrendatario"
    )
    
    monthly_rent = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Renta mensual actual (COP)"
    )
    
    lease_start_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Inicio del contrato"
    )
    
    lease_end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fin del contrato"
    )
    
    lease_contract = models.FileField(
        upload_to=asset_file_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])],
        verbose_name="Contrato de arrendamiento"
    )
    
    # ========================================
    # IMÁGENES DEL ACTIVO
    # ========================================
    main_image = models.ImageField(
        upload_to=asset_file_path,
        blank=True,
        null=True,
        verbose_name="Imagen principal"
    )
    
    # ========================================
    # METADATOS
    # ========================================
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas adicionales"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos adicionales"
    )
    
    class Meta:
        verbose_name = "Activo Inmobiliario"
        verbose_name_plural = "Activos Inmobiliarios"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_code']),
            models.Index(fields=['fund', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.asset_code} - {self.name}"
    
    @property
    def is_active(self):
        """Verifica si el activo está activo"""
        return self.status == self.AssetStatus.ACTIVE


class AssetImage(base_model.BaseModel):
    """Imágenes adicionales del activo"""
    
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Activo"
    )
    
    image = models.ImageField(
        upload_to=asset_file_path,
        verbose_name="Imagen"
    )
    
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Título"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )
    
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Orden"
    )
    
    class Meta:
        verbose_name = "Imagen del Activo"
        verbose_name_plural = "Imágenes del Activo"
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return f"Imagen {self.order} - {self.asset.asset_code}"


