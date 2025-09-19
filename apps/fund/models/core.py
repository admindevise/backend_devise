from django.db import models
from django.utils import timezone

from apps.user.models import User
from apps.kaleido.models import Wallet, InstanceOfTokenContract721

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
    
    financial_institution = models.ForeignKey(
        'financial_institution.FinancialInstitution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Institución financiera"
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
    evolution_description = models.TextField(
        max_length=500,
        blank=True, 
        null=True,
        verbose_name="Evolución del fondo"
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

class FundSemestralDocument(models.Model):
    """
    Modelo para manejar documentos semestrales asociados a un fondo
    """
    
    class DocumentType(models.TextChoices):
        ACCOUNTTABILITY = 'accountability', 'Rendición de cuentas'
        TAX_CERTIFICATE = 'tax_certificate', 'Certificado tributario'
        OPERATOR_REPORT = 'operator_report', 'Reporte del operador'
    
    fund = models.ForeignKey(
        Fund, 
        on_delete=models.CASCADE, 
        related_name="semestral_documents",
        verbose_name="Fondo"
    )
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        verbose_name="Tipo de documento"
    )
    
    # Información temporal
    year = models.PositiveSmallIntegerField(
        verbose_name="Año del documento"
    )
    semester = models.PositiveSmallIntegerField(
        choices=[(1, 'Primer semestre'), (2, 'Segundo semestre')],
        verbose_name="Semestre del documento"
    )
    
    # Documento y metadatos
    document = models.FileField(
        upload_to='funds/semestral_documents/', 
        verbose_name="Documento semestral"
    )
    title = models.CharField(
        max_length=255, 
        verbose_name="Título del documento"
    )
    description = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Descripción del documento"
    )
    
    # Fechas
    period_start_date = models.DateField(
        verbose_name="Fecha de inicio del período"
    )
    period_end_date = models.DateField(
        verbose_name="Fecha de fin del período"
    )
    uploaded_date = models.DateField(
        auto_now_add=True,
        verbose_name="Fecha de subida"
    )
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Subido por"
    )
    
    class Meta:
        verbose_name = "Documento Semestral"
        verbose_name_plural = "Documentos Semestrales"
        ordering = ['-uploaded_date']
        indexes = [
            models.Index(fields=['fund', 'uploaded_date']),
        ]
    
    def __str__(self):
        return f"Documento Semestral - {self.fund.name}"

    @property
    def period_display(self):
        """Retorna una representación legible del período"""
        return f"{self.year} - Semestre {self.semester}"

class FundPriceHistory(models.Model):
    """
    Modelo para almacenar el historial de precios por unidad de los fondos.
    """
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='price_history')
    price_per_unit = models.DecimalField(max_digits=14, decimal_places=4)
    effective_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    notes = models.TextField(blank=True, null=True, help_text="Razón para el cambio de precio")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Historial de Precio de Fondo"
        verbose_name_plural = "Historial de Precios de Fondos"
