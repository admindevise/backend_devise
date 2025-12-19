from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator
from apps.utils.models import base_model


# ============================================================================
# COMISIONES
# ============================================================================
class Commissions(base_model.BaseModel):
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='commissions',
        verbose_name="Fondo"
    )
    contract_num = models.CharField(
        max_length=10,
        verbose_name="Seccion del contrato que especifica la comision"
    )
    name = models.CharField(
        max_length=50,
        verbose_name="Nombre de la comision"
    )
    description = models.TextField(
        max_length=256,
        verbose_name="Detalle de la comision"
    )
    amount = models.CharField(
        max_length=50,
        verbose_name="Monto acordado en el contrato de la comision"
    )
    

# ============================================================================
# ESTADO DE CUENTA - COMISIONES FIDUCIARIAS
# ============================================================================

class AccountStatement(base_model.BaseModel):
    """
    Estado de cuenta para seguimiento de comisiones fiduciarias.
    Registra movimientos, saldos pendientes e intereses de mora.
    """
    
    class MovementStatus(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PARTIAL = 'partial', 'Pago Parcial'
        PAID = 'paid', 'Pagado'
        OVERDUE = 'overdue', 'Vencido'
        CANCELLED = 'cancelled', 'Anulado'
    
    class CommissionType(models.TextChoices):
        STRUCTURING = 'structuring', 'Estructuración'
        ADMINISTRATION = 'administration', 'Administración'
        MANAGEMENT = 'management', 'Gestión'
        SUCCESS = 'success', 'Éxito'
        OTHER = 'other', 'Otra'
    
    # ========================================
    # RELACIONES
    # ========================================
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='account_statements',
        verbose_name="Fondo"
    )
    
    period = models.ForeignKey(
        'fund.AccountingPeriod',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='account_statements',
        verbose_name="Período contable"
    )
    
    # Relación opcional con registro contable
    accounting_entry = models.ForeignKey(
        'fund.AccountingEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='account_statements',
        verbose_name="Registro contable asociado"
    )
    
    # ========================================
    # IDENTIFICACIÓN DEL DOCUMENTO
    # ========================================
    document_number = models.CharField(
        max_length=50,
        verbose_name="Documento",
        help_text="Identificador del registro contable (ej: FB-31909)"
    )
    
    commission_description = models.TextField(
        verbose_name="Descripción comisión",
        help_text="Detalle de la comisión causada"
    )
    
    commission_type = models.CharField(
        max_length=20,
        choices=CommissionType.choices,
        default=CommissionType.OTHER,
        verbose_name="Tipo de comisión"
    )
    
    # ========================================
    # VALORES FINANCIEROS
    # ========================================
    movement_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Movimiento",
        help_text="Valor del movimiento contable"
    )
    
    pending_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Saldo Pendiente",
        help_text="Valor del saldo pendiente del movimiento"
    )
    
    overdue_interest = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Intereses de Mora",
        help_text="Valor de los intereses por no pagar la comisión"
    )
    
    # ========================================
    # FECHAS
    # ========================================
    issue_date = models.DateField(
        verbose_name="Fecha de emisión",
        help_text="Fecha en que se genera la comisión"
    )
    
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento",
        help_text="Fecha límite de pago"
    )
    
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de pago",
        help_text="Fecha en que se realizó el pago"
    )
    
    # ========================================
    # ESTADO
    # ========================================
    status = models.CharField(
        max_length=20,
        choices=MovementStatus.choices,
        default=MovementStatus.PENDING,
        verbose_name="Estado"
    )
    
    # ========================================
    # IMPORTACIÓN
    # ========================================
    import_batch = models.ForeignKey(
        'fund.AccountingImportBatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='account_statements',
        verbose_name="Lote de importación"
    )
    
    original_row_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Fila original"
    )
    
    # ========================================
    # METADATOS
    # ========================================
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos adicionales"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )
    
    class Meta:
        verbose_name = "Estado de Cuenta"
        verbose_name_plural = "Estados de Cuenta"
        ordering = ['-issue_date', '-created_at']
        unique_together = ['fund', 'document_number']
        indexes = [
            models.Index(fields=['fund', 'status']),
            models.Index(fields=['fund', 'issue_date']),
            models.Index(fields=['document_number']),
            models.Index(fields=['due_date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.document_number} - {self.commission_description[:50]}"
    
    @property
    def total_debt(self) -> Decimal:
        """Total adeudado (saldo pendiente + intereses)"""
        return self.pending_balance + self.overdue_interest
    
    @property
    def is_overdue(self) -> bool:
        """Verifica si el documento está vencido"""
        from django.utils import timezone
        if self.due_date and self.status == self.MovementStatus.PENDING:
            return timezone.now().date() > self.due_date
        return False
    
    @property
    def days_overdue(self) -> int:
        """Días de mora"""
        from django.utils import timezone
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0
    
    def calculate_overdue_interest(self, annual_rate: Decimal = Decimal('0.12')) -> Decimal:
        """
        Calcula intereses de mora basado en días vencidos.
        
        Args:
            annual_rate: Tasa anual de interés (default 12%)
        
        Returns:
            Intereses calculados
        """
        if not self.is_overdue:
            return Decimal('0.00')
        
        daily_rate = annual_rate / Decimal('365')
        interest = self.pending_balance * daily_rate * Decimal(self.days_overdue)
        return interest.quantize(Decimal('0.01'))
    
    def update_overdue_interest(self, annual_rate: Decimal = Decimal('0.12')) -> None:
        """Actualiza los intereses de mora"""
        self.overdue_interest = self.calculate_overdue_interest(annual_rate)
        self.save(update_fields=['overdue_interest', 'updated_at'])
    
    def mark_as_paid(self, payment_date=None) -> None:
        """Marca el documento como pagado"""
        from django.utils import timezone
        self.status = self.MovementStatus.PAID
        self.payment_date = payment_date or timezone.now().date()
        self.pending_balance = Decimal('0.00')
        self.save(update_fields=['status', 'payment_date', 'pending_balance', 'updated_at'])

class Meetings(base_model.BaseModel):
    class MeetingType(models.TextChoices):
        ANNUAL_MEETING = 'annual_meeting', 'asamblea anual'
        COMMITTEE = 'committee', 'comite'
        EXTRAORDINARY = 'extraordinary', 'extraordinaria'
        
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='meetings',
        verbose_name="Fondo"
    )
    type_meeting = models.CharField(
        max_length=20,
        choices=MeetingType.choices,
        verbose_name="Tipo de reunion"
    )

# ============================================================================
# CESIONES
# ============================================================================    

class Transfers(base_model.BaseModel):
    class TypeIdActor(models.TextChoices):
        CC = 'national identity card', 'cedula de ciudadania'
        CE = 'foreigners identity card', 'cedula de extranjeria'
        
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        verbose_name="Fondo"
    )
    doc_transfer = models.FileField(
        upload_to="funds/transfer/",
        null=True,
        blank=True,
        verbose_name="Documento de cesion"
    )
    effective_date = models.DateField(
        verbose_name="Fecha de vigencia"
    )
    class_transfer = models.CharField(
        max_length=40,
        verbose_name="Clase de sesion que se adquirio"
    )
    settlor = models.CharField(
        max_length=40,
        verbose_name="Actor que cede su participacion"
    )
    assignee = models.CharField(
        max_length=40,
        verbose_name="Actor que recibe la participacion"
    )
    assigned_amount = models.DecimalField(
        decimal_places=2,
        max_digits=12,
        verbose_name="Cantidad que se acuerda entre las partes"
    )
    
    # Agregados luego de examinar el contrato de cesion
    actor_settlor = models.CharField(
        max_length=50,
        verbose_name="Representante legal del al entidad Cesionario"
    )    
    actor_assignee = models.CharField(
        max_length=50,
        verbose_name="Representante legal de la entidad Cedente"
    )
    nit_settlor = models.IntegerField(
        verbose_name="Nit del actor que cede si participacion"
    )
    nit_assignee = models.IntegerField(
        verbose_name="Nit del actor que recibe la participacion"
    )
    type_doc_settlor = models.CharField(
        max_length=50,
        choices=TypeIdActor.choices,
        verbose_name="Tipo de documento del representante legal del Cesionario"
    )
    type_doc_assignee = models.CharField(
        max_length=50,
        choices=TypeIdActor.choices,
        verbose_name="Tipo de documento del representante legal del Cedente"
    )
    id_doc_settlor = models.IntegerField(
        verbose_name="Numero de documento del representante legal del Cesionario"
    )
    id_doc_assignee = models.IntegerField(
        verbose_name="Numero de documento del representante legal del Cedente"
    )
