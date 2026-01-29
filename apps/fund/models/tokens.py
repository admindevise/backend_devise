import uuid
from django.db import models
from apps.utils.models import base_model

class FundToken(base_model.BaseModel):
    """
    Modelo para almacenar los tokens asociados a un fideicomiso.
    """
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.CASCADE,
        related_name='tokens'
        )
    fund_investment = models.ForeignKey(
        'fund.FundInvestment',
        on_delete=models.CASCADE,
        related_name='tokens',
        null=True,
        blank=True,
        verbose_name="Inversión asociada",
        )
    
    token_id = models.CharField(max_length=255)
    nickname = models.CharField(max_length=255, blank=True, null=True)
    
    created_by = models.ForeignKey('user.User', on_delete=models.PROTECT, null=True)
    owner_user = models.ForeignKey('user.User', on_delete=models.PROTECT, null=True, related_name="owned_tokens")
    
    available_for_trading = models.BooleanField(default=False)
    reserved_for_sale = models.BooleanField(default=False)
    reserved_at = models.DateTimeField(null=True, blank=True)
    reservation_expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Token de Fideicomiso"
        verbose_name_plural = "Tokens de Fideicomisos"
        unique_together = ('fund', 'token_id')
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Token {self.token_id} del fideicomiso {self.fund.name}"
    
    
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
    fund = models.ForeignKey(
        'fund.Fund',
        on_delete=models.PROTECT,
        related_name='token_transactions'
        )
    token = models.ForeignKey(
        FundToken,
        on_delete=models.PROTECT,
        related_name='transactions'
        )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionTypes.choices,
        default=TransactionTypes.TRANSFER,)
    
    # Participantes
    from_user = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='token_transactions_sent',
        null=True, blank=True
        )
    to_user = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='token_transactions_received',
        null=True, blank=True
        )
    
    # Detalles de la transacción
    kaleido_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount = models.IntegerField(default=0, help_text="Cantidad de tokens involucrados en la transacción")
    
    # Relación con trading (si aplica)
    trading_transaction = models.ForeignKey(
        'trading.Transaction',
        on_delete=models.SET_NULL,
        null=True, blank=True
        )
    
    # Estado y metadatos
    status = models.CharField(
        max_length=20, 
        choices=TransactionStatus.choices, 
        default=TransactionStatus.COMPLETED
        )
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transacción de Token"
        verbose_name_plural = "Transacciones de Tokens"