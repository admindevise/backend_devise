from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from apps.user.models import User

class MatchSelection(models.Model):
    """
    Model representing a match selection between purchase and sales orders in a trading system.
    This model manages the pairing of purchase orders with sales orders, tracking the selection
    status, financial details, and expiration timing. It serves as a bridge between buyers and
    sellers in the trading platform.
    Attributes:
        purchase_order (OneToOneField): Reference to the associated purchase order
        sales_order (OneToOneField): Reference to the associated sales order
        total_units (PositiveIntegerField): Total number of units in the match
        total_amount (DecimalField): Total monetary value of the match
        expected_savings (DecimalField): Expected savings from this match
        status (CharField): Current status of the match selection (ACTIVE, EXPIRED, PROCESSING, COMPLETED)
        selected_at (DateTimeField): Timestamp when the match was initially selected
        expires_at (DateTimeField): Timestamp when the match selection expires
        created_at (DateTimeField): Timestamp when the record was created
        created_by (ForeignKey): User who created this match selection
        metadata (JSONField): Additional metadata storage for flexible data
    Properties:
        is_expired: Boolean indicating if the selection has passed its expiration time
        time_remaining: Time delta until expiration, or zero if already expired
    Meta:
        - Database table: 'trading_match_selection'
        - Indexed fields: expires_at, (purchase_order, sales_order, status), selected_at
    The model enforces business rules around match timing and provides utility methods
    for checking expiration status and calculating remaining time for decision-making.
    """
    
    class MatchSelectionStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Activo'
        EXPIRED = 'EXPIRED', 'Expirado'
        PROCESSING = 'PROCESSING', 'En Proceso'
        COMPLETED = 'COMPLETED', 'Completado'
        
    # Relations with other models
    purchase_order = models.OneToOneField('PurchaseOrder', on_delete=models.CASCADE, related_name='match_selection', null=True, blank=True)
    sales_order = models.OneToOneField('SalesOrder', on_delete=models.CASCADE, related_name='match_selection', null=True, blank=True)

    # Fields for match selection
    total_units = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    expected_savings = models.DecimalField(max_digits=20, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=MatchSelectionStatus.choices, default=MatchSelectionStatus.ACTIVE)

    # Critical timestamps
    selected_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_match_selection')
    
    metadata = models.JSONField(default=dict, blank=True, null=True)
    
    class Meta:
        db_table = 'trading_match_selection'
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['purchase_order', 'sales_order', 'status']),
            models.Index(fields=['selected_at']),
        ]
    
    def __str__(self):
        return f"MatchSelection {self.id} - {self.status}"
    
    @property
    def is_expired(self):
        """Determina si la selección ha expirado"""
        return timezone.now() > self.expires_at
    
    @property
    def time_remaining(self):
        """Calcula el tiempo restante hasta la expiración"""
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - timezone.now()
    

class MatchSelectionItem(models.Model):
    """Items individuales de una seleccion"""
    selection = models.ForeignKey(MatchSelection, on_delete=models.CASCADE, related_name='items')
    sales_order = models.ForeignKey('SalesOrder', on_delete=models.CASCADE, related_name='match_selection_items', null=True, blank=True)
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='match_selection_items', null=True, blank=True)
    
    # Transaction data
    units = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=20, decimal_places=2)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Automatically calculate
    buyer_savings = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    seller_gain = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    
    # Metadata for tracking
    metadata = models.JSONField(default=dict, blank=True, null=True)
    
    class Meta:
        db_table = 'trading_match_selection_item'
        indexes = [
            models.Index(fields=['selection', 'sales_order', 'purchase_order']),
            models.Index(fields=['units']),
        ]
    
    def __str__(self):
        return f"MatchSelectionItem {self.id} for Selection {self.selection.id} - SO {self.sales_order.order_number} - PO {self.purchase_order.order_number}"


class TokenTransferRecord(models.Model):
    """Registro completo de transferencias de tokens"""
    class TokenTransferStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        IN_PROGRESS = 'IN_PROGRESS', 'En Progreso'
        COMPLETED = 'COMPLETED', 'Completado'
        FAILED = 'FAILED', 'Fallido'
        REVERTED = 'REVERTED', 'Revertido'
    
    # Relations with other models
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='token_transfers')
    sales_order = models.ForeignKey('SalesOrder', on_delete=models.CASCADE, related_name='token_transfers')
    match_item = models.ForeignKey(MatchSelectionItem, on_delete=models.CASCADE, related_name='token_transfers')
    
    # Token data
    token_id = models.CharField(max_length=100, unique=True)
    from_user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='token_transfers_from')
    to_user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='token_transfers_to')
    
    # Status and timestamps
    status = models.CharField(max_length=20, choices=TokenTransferStatus.choices, default=TokenTransferStatus.PENDING)
    
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Blockchain transaction data
    transaction_uuid = models.CharField(max_length=100, null=True, blank=True)
    
    # Metadata for tracking
    metadata = models.JSONField(default=dict, blank=True, null=True)
    
    class Meta:
        db_table = 'trading_token_transfer_record'
        indexes = [
            models.Index(fields=['purchase_order', 'status']),
            models.Index(fields=['sales_order', 'status']),
            models.Index(fields=['token_id']),
            models.Index(fields=['status' ,'initiated_at']),
        ]
    
    
class PaymentRecord(models.Model):
    """Registro completo de pagos"""
    class PaymentStatus(models.TextChoices):
        INITIATED = 'INITIATED', 'Iniciado'
        PROCESSING = 'PROCESSING', 'Procesando'
        COMPLETED = 'COMPLETED', 'Completado'
        FAILED = 'FAILED', 'Fallido'
        REFUNDED = 'REFUNDED', 'Reembolsado'
    
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='payment_records')
    
    # Payment data
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=10, default='COP')
    payment_method = models.CharField(max_length=50, default='CREDIT_CARD')
    reference = models.CharField(max_length=100, default='test_001_devise')
    
    # Status and timestamps
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.INITIATED)
    
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    # Banking data (testing)
    bank_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    bank_reference = models.CharField(max_length=100, null=True, blank=True)
    
    # Metadata for tracking
    metadata = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        db_table = 'trading_payment_record'
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status', 'initiated_at']),
            models.Index(fields=['purchase_order', 'status']),
        ]