from apps.kaleido.models import Wallet, InstanceOfTokenContract721
from apps.utils.models import base_model
from apps.user.models import User

from django.db import models
from django.utils import timezone
import uuid

class Fund(models.Model):
    """
    Modelo principal para gestionar fondos de inversión
    """
    
    # ========================================
    # RELACIONES EXTERNAS
    # ========================================
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Usuario propietario"
    )
    hd_wallet = models.OneToOneField(
        Wallet, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Wallet HD"
    )
    token_contract_721 = models.OneToOneField(
        InstanceOfTokenContract721, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Contrato de Token 721"
    )
    
    # ========================================
    # INFORMACIÓN BÁSICA
    # ========================================
    name = models.CharField(
        max_length=100,
        verbose_name="Nombre del fondo"
    )
    description = models.TextField(
        verbose_name="Descripción"
    )
    description_admin = models.TextField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="Descripción administrativa"
    )
    
    # Imágenes
    image = models.ImageField(
        upload_to='funds/images/', 
        null=True, 
        blank=True,
        verbose_name="Imagen principal"
    )
    image_admin = models.ImageField(
        upload_to='funds/images/', 
        null=True, 
        blank=True,
        verbose_name="Imagen administrativa"
    )
    
    # Estado y fechas
    STATUS_CHOICES = (
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
    )
    status = models.CharField(
        choices=STATUS_CHOICES, 
        max_length=10, 
        default='active',
        verbose_name="Estado"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    
    # ========================================
    # CONFIGURACIÓN DE TOKENS Y UNIDADES
    # ========================================
    amount_units = models.PositiveIntegerField(
        default=0, 
        help_text="Cantidad de unidades del fondo",
        verbose_name="Cantidad de unidades"
    )
    amount_tokens = models.PositiveIntegerField(
        default=0, 
        help_text="Cantidad de tokens del fondo",
        verbose_name="Cantidad de tokens"
    )
    nickname_tokens = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Nombre de los tokens"
    )
    secret = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        verbose_name="Clave secreta"
    )
    
    # ========================================
    # PARÁMETROS FINANCIEROS - PRECIOS
    # ========================================
    price_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Precio por unidad actual"
    )
    initial_unit_value = models.DecimalField(
        max_digits=14, 
        decimal_places=4, 
        blank=True, 
        null=True,
        verbose_name="Valor inicial por unidad"
    )
    
    # ========================================
    # PARÁMETROS FINANCIEROS - RENDIMIENTOS
    # ========================================
    current_annual_yield = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Rendimiento anualizado porcentual",
        verbose_name="Rendimiento anual actual (%)"
    )
    current_return_rate = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Porcentaje de rendimiento actual",
        verbose_name="Tasa de retorno actual (%)"
    )
    expected_return = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Porcentaje de rentabilidad esperada",
        verbose_name="Retorno esperado (%)"
    )
    tir = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Tasa Interna de Retorno porcentual",
        verbose_name="TIR (%)"
    )
    
    # ========================================
    # PARÁMETROS FINANCIEROS - ACTIVOS Y COMISIONES
    # ========================================
    total_assets = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Activos totales"
    )
    management_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Porcentaje de comisión de administración",
        verbose_name="Comisión de administración (%)"
    )
    success_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Porcentaje de comisión por desempeño",
        verbose_name="Comisión de éxito (%)"
    )
    
    # ========================================
    # INFORMACIÓN REGULATORIA
    # ========================================
    superintendency_registry = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Número de registro en Superintendencia Financiera",
        verbose_name="Registro superintendencia"
    )
    tax_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        help_text="Número de identificación tributaria",
        verbose_name="NIT"
    )
    risk_rating = models.CharField(
        max_length=10, 
        blank=True, 
        null=True, 
        help_text="Ej.: AAA, AA+, BBB, etc.",
        verbose_name="Calificación de riesgo"
    )
    
    # ========================================
    # CLASIFICACIÓN DEL FONDO
    # ========================================
    FUND_TYPE_CHOICES = (
        ('real_estate', 'Fondo Inmobiliario'),
        ('securities', 'Fondo de Valores'),
        ('private_equity', 'Capital Privado'),
        ('pension', 'Pensión Voluntaria'),
        ('other', 'Otro'),
    )
    fund_type = models.CharField(
        choices=FUND_TYPE_CHOICES, 
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Tipo de fondo"
    )
    management_company = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Compañía administradora"
    )
    
    # ========================================
    # POLÍTICAS DE INVERSIÓN
    # ========================================
    RISK_PROFILE_CHOICES = (
        ('conservative', 'Conservador'),
        ('moderate', 'Moderado'),
        ('aggressive', 'Agresivo'),
    )
    risk_profile = models.CharField(
        choices=RISK_PROFILE_CHOICES, 
        max_length=15, 
        blank=True, 
        null=True,
        verbose_name="Perfil de riesgo"
    )
    investment_horizon = models.PositiveSmallIntegerField(
        blank=True, 
        null=True, 
        help_text="Tiempo recomendado en años",
        verbose_name="Horizonte de inversión (años)"
    )
    suggested_trend = models.PositiveSmallIntegerField(
        blank=True, 
        null=True, 
        help_text="Tiempo sugerido para mantener la inversión en años",
        verbose_name="Tendencia sugerida (años)"
    )
    asset_composition = models.JSONField(
        blank=True, 
        null=True, 
        help_text="Distribución porcentual por tipo de activo",
        verbose_name="Composición de activos"
    )
    
    # ========================================
    # POLÍTICAS DE DIVIDENDOS
    # ========================================
    DIVIDEND_DISTRIBUTION_CHOICES = (
        ('automatic_reinvestment', 'Reinversión Automática'),
        ('periodic_distribution', 'Distribución Periódica'),
        ('mixed', 'Mixto'),
    )
    dividend_distribution = models.CharField(
        choices=DIVIDEND_DISTRIBUTION_CHOICES, 
        max_length=25, 
        blank=True, 
        null=True,
        verbose_name="Distribución de dividendos"
    )
    
    PERFORMANCE_PAYMENT_FREQUENCY_CHOICES = (
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('semi_annually', 'Semestral'),
        ('annually', 'Anual'),
    )
    performance_payment_frequency = models.CharField(
        choices=PERFORMANCE_PAYMENT_FREQUENCY_CHOICES,
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Frecuencia de pago de rendimientos"
    )
    
    # ========================================
    # PARÁMETROS OPERACIONALES
    # ========================================
    minimum_investment = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Inversión mínima"
    )
    permanence_period = models.PositiveSmallIntegerField(
        blank=True, 
        null=True, 
        help_text="Tiempo mínimo en días",
        verbose_name="Período de permanencia (días)"
    )
    early_withdrawal_penalty = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Porcentaje de penalización por retiro anticipado",
        verbose_name="Penalización retiro anticipado (%)"
    )
    trading_hours = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Ej.: 8:00 a.m. - 1:00 p.m.",
        verbose_name="Horario de operaciones"
    )
    operations_start_date = models.DateField(
        blank=True, 
        null=True,
        verbose_name="Fecha de inicio de operaciones"
    )
    operations_closing_date = models.DateField(
        blank=True, 
        null=True,
        verbose_name="Fecha de cierre de operaciones"
    )
    
    # ========================================
    # GESTIÓN Y ADMINISTRACIÓN
    # ========================================
    main_manager = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Gerente principal"
    )
    description_main_manager = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Descripción del gerente principal"
    )
    
    # ========================================
    # DOCUMENTOS Y POLÍTICAS
    # ========================================
    terms_and_conditions = models.FileField(
        upload_to='funds/terms/', 
        blank=True, 
        null=True, 
        help_text="Documento de términos y condiciones",
        verbose_name="Términos y condiciones"
    )
    data_processing_policy = models.FileField(
        upload_to='funds/policies/', 
        blank=True, 
        null=True, 
        help_text="Documento de política de tratamiento de datos",
        verbose_name="Política de tratamiento de datos"
    )
    accountability = models.FileField(
        upload_to='funds/accountability/', 
        blank=True, 
        null=True, 
        help_text="Documento de rendición de cuentas",
        verbose_name="Rendición de cuentas"
    )
    tax_certificate = models.FileField(
        upload_to='funds/tax_certificates/', 
        blank=True, 
        null=True, 
        help_text="Documento de certificado tributario",
        verbose_name="Certificado tributario"
    )
    operator_report = models.FileField(
        upload_to='funds/reports/', 
        blank=True, 
        null=True, 
        help_text="Reporte del operador",
        verbose_name="Reporte del operador"
    )
    
    # ========================================
    # META CONFIGURACIÓN
    # ========================================
    class Meta:
        verbose_name = "Fondo de Inversión"
        verbose_name_plural = "Fondos de Inversión"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'fund_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['name']),
        ]
    
    # ========================================
    # MÉTODOS ESPECIALES
    # ========================================
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    # ========================================
    # PROPIEDADES
    # ========================================
    @property
    def wallet_id(self):
        """ID de la wallet asociada"""
        return self.hd_wallet.id_wallet if self.hd_wallet else None
    
    @property
    def contract_address(self):
        """Dirección del contrato de token"""
        return self.token_contract_721.contract_address if self.token_contract_721 else None
    
    @property
    def amount_total(self):
        """Monto total del fondo (cantidad × precio por unidad)"""
        return self.amount_units * self.price_per_unit if self.price_per_unit else 0
    
    @property
    def current_price(self):
        """Precio actual desde el historial (más reciente)"""
        latest_price = self.price_history.first()  # Ordenado por -effective_date
        return latest_price.price_per_unit if latest_price else self.price_per_unit
    
    @property
    def total_investors(self):
        """Número total de inversores únicos en este fondo"""
        return self.investments.values('investor').distinct().count()
    
    # ========================================
    # MÉTODOS DE GESTIÓN DE PRECIOS
    # ========================================
    def update_price(self, new_price, user=None, notes=None, effective_date=None):
        """
        Actualiza el precio del fondo y guarda el cambio en el historial
        
        Args:
            new_price (Decimal): Nuevo precio por unidad
            user (User, optional): Usuario que realiza el cambio
            notes (str, optional): Notas sobre el cambio
            effective_date (datetime, optional): Fecha efectiva del cambio
            
        Returns:
            Decimal: El nuevo precio actualizado
        """
        # Guardar valor actual en el historial
        FundPriceHistory.objects.create(
            fund=self,
            price_per_unit=new_price,
            effective_date=effective_date or timezone.now(),
            created_by=user,
            notes=notes
        )
        
        # Actualizar el precio actual del fondo
        self.price_per_unit = new_price
        self.save(update_fields=['price_per_unit'])
        
        return self.price_per_unit
    
    def get_price_at(self, date):
        """
        Obtiene el precio del fondo en una fecha específica
        
        Args:
            date (datetime): Fecha para consultar el precio
            
        Returns:
            Decimal or None: Precio en la fecha especificada
        """
        price = self.price_history.filter(
            effective_date__lte=date
        ).order_by('-effective_date').first()
        
        return price.price_per_unit if price else None
    
    def get_price_history(self, start_date=None, end_date=None):
        """
        Obtiene el historial de precios en un rango de fechas
        
        Args:
            start_date (datetime, optional): Fecha de inicio
            end_date (datetime, optional): Fecha de fin
            
        Returns:
            QuerySet: Historial de precios filtrado
        """
        queryset = self.price_history.all()
        
        if start_date:
            queryset = queryset.filter(effective_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(effective_date__lte=end_date)
            
        return queryset
    
    # ========================================
    # MÉTODOS DE CÁLCULO DE RENDIMIENTOS
    # ========================================
    def calculate_total_return(self, from_date=None, to_date=None):
        """
        Calcula el rendimiento total del fondo en un período
        
        Args:
            from_date (datetime, optional): Fecha de inicio del cálculo
            to_date (datetime, optional): Fecha de fin del cálculo
            
        Returns:
            dict: Diccionario con información de rendimientos
        """
        to_date = to_date or timezone.now()
        from_date = from_date or self.operations_start_date or self.created_at
        
        initial_price = self.get_price_at(from_date) or self.initial_unit_value
        current_price = self.get_price_at(to_date) or self.current_price
        
        if not initial_price or not current_price:
            return {
                'total_return': 0,
                'percentage_return': 0,
                'error': 'Precios no disponibles para el cálculo'
            }
        
        total_return = current_price - initial_price
        percentage_return = (total_return / initial_price) * 100 if initial_price > 0 else 0
        
        return {
            'initial_price': initial_price,
            'current_price': current_price,
            'total_return': total_return,
            'percentage_return': percentage_return,
            'period_days': (to_date.date() - from_date.date()).days,
            'from_date': from_date,
            'to_date': to_date
        }
    
    # ========================================
    # MÉTODOS DE VALIDACIÓN
    # ========================================
    def clean(self):
        """Validaciones personalizadas del modelo"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # Validar que el precio por unidad sea positivo
        if self.price_per_unit and self.price_per_unit <= 0:
            errors['price_per_unit'] = 'El precio por unidad debe ser mayor a cero'
        
        # Validar que la inversión mínima sea positiva
        if self.minimum_investment and self.minimum_investment <= 0:
            errors['minimum_investment'] = 'La inversión mínima debe ser mayor a cero'
        
        # Validar fechas
        if (self.operations_start_date and self.operations_closing_date and 
            self.operations_start_date >= self.operations_closing_date):
            errors['operations_closing_date'] = 'La fecha de cierre debe ser posterior a la fecha de inicio'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override del método save para validaciones adicionales"""
        self.clean()
        super().save(*args, **kwargs)


class FundApplication(models.Model):
    """
    Modelo para manejar las solicitudes de ingreso a fondos y el proceso de verificación.
    Responsabilidad: Gestionar el proceso de aplicación y verificación inicial.
    """
    
    class ApplicationStatus(models.TextChoices):
        """Enum para estados de la aplicación usando TextChoices (Django 3.0+)"""
        PENDING = 'pending', 'Solicitud Pendiente'
        UNDER_REVIEW = 'under_review', 'En Revisión'
        APPROVED = 'approved', 'Aprobada'
        REJECTED = 'rejected', 'Rechazada'
        CANCELLED = 'cancelled', 'Cancelada'
    
    # ========================================
    # RELACIONES
    # ========================================
    fund = models.ForeignKey(
        Fund, 
        on_delete=models.CASCADE, 
        related_name="applications",
        verbose_name="Fondo"
    )
    applicant = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="fund_applications",
        verbose_name="Solicitante"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_applications",
        verbose_name="Revisado por"
    )
    
    # ========================================
    # INFORMACIÓN FINANCIERA DE LA SOLICITUD
    # ========================================
    requested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Monto solicitado",
        help_text="Monto que el solicitante desea invertir"
    )
    
    requested_units = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Unidades solicitadas",
        help_text="Número específico de unidades que desea adquirir"
    )
    
    maximum_acceptable_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio máximo aceptable por unidad",
        help_text="Precio máximo que está dispuesto a pagar por unidad"
    )
    
    preferred_payment_method = models.CharField(
        max_length=30,
        choices=[
            ('bank_transfer', 'Transferencia Bancaria'),
            ('credit_card', 'Tarjeta de Crédito'),
            ('debit_card', 'Tarjeta Débito'),
            ('check', 'Cheque'),
            ('crypto', 'Criptomonedas'),
            ('other', 'Otro'),
        ],
        null=True,
        blank=True,
        verbose_name="Método de pago preferido"
    )
    
    # ========================================
    # PERFIL DE INVERSIÓN
    # ========================================
    investment_objective = models.CharField(
        max_length=30,
        choices=[
            ('capital_growth', 'Crecimiento de Capital'),
            ('income_generation', 'Generación de Ingresos'),
            ('capital_preservation', 'Preservación de Capital'),
            ('retirement', 'Jubilación'),
            ('education', 'Educación'),
            ('other', 'Otro'),
        ],
        null=True,
        blank=True,
        verbose_name="Objetivo de inversión"
    )
    
    risk_tolerance = models.CharField(
        max_length=15,
        choices=[
            ('low', 'Bajo'),
            ('medium', 'Medio'),
            ('high', 'Alto'),
        ],
        null=True,
        blank=True,
        verbose_name="Tolerancia al riesgo"
    )
    
    investment_experience = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Principiante'),
            ('intermediate', 'Intermedio'),
            ('advanced', 'Avanzado'),
            ('professional', 'Profesional'),
        ],
        null=True,
        blank=True,
        verbose_name="Experiencia en inversión"
    )
    
    planned_investment_horizon = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Horizonte de inversión planeado (años)",
        help_text="Tiempo que planea mantener la inversión"
    )
    
    # ========================================
    # DECLARACIONES Y CONFIRMACIONES
    # ========================================
    accepts_terms_and_conditions = models.BooleanField(
        default=False,
        verbose_name="Acepta términos y condiciones"
    )
    
    accepts_risk_disclosure = models.BooleanField(
        default=False,
        verbose_name="Acepta declaración de riesgos"
    )
    
    confirms_information_accuracy = models.BooleanField(
        default=False,
        verbose_name="Confirma veracidad de la información"
    )
    
    authorizes_background_check = models.BooleanField(
        default=False,
        verbose_name="Autoriza verificación de antecedentes"
    )
    
    # ========================================
    # INFORMACIÓN ADICIONAL
    # ========================================
    source_of_funds = models.CharField(
        max_length=30,
        choices=[
            ('salary', 'Salario'),
            ('business_income', 'Ingresos de Negocio'),
            ('investments', 'Inversiones'),
            ('inheritance', 'Herencia'),
            ('loan', 'Préstamo'),
            ('savings', 'Ahorros'),
            ('other', 'Otro'),
        ],
        null=True,
        blank=True,
        verbose_name="Fuente de los fondos"
    )
    
    is_politically_exposed = models.BooleanField(
        default=False,
        verbose_name="¿Es persona políticamente expuesta?",
        help_text="PEP - Persona Expuesta Políticamente"
    )
    
    referral_source = models.CharField(
        max_length=30,
        choices=[
            ('website', 'Sitio Web'),
            ('social_media', 'Redes Sociales'),
            ('referral', 'Referido'),
            ('advisor', 'Asesor Financiero'),
            ('advertisement', 'Publicidad'),
            ('event', 'Evento'),
            ('other', 'Otro'),
        ],
        null=True,
        blank=True,
        verbose_name="¿Cómo se enteró del fondo?"
    )
    
    special_instructions = models.TextField(
        blank=True,
        null=True,
        verbose_name="Instrucciones especiales",
        help_text="Cualquier instrucción o requerimiento especial"
    )
    
    # ========================================
    # FECHAS Y ESTADO
    # ========================================
    status = models.CharField(
        max_length=15,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        verbose_name="Estado"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de solicitud")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    reviewed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de revisión"
    )
    
    # ========================================
    # NOTAS Y OBSERVACIONES 
    # ========================================
    applicant_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas del solicitante",
        help_text="Información adicional proporcionada por el solicitante"
    )
    review_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas de revisión",
        help_text="Observaciones del proceso de revisión"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de rechazo"
    )
    
    # ========================================
    # METADATOS
    # ========================================
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP de solicitud"
    )
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name="User Agent del navegador"
    )
    
    application_version = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Versión de la aplicación",
        help_text="Versión del formulario usado"
    )
    
    @property
    def is_approved(self) -> bool:
        """Verifica si la aplicación está aprobada."""
        return self.status == self.ApplicationStatus.APPROVED
    
    @property
    def can_proceed_to_investment(self) -> bool:
        """Verifica si puede proceder al proceso de inversión."""
        return self.is_approved

    class Meta:
        unique_together = ('fund', 'applicant')
        ordering = ['-created_at']
        verbose_name = "Solicitud de Fondo"
        verbose_name_plural = "Solicitudes de Fondos"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['fund', 'status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.applicant.email} → {self.fund.name} ({self.get_status_display()})"
    

class FundInvestment(models.Model):
    """
    Modelo para manejar las inversiones activas en fondos.
    Responsabilidad: Gestionar el proceso de compra de tokens e inversión final.
    """
    
    class InvestmentStatus(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', 'Pago Pendiente'
        PAYMENT_VERIFIED = 'payment_verified', 'Pago Verificado'
        ACTIVE = 'active', 'Activa'
        SUSPENDED = 'suspended', 'Suspendida'
        MATURE = 'mature', 'Vencida'
        PARTIAL_REDEMPTION = 'partial_redemption', 'Redención Parcial'
        FULL_REDEMPTION = 'full_redemption', 'Redención Total'
        CANCELLED = 'cancelled', 'Cancelada'
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PARTIAL = 'partial', 'Parcial'
        COMPLETED = 'completed', 'Completado'
        FAILED = 'failed', 'Fallido'
        REFUNDED = 'refunded', 'Reembolsado'
    
    # ========================================
    # RELACIONES
    # ========================================
    application = models.OneToOneField(
        FundApplication,
        on_delete=models.CASCADE,
        related_name="investment",
        verbose_name="Solicitud asociada",
        null=True,
        blank=True
    )
    fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        related_name="investments",
        verbose_name="Fondo"
    )
    investor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="fund_investments",
        verbose_name="Inversor"
    )
    
    # ========================================
    # INFORMACIÓN FINANCIERA PRINCIPAL
    # ========================================
    invested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Monto invertido",
        help_text="Monto realmente invertido confirmado"
    )
    
    units_owned = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        verbose_name="Unidades poseídas",
        help_text="Número de unidades del fondo que posee"
    )
    
    purchase_price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Precio de compra por unidad",
        help_text="Precio al cual compró las unidades"
    )
    
    current_unit_value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Valor actual por unidad",
        help_text="Precio actual de mercado por unidad"
    )
    
    # ========================================
    # RENDIMIENTOS Y GANANCIAS
    # ========================================
    total_dividends_received = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Total dividendos recibidos",
        help_text="Suma total de dividendos recibidos históricamente"
    )
    
    pending_dividends = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Dividendos pendientes",
        help_text="Dividendos declarados pero no pagados"
    )
    
    realized_capital_gains = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Ganancias de capital realizadas",
        help_text="Ganancias por ventas parciales ya realizadas"
    )
    
    unrealized_capital_gains = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Ganancias de capital no realizadas",
        help_text="Ganancias en papel basadas en precio actual"
    )
    
    accrued_interest = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Intereses acumulados",
        help_text="Intereses devengados pero no pagados"
    )
    
    performance_fees_paid = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Comisiones de performance pagadas",
        help_text="Total de comisiones por desempeño pagadas"
    )
    
    management_fees_paid = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Comisiones de administración pagadas",
        help_text="Total de comisiones de administración pagadas"
    )
    
    # ========================================
    # INFORMACIÓN DE PAGO
    # ========================================
    payment_status = models.CharField(
        max_length=15,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="Estado del pago"
    )
    
    payment_method = models.CharField(
        max_length=30,
        choices=[
            ('bank_transfer', 'Transferencia Bancaria'),
            ('credit_card', 'Tarjeta de Crédito'),
            ('debit_card', 'Tarjeta Débito'),
            ('check', 'Cheque'),
            ('wire_transfer', 'Transferencia Internacional'),
            ('crypto', 'Criptomonedas'),
            ('ach', 'ACH'),
            ('cash', 'Efectivo'),
            ('other', 'Otro'),
        ],
        null=True,
        blank=True,
        verbose_name="Método de pago utilizado"
    )
    
    payment_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Referencia de pago",
        help_text="Número de transacción, cheque, etc."
    )
    
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de pago confirmado"
    )
    
    # ========================================
    # FECHAS IMPORTANTES
    # ========================================
    status = models.CharField(
        max_length=25,
        choices=InvestmentStatus.choices,
        default=InvestmentStatus.PENDING_PAYMENT,
        verbose_name="Estado"
    )
    
    investment_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de inicio de inversión",
        help_text="Fecha cuando la inversión se activa oficialmente"
    )
    
    maturity_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento",
        help_text="Fecha de vencimiento del período de permanencia"
    )
    
    last_valuation_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última fecha de valoración",
        help_text="Última vez que se calculó el valor de la inversión"
    )
    
    last_dividend_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Última fecha de dividendo",
        help_text="Última vez que recibió dividendos"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Última actualización"
    )
    
    # ========================================
    # CONFIGURACIONES DE INVERSIÓN
    # ========================================
    auto_reinvest_dividends = models.BooleanField(
        default=True,
        verbose_name="Reinversión automática de dividendos",
        help_text="Si los dividendos se reinvierten automáticamente"
    )
    
    dividend_payment_preference = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Efectivo'),
            ('reinvest', 'Reinversión'),
            ('mixed', 'Mixto'),
        ],
        default='reinvest',
        verbose_name="Preferencia de pago de dividendos"
    )
    
    tax_withholding_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Porcentaje de retención fiscal (%)",
        help_text="Porcentaje de impuestos retenidos automáticamente"
    )
    
    # ========================================
    # ACEPTACIONES Y CONFIRMACIONES DE INVERSIÓN
    # ========================================
    accepts_terms_and_conditions = models.BooleanField(
        default=False,
        verbose_name="Acepta términos y condiciones de la inversión",
        help_text="Confirmación específica para esta inversión"
    )
    
    accepts_risk_disclosure = models.BooleanField(
        default=False,
        verbose_name="Acepta declaración de riesgos de la inversión",
        help_text="Confirmación específica de riesgos para esta inversión"
    )
    
    # ========================================
    # INFORMACIÓN BANCARIA PARA PAGOS
    # ========================================
    bank_account_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Número de cuenta bancaria",
        help_text="Para pagos de dividendos y redenciones"
    )
    
    bank_routing_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Código de enrutamiento bancario"
    )
    
    bank_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Nombre del banco"
    )
    
    # ========================================
    # DOCUMENTACIÓN
    # ========================================
    investment_agreement = models.FileField(
        upload_to='investments/agreements/',
        null=True,
        blank=True,
        verbose_name="Contrato de inversión firmado"
    )
    
    payment_receipt = models.FileField(
        upload_to='investments/receipts/',
        null=True,
        blank=True,
        verbose_name="Comprobante de pago"
    )
    
    tax_documents = models.FileField(
        upload_to='investments/tax/',
        null=True,
        blank=True,
        verbose_name="Documentos fiscales"
    )
    
    # ========================================
    # NOTAS Y OBSERVACIONES
    # ========================================
    investment_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas de la inversión",
        help_text="Observaciones específicas de esta inversión"
    )
    
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de cancelación"
    )
    
    suspension_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de suspensión"
    )
    
    # ========================================
    # METADATOS DE AUDITORÍA
    # ========================================
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_investments",
        verbose_name="Creado por"
    )
    
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="modified_investments",
        verbose_name="Última modificación por"
    )
    
    audit_trail = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Historial de cambios",
        help_text="Log de cambios importantes en la inversión"
    )
    
    # ========================================
    # PROPIEDADES CALCULADAS
    # ========================================
    @property
    def current_investment_value(self):
        """Valor actual total de la inversión"""
        if self.units_owned and self.current_unit_value:
            return self.units_owned * self.current_unit_value
        return self.invested_amount
    
    @property
    def total_return_amount(self):
        """Rendimiento total en pesos (realizado + no realizado + dividendos)"""
        return (
            self.realized_capital_gains + 
            self.unrealized_capital_gains + 
            self.total_dividends_received
        )
    
    @property
    def total_return_percentage(self):
        """Porcentaje total de rendimiento"""
        if self.invested_amount > 0:
            return float((self.total_return_amount / self.invested_amount) * 100)
        return 0.0
    
    @property
    def annualized_return(self):
        """Rendimiento anualizado desde la inversión inicial"""
        if not self.investment_start_date or self.invested_amount <= 0:
            return 0.0
        
        from datetime import date
        from decimal import Decimal
        
        days_invested = (date.today() - self.investment_start_date).days
        if days_invested <= 0:
            return 0.0
        
        total_return_ratio = float(self.total_return_amount / self.invested_amount)
        years_invested = days_invested / 365.25
        
        if years_invested <= 0:
            return 0.0
        
        # Fórmula: (1 + total_return)^(1/años) - 1
        annualized = ((1 + total_return_ratio) ** (1 / years_invested)) - 1
        return annualized * 100
    
    @property
    def dividend_yield(self):
        """Rendimiento por dividendos sobre la inversión inicial"""
        if self.invested_amount > 0:
            return float((self.total_dividends_received / self.invested_amount) * 100)
        return 0.0
    
    @property
    def unrealized_gain_loss(self):
        """Ganancia/pérdida no realizada actual"""
        current_value = self.current_investment_value
        return current_value - self.invested_amount
    
    @property
    def can_redeem(self):
        """Verifica si puede solicitar redención"""
        if not self.maturity_date:
            return True
        
        from datetime import date
        return date.today() >= self.maturity_date
    
    @property
    def is_active(self):
        """Verifica si la inversión está activa"""
        return self.status == self.InvestmentStatus.ACTIVE
    
    @property
    def days_until_maturity(self):
        """Días hasta el vencimiento"""
        if not self.maturity_date:
            return None
        
        from datetime import date
        delta = self.maturity_date - date.today()
        return max(0, delta.days)
    
    # ========================================
    # MÉTODOS DE NEGOCIO
    # ========================================
    def calculate_current_value(self):
        """Recalcula el valor actual basado en el precio del fondo"""
        if self.units_owned and self.fund.price_per_unit:
            self.current_unit_value = self.fund.price_per_unit
            self.unrealized_capital_gains = (
                (self.current_unit_value - self.purchase_price_per_unit) * 
                self.units_owned
            )
            self.last_valuation_date = timezone.now()
            self.save(update_fields=[
                'current_unit_value', 
                'unrealized_capital_gains', 
                'last_valuation_date'
            ])
    
    def record_dividend_payment(self, amount, payment_date=None):
        """Registra un pago de dividendos"""
        from decimal import Decimal
        
        self.total_dividends_received += Decimal(str(amount))
        self.last_dividend_date = payment_date or timezone.now().date()
        
        # Registrar en audit trail
        self.audit_trail.append({
            'action': 'dividend_payment',
            'amount': str(amount),
            'date': str(self.last_dividend_date),
            'timestamp': timezone.now().isoformat()
        })
        
        self.save(update_fields=[
            'total_dividends_received', 
            'last_dividend_date', 
            'audit_trail'
        ])
    
    def record_fee_payment(self, fee_type, amount):
        """Registra el pago de comisiones"""
        from decimal import Decimal
        
        amount_decimal = Decimal(str(amount))
        
        if fee_type == 'management':
            self.management_fees_paid += amount_decimal
        elif fee_type == 'performance':
            self.performance_fees_paid += amount_decimal
        
        # Registrar en audit trail
        self.audit_trail.append({
            'action': f'{fee_type}_fee_payment',
            'amount': str(amount),
            'timestamp': timezone.now().isoformat()
        })
        
        self.save()
    
    def calculate_maturity_date(self):
        """Calcula la fecha de vencimiento basada en el período de permanencia"""
        if self.investment_start_date and self.fund.permanence_period:
            from datetime import timedelta
            self.maturity_date = (
                self.investment_start_date + 
                timedelta(days=self.fund.permanence_period)
            )
            self.save(update_fields=['maturity_date'])
    
    # ========================================
    # VALIDACIONES
    # ========================================
    def clean(self):
        """Validaciones personalizadas"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # Validar que el monto invertido sea positivo
        if self.invested_amount <= 0:
            errors['invested_amount'] = 'El monto invertido debe ser mayor a cero'
        
        # Validar consistencia entre unidades y monto
        if (self.units_owned and self.purchase_price_per_unit and 
            self.invested_amount):
            calculated_amount = self.units_owned * self.purchase_price_per_unit
            if abs(calculated_amount - self.invested_amount) > 1:
                errors['units_owned'] = 'Las unidades no coinciden con el monto invertido'
        
        # Validar fechas
        if (self.investment_start_date and self.maturity_date and 
            self.investment_start_date >= self.maturity_date):
            errors['maturity_date'] = 'La fecha de vencimiento debe ser posterior al inicio'
        
        if errors:
            raise ValidationError(errors)
    
    # ========================================
    # META CONFIGURACIÓN
    # ========================================
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Inversión en Fondo"
        verbose_name_plural = "Inversiones en Fondos"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['fund', 'investor']),
            models.Index(fields=['investor', 'status']),
            models.Index(fields=['investment_start_date']),
            models.Index(fields=['maturity_date']),
            models.Index(fields=['payment_status']),
        ]
        unique_together = [('fund', 'investor', 'created_at')]
    
    def __str__(self):
        return f"{self.investor.email} → {self.fund.name} (${self.invested_amount})"
    
    
class FundPriceHistory(base_model.BaseModel):
    """
    Modelo para almacenar el historial de precios por unidad de los fondos.
    """
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='price_history')
    price_per_unit = models.DecimalField(max_digits=14, decimal_places=4)
    effective_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    notes = models.TextField(blank=True, null=True, help_text="Razón para el cambio de precio")
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Historial de Precio de Fondo"
        verbose_name_plural = "Historial de Precios de Fondos"
        
    def __str__(self):
        return f"{self.fund.name}: {self.price_per_unit} ({self.effective_date.strftime('%Y-%m-%d %H:%M')})"


class FundToken(base_model.BaseModel):
    """
    Modelo para almacenar los tokens asociados a un fondo.
    """
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='tokens')
    fund_investment = models.ForeignKey(
        FundInvestment,
        on_delete=models.CASCADE,
        related_name='tokens',
        null=True,
        blank=True,
        verbose_name="Inversión asociada",
        help_text="Inversión específica a la que pertenece este token"
    )
    
    token_id = models.CharField(max_length=255)
    nickname = models.CharField(max_length=255, blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    owner_user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name="owned_tokens")
    
    available_for_trading = models.BooleanField(default=False)
    reserved_for_sale = models.BooleanField(default=False)
    reserved_at = models.DateTimeField(null=True, blank=True)
    reservation_expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Token de Fondo"
        verbose_name_plural = "Tokens de Fondos"
        unique_together = ('fund', 'token_id')
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Token {self.token_id} del fondo {self.fund.name}"
    
    
class TokenTransaction(base_model.BaseModel):
    """
    Modelo para registrar todos los movimientos de tokens a nivel global
    """
    
    class TransactionStatus(models.TextChoices):
        COMPLETED = 'COMPLETED', 'Completada'
        PENDING = 'PENDING', 'Pendiente'
        FAILED = 'FAILED', 'Fallida'
    
    class TransactionTypes(models.TextChoices):
        MINT = 'MINTED', 'Creación de Token'
        BURN = 'BURNED', 'Quema de Token'
        TRANSFER = 'TRANSFER', 'Transferencia de Token'
        PURCHASE = 'PURCHASE', 'Compra de Token'
        SALE = 'SOLD', 'Venta de Token'
        INDEX_TRANSFER = 'INDEX_TRANSFER', 'Transferencia Index-to-Index'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Información del token
    fund = models.ForeignKey(Fund, on_delete=models.PROTECT, related_name='token_transactions')
    token = models.ForeignKey(FundToken, on_delete=models.PROTECT, related_name='transactions')
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionTypes.choices,
        default=TransactionTypes.TRANSFER,)
    
    # Participantes
    from_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='token_transactions_sent', null=True, blank=True)
    to_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='token_transactions_received', null=True, blank=True)
    
    # Detalles de la transacción
    kaleido_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount = models.IntegerField(default=0, help_text="Cantidad de tokens involucrados en la transacción")
    
    # Relación con trading (si aplica)
    trading_transaction = models.ForeignKey('trading.Transaction', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Estado y metadatos
    status = models.CharField(
        max_length=20, 
        choices=TransactionStatus.choices, 
        default=TransactionStatus.COMPLETED)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transacción de Token"
        verbose_name_plural = "Transacciones de Tokens"