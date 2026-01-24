from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.utils.models import base_model


# ============================================================================
# CATÁLOGO DE CUENTAS CONTABLES
# ============================================================================
class AccountCategory(base_model.BaseModel):
    """
    Categorías principales de cuentas contables.
    Permite estructura jerárquica flexible.
    """
    
    class CategoryType(models.TextChoices):
        ASSET = 'asset', 'Activo'
        LIABILITY = 'liability', 'Pasivo'
        EQUITY = 'equity', 'Patrimonio'
        INCOME = 'income', 'Ingreso'
        EXPENSE = 'expense', 'Gasto'
        OTHER = 'other', 'Otro'
    
    class OperationalType(models.TextChoices):
        OPERATIONAL = 'operational', 'Operativo',
        NON_OPERATIONAL = 'non_operational', 'No operativo'
        NOT_APPLICABLE = 'na', 'No Aplica'
        
    code = models.CharField(
        max_length=20,
        verbose_name="Código"
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre"
    )
    
    category_type = models.CharField(
        max_length=20,
        choices=CategoryType.choices,
        verbose_name="Tipo de categoría"
    )
    
    operational_type = models.CharField(
        max_length=30,
        choices=OperationalType.choices,
        verbose_name="Tipo operacional"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name="Categoría padre"
    )
    
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name='account_categories',
        verbose_name="Fondo",
        help_text="Fondo al que pertenece esta categoría"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="¿Activa?"
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden de visualización"
    )
    
    class Meta:
        verbose_name = "Categoría Contable"
        verbose_name_plural = "Categorías Contables"
        ordering = ['fund', 'display_order', 'code']
        unique_together = ['fund', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


# ============================================================================
# PERÍODOS CONTABLES
# ============================================================================
class AccountingPeriod(base_model.BaseModel):
    """
    Períodos contables para organizar registros.
    """
    
    class PeriodStatus(models.TextChoices):
        OPEN = 'open', 'Abierto'
        CLOSED = 'closed', 'Cerrado'
        LOCKED = 'locked', 'Bloqueado'
    
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name='accounting_periods',
        verbose_name="Fondo"
    )
    
    year = models.PositiveIntegerField(
        verbose_name="Año"
    )
    
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Mes"
    )
    
    start_date = models.DateField(
        verbose_name="Fecha de inicio"
    )
    
    end_date = models.DateField(
        verbose_name="Fecha de fin"
    )
    
    period_status = models.CharField(
        max_length=20,
        choices=PeriodStatus.choices,
        default=PeriodStatus.OPEN,
        verbose_name="Estado"
    )
    
    closed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de cierre"
    )
    
    closed_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_accounting_periods',
        verbose_name="Cerrado por"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )
    
    class Meta:
        verbose_name = "Período Contable"
        verbose_name_plural = "Períodos Contables"
        ordering = ['-year', '-month']
        unique_together = ['fund', 'year', 'month']
    
    def __str__(self):
        return f"{self.fund.name} - {self.year}/{self.month:02d}"
    
    @property
    def period_display(self):
        """Representación legible del período"""
        months = [
            '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
        return f"{months[self.month]} {self.year}"


# ============================================================================
# TIPOS DE COMPROBANTES
# ============================================================================
class ReceipType(base_model.BaseModel):
    name = models.CharField(
        max_length=50,
        verbose_name="Nombre de tipo de comprobante"
    )
    code = models.CharField(
        max_length=10,
        verbose_name="Codigo de tipo de comprobante"
    )
    
    class Meta:
        verbose_name = "Tipo de Comprobante"
        verbose_name_plural = "Tipos de Comprobantes"
        ordering = ['code']
        unique_together = ['code']


# ============================================================================
# CUENTAS
# ============================================================================
class Account(base_model.BaseModel):
    account_category = models.ForeignKey(
        AccountCategory,
        on_delete=models.PROTECT,
        related_name='account',
        verbose_name="Categoria de cuenta"
    )
    account_id = models.CharField(
        max_length=256,
        unique=True,
        verbose_name="Numero unico de cuenta"
    )
    name = models.CharField(
        max_length=50,
        verbose_name="Nombre de la cuenta"
    )
    
    class Meta:
        verbose_name = "Cuenta Contable"
        verbose_name_plural = "Cuentas Contables"
        ordering = ['account_category', 'account_id']


# ============================================================================
# REGISTROS CONTABLES (TRANSACCIONES)
# ============================================================================
class AccountingEntry(base_model.BaseModel):
    """
    Registro contable individual.
    Modelo flexible para cualquier tipo de transacción contable.
    """
    
    class EntryType(models.TextChoices):
        DEBIT = 'debit', 'Débito'
        CREDIT = 'credit', 'Crédito'
    
    class EntryStatus(models.TextChoices):
        DRAFT = 'draft', 'Borrador'
        POSTED = 'posted', 'Contabilizado'
        CANCELLED = 'cancelled', 'Anulado'
    
    class EntrySource(models.TextChoices):
        MANUAL = 'manual', 'Registro Manual'
        IMPORT = 'import', 'Importación XLSX'
        SYSTEM = 'system', 'Generado por Sistema'
    
    # ========================================
    # RELACIONES PRINCIPALES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='accounting_entries',
        verbose_name="Fondo"
    )
    
    period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.PROTECT,
        related_name='entries',
        verbose_name="Período contable"
    )
    
    category = models.ForeignKey(
        AccountCategory,
        on_delete=models.PROTECT,
        related_name='entries',
        verbose_name="Categoría contable"
    )
    
    receip_type = models.ForeignKey(
        ReceipType,
        on_delete=models.PROTECT,
        related_name="entries",
        verbose_name="Tipo de comprobante"
    )
    
    # ========================================
    # INFORMACIÓN DEL REGISTRO
    # ========================================
    entry_date = models.DateField(
        verbose_name="Fecha del registro"
    )
    
    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.choices,
        verbose_name="Tipo (Débito/Crédito)"
    )
    
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Monto (COP)"
    )
    
    description = models.TextField(
        verbose_name="Descripción/Concepto"
    )
    
    # ========================================
    # ESTADO Y ORIGEN
    # ========================================
    entry_status = models.CharField(
        max_length=20,
        choices=EntryStatus.choices,
        default=EntryStatus.DRAFT,
        verbose_name="Estado"
    )
    
    entry_source = models.CharField(
        max_length=20,
        choices=EntrySource.choices,
        default=EntrySource.MANUAL,
        verbose_name="Origen del registro"
    )
    
    # ========================================
    # REFERENCIA EXTERNA (OPCIONAL)
    # ========================================
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Referencia externa",
        help_text="Número de documento, factura, etc."
    )
    
    document_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número de documento"
    )
    
    # ========================================
    # TERCERO (OPCIONAL)
    # ========================================
    third_party_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nombre del tercero"
    )
    
    third_party_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="ID del tercero (NIT/Cédula)"
    )
    
    # ========================================
    # IMPORTACIÓN
    # ========================================
    import_batch = models.ForeignKey(
        'fund.AccountingImportBatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entries',
        verbose_name="Lote de importación"
    )
    
    original_row_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Fila original XLSX"
    )
    
    # ========================================
    # DATOS ADICIONALES FLEXIBLES
    # ========================================
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos adicionales",
        help_text="Datos adicionales en formato JSON"
    )
    
    # ========================================
    # DOCUMENTOS SOPORTE
    # ========================================
    attachment = models.FileField(
        upload_to='funds/accounting/entries/',
        blank=True,
        null=True,
        verbose_name="Documento soporte"
    )
    
    class Meta:
        verbose_name = "Registro Contable"
        verbose_name_plural = "Registros Contables"
        ordering = ['-entry_date', '-created_at']
        indexes = [
            models.Index(fields=['fund', 'entry_date']),
            models.Index(fields=['fund', 'period']),
            models.Index(fields=['category', 'entry_date']),
            models.Index(fields=['entry_status']),
            models.Index(fields=['entry_source']),
        ]
    
    def __str__(self):
        return f"{self.entry_date} - {self.category.name}: ${self.amount:,.2f}"


# ============================================================================
# RENDICION DE CUENTAS (CARGA DE ARCHIVO PDF, LUEGO DE APROBACION)
# ============================================================================
class Accountability(base_model.BaseModel):
    class PeriodType(models.TextChoices):
        MONTHLY = 'monthly', 'Mensual'
        QUARTERLY = 'quarterly', 'Trimestral'
        BIANNUAL = 'biannual', 'Semestral'
        ANNUAL = 'annual', 'Anual'
    
    # ========================================
    # RELACIONES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='accountability_docs',
        verbose_name="Fondo"
    )
    
    # ========================================
    # INFORMACIÓN DEL PERÍODO
    # ========================================
    period_type = models.CharField(
        max_length=20,
        choices=PeriodType.choices,
        verbose_name="Tipo de período"
    )
    
    period_year = models.PositiveIntegerField(
        verbose_name="Año"
    )
    
    period_month = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Mes",
        help_text="Requerido para períodos mensuales"
    )
    
    # ========================================
    # DOCUMENTO
    # ========================================
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre del documento"
    )
    
    document = models.FileField(
        upload_to='funds/accountability/%Y/',
        verbose_name="Documento aprobado"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )
    
    class Meta:
        verbose_name = "Rendición de Cuentas"
        verbose_name_plural = "Rendiciones de Cuentas"
        ordering = ['-period_year', '-period_month',]
        unique_together = ['fund', 'period_type', 'period_year', 'period_month']
    
    def __str__(self):
        if self.period_month:
            return f"{self.fund.name} - {self.get_period_type_display()} {self.period_year}/{self.period_month:02d}"
        return f"{self.fund.name} - {self.get_period_type_display()} {self.period_year}"    
    

# ============================================================================
# REGISTRO DE FACTURAS
# ============================================================================
class InvoiceRecord(base_model.BaseModel):
    """
    Registro de facturas recibidas o emitidas.
    """
    class InvoiceType(models.TextChoices):
        SALE = 'sale', 'Venta'
        COMISSION = 'comission', 'Comisión'
        SPENT = 'spent', 'Gasto'
    
    class InvoiceStatus(models.TextChoices):
        ISSUED = 'issued', 'Emitida'
        PAID = 'paid', 'Pagada'
        EXPIRED = 'expired', 'Vencida'
        ANNULLED = 'annulled', 'Anulada'
        
    # Relaciones principales
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Fondo"
    )
    trust_agreement = models.ForeignKey(
        'fund.TrustAgreement',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Acuerdo de fideicomiso"
    )
    accounting_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Cuenta contable"
    )
    accounting_period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Período contable"
    )
    
    
    # Identificación de la factura
    invoice_number = models.CharField(
        max_length=50,
        verbose_name="Número de factura"
    )
    invoice_type = models.CharField(
        max_length=20,
        choices=InvoiceType.choices,
        verbose_name="Tipo de factura"
    )
    
    # Emisor y receptor
    issuer_name = models.CharField(
        max_length=255,
        verbose_name="Nombre del emisor"
    )
    issuer_nit = models.CharField(
        max_length=50,
        verbose_name="NIT del emisor"
    )
    receiver_name = models.CharField(
        max_length=255,
        verbose_name="Nombre del receptor"
    )
    receiver_nit = models.CharField(
        max_length=50,
        verbose_name="NIT del receptor"
    )
    
    # Fechas
    issued_date = models.DateField(
        verbose_name="Fecha de emisión"
    )
    expiration_date = models.DateField(
        verbose_name="Fecha de vencimiento"
    )
    
    # Conceptos
    notion = models.TextField(
        verbose_name="Concepto"
    )
    items_details = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Detalles de ítems",
        help_text="Lista de ítems en formato JSON"
    )
    
    # Valores monetarios
    subtotal = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Subtotal (COP)"
    )
    value_iva = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Valor IVA (COP)"
    )
    withholding_tax = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Retención en la fuente (COP)"
    )
    ica_withholding_tax = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Retención ICA (COP)"
    )
    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Monto total (COP)"
    )
    
    # Pago
    invoice_status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.ISSUED,
        verbose_name="Estado de la factura"
    )
    payment_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de pago"
    )
    payment_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Monto pagado (COP)"
    )
    payment_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Tipo de pago"
    )
    
    # Documentos
    attachment = models.FileField(
        upload_to='funds/invoices/%Y/',
        blank=True,
        null=True,
        verbose_name="Documento de la factura"
    )
    xml_attachment = models.FileField(
        upload_to='funds/invoices/xml/%Y/',
        blank=True,
        null=True,
        verbose_name="Archivo XML de la factura"
    )
    
    class Meta:
        verbose_name = "Registro de Factura"
        verbose_name_plural = "Registros de Facturas"
        ordering = ['-issued_date', '-created_at']
        unique_together = ['fund', 'invoice_number']
        
    def calculate_total(self):
        """Calcula el monto total de la factura"""
        self.total_amount = self.subtotal + self.value_iva - self.withholding_tax - self.ica_withholding_tax
        return self.total_amount


# ============================================================================
# SALDOS POR CATEGORÍA Y PERÍODO
# ============================================================================
class AccountingBalance(base_model.BaseModel):
    """
    Saldos consolidados por categoría y período.
    Facilita consultas rápidas sin recalcular desde registros.
    """
    
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name='accounting_balances',
        verbose_name="Fondo"
    )
    
    period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.CASCADE,
        related_name='balances',
        verbose_name="Período"
    )
    
    category = models.ForeignKey(
        AccountCategory,
        on_delete=models.CASCADE,
        related_name='balances',
        verbose_name="Categoría"
    )
    
    # ========================================
    # SALDOS
    # ========================================
    opening_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Saldo inicial"
    )
    
    total_debits = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total débitos"
    )
    
    total_credits = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total créditos"
    )
    
    closing_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Saldo final"
    )
    
    # ========================================
    # METADATOS
    # ========================================
    last_calculated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )
    
    class Meta:
        verbose_name = "Saldo Contable"
        verbose_name_plural = "Saldos Contables"
        unique_together = ['fund', 'period', 'category']
        ordering = ['period', 'category__code']
    
    def __str__(self):
        return f"{self.category.code} - {self.period}: ${self.closing_balance:,.2f}"
    
    def recalculate(self):
        """Recalcula el saldo basado en los registros del período"""
        from django.db.models import Sum
        
        entries = AccountingEntry.objects.filter(
            fund=self.fund,
            period=self.period,
            category=self.category,
            entry_status='posted'
        )
        
        self.total_debits = entries.filter(
            entry_type='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        self.total_credits = entries.filter(
            entry_type='credit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Calcular saldo según tipo de categoría
        if self.category.category_type in ['asset', 'expense']:
            self.closing_balance = self.opening_balance + self.total_debits - self.total_credits
        else:
            self.closing_balance = self.opening_balance + self.total_credits - self.total_debits
        
        self.save()


# ============================================================================
# IMPORTACIÓN MASIVA XLSX
# ============================================================================
class AccountingImportBatch(base_model.BaseModel):
    """
    Lote de importación desde archivos XLSX.
    Permite trazabilidad y reversión de importaciones.
    """
    
    class ImportStatus(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        VALIDATING = 'validating', 'Validando'
        VALIDATED = 'validated', 'Validado'
        IMPORTING = 'importing', 'Importando'
        COMPLETED = 'completed', 'Completado'
        FAILED = 'failed', 'Fallido'
        PARTIAL = 'partial', 'Parcialmente Completado'
        REVERSED = 'reversed', 'Reversado'
    
    class ImportType(models.TextChoices):
        HISTORICAL = 'historical', 'Datos Históricos'
        CURRENT = 'current', 'Datos Corrientes'
        OPENING_BALANCES = 'opening', 'Saldos de Apertura'
        CATEGORIES = 'categories', 'Catálogo de Categorías'
    
    # ========================================
    # RELACIONES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='accounting_imports',
        verbose_name="Fondo"
    )
    
    # ========================================
    # ARCHIVO
    # ========================================
    file = models.FileField(
        upload_to='funds/accounting/imports/',
        verbose_name="Archivo XLSX"
    )
    
    original_filename = models.CharField(
        max_length=255,
        verbose_name="Nombre original"
    )
    
    # ========================================
    # TIPO Y ESTADO
    # ========================================
    import_type = models.CharField(
        max_length=20,
        choices=ImportType.choices,
        verbose_name="Tipo de importación"
    )
    
    import_status = models.CharField(
        max_length=20,
        choices=ImportStatus.choices,
        default=ImportStatus.PENDING,
        verbose_name="Estado"
    )
    
    # ========================================
    # RANGO DE DATOS
    # ========================================
    data_start_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha inicio datos"
    )
    
    data_end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha fin datos"
    )
    
    # ========================================
    # ESTADÍSTICAS
    # ========================================
    total_rows = models.PositiveIntegerField(
        default=0,
        verbose_name="Total filas"
    )
    
    processed_rows = models.PositiveIntegerField(
        default=0,
        verbose_name="Filas procesadas"
    )
    
    successful_rows = models.PositiveIntegerField(
        default=0,
        verbose_name="Filas exitosas"
    )
    
    failed_rows = models.PositiveIntegerField(
        default=0,
        verbose_name="Filas fallidas"
    )
    
    # ========================================
    # ERRORES Y CONFIGURACIÓN
    # ========================================
    validation_errors = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Errores de validación"
    )
    
    column_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Mapeo de columnas",
        help_text="Mapeo de columnas del XLSX a campos del modelo"
    )
    
    # ========================================
    # AUDITORÍA
    # ========================================
    imported_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='accounting_imports',
        verbose_name="Importado por"
    )
    
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Inicio"
    )
    
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fin"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )
    
    class Meta:
        verbose_name = "Importación Contable"
        verbose_name_plural = "Importaciones Contables"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Import {self.id} - {self.fund.name} ({self.get_import_status_display()})"
    
    @property
    def success_rate(self):
        """Porcentaje de éxito"""
        if self.total_rows == 0:
            return 0
        return round((self.successful_rows / self.total_rows) * 100, 2)


class AccountingImportError(base_model.BaseModel):
    """
    Errores detallados de importación.
    """
    
    class ErrorSeverity(models.TextChoices):
        WARNING = 'warning', 'Advertencia'
        ERROR = 'error', 'Error'
        CRITICAL = 'critical', 'Crítico'
    
    batch = models.ForeignKey(
        AccountingImportBatch,
        on_delete=models.CASCADE,
        related_name='errors',
        verbose_name="Lote"
    )
    
    row_number = models.PositiveIntegerField(
        verbose_name="Fila"
    )
    
    column_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Columna"
    )
    
    severity = models.CharField(
        max_length=20,
        choices=ErrorSeverity.choices,
        default=ErrorSeverity.ERROR,
        verbose_name="Severidad"
    )
    
    error_code = models.CharField(
        max_length=50,
        verbose_name="Código"
    )
    
    error_message = models.TextField(
        verbose_name="Mensaje"
    )
    
    original_value = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Valor original"
    )
    
    is_resolved = models.BooleanField(
        default=False,
        verbose_name="¿Resuelto?"
    )
    
    class Meta:
        verbose_name = "Error de Importación"
        verbose_name_plural = "Errores de Importación"
        ordering = ['batch', 'row_number']
    
    def __str__(self):
        return f"Fila {self.row_number}: {self.error_code}"


# ============================================================================
# RESÚMENES FINANCIEROS
# ============================================================================
class FinancialSummary(base_model.BaseModel):
    """
    Resúmenes financieros generados por período.
    Almacena totales y métricas calculadas.
    """
    
    class SummaryType(models.TextChoices):
        MONTHLY = 'monthly', 'Resumen Mensual'
        QUARTERLY = 'quarterly', 'Resumen Trimestral'
        ANNUAL = 'annual', 'Resumen Anual'
    
    class SummaryStatus(models.TextChoices):
        DRAFT = 'draft', 'Borrador'
        GENERATED = 'generated', 'Generado'
        APPROVED = 'approved', 'Aprobado'
    
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name='financial_summaries',
        verbose_name="Fondo"
    )
    
    period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.CASCADE,
        related_name='summaries',
        verbose_name="Período"
    )
    
    summary_type = models.CharField(
        max_length=20,
        choices=SummaryType.choices,
        default=SummaryType.MONTHLY,
        verbose_name="Tipo"
    )
    
    summary_status = models.CharField(
        max_length=20,
        choices=SummaryStatus.choices,
        default=SummaryStatus.DRAFT,
        verbose_name="Estado"
    )
    
    # ========================================
    # TOTALES PRINCIPALES
    # ========================================
    total_assets = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total Activos"
    )
    
    total_liabilities = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total Pasivos"
    )
    
    total_equity = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total Patrimonio"
    )
    
    total_income = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total Ingresos"
    )
    
    total_expenses = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total Gastos"
    )
    
    net_result = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Resultado Neto"
    )
    
    # ========================================
    # DATOS DETALLADOS
    # ========================================
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos detallados",
        help_text="Estructura JSON con desglose por categorías"
    )
    
    # ========================================
    # AUDITORÍA
    # ========================================
    generated_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_summaries',
        verbose_name="Generado por"
    )
    
    generated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha generación"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )
    
    class Meta:
        verbose_name = "Resumen Financiero"
        verbose_name_plural = "Resúmenes Financieros"
        unique_together = ['fund', 'period', 'summary_type']
        ordering = ['-period__year', '-period__month']
    
    def __str__(self):
        return f"{self.fund.name} - {self.get_summary_type_display()} {self.period}"
    
    