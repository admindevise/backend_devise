from django.db import models
from decimal import Decimal
import uuid
from django.utils import timezone

from apps.user.models import User
from apps.fund.models import Fund
from apps.utils.models import base_model

class BaseOrder(base_model.BaseModel):
    """
    Modelo base abstracto para órdenes de compra y venta.
    Contiene los campos y métodos comunes a ambos tipos de órdenes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True, blank=True)
    units = models.PositiveIntegerField(blank=False, null=False)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    expiration_date = models.DateField()
    metadata = models.JSONField(default=dict, blank=True)
    margin = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0
    )    
    status = models.CharField(
        max_length=20, 
        choices=[
            ('PENDING', 'Pendiente'),
            ('MATCHED', 'Emparejada'),
            ('EXPIRED', 'Expirada'),
            ('PROCESSING_PAYMENT', 'Procesando Pago'),
            ('PAID', 'Pagada'),
            ('COMPLETED', 'Completada'),
            ('CANCELLED', 'Cancelada')
        ],
        default='PENDING'
    )
    
    fund = models.ForeignKey(Fund, on_delete=models.PROTECT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Campos de seguimiento temporal
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    matched_at = models.DateTimeField(null=True, blank=True)
    processing_payment_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    @property
    def amount(self):
        """
        Calcula el monto total de la orden.
        """
        return self.units * self.price_per_unit

    @property
    def days_until_expiration(self):
        """
        Calcula cuántos días faltan para la expiración de la orden.
        Retorna 0 si la orden ya ha expirado.
        """
        today = timezone.now().date()
        if self.expiration_date <= today:
            return 0
        
        delta = self.expiration_date - today
        return delta.days

    def update_status(self, new_status):
        """
        Actualiza el estado de la orden y registra la fecha del cambio.
        """
        self.status = new_status
        now = timezone.now()
        
        if new_status == 'APPROVED':
            self.approved_at = now
        elif new_status == 'PAID':
            self.paid_at = now
        elif new_status == 'COMPLETED':
            self.completed_at = now
        elif new_status == 'CANCELLED':
            self.cancelled_at = now
            
        self.save()


class PurchaseOrder(BaseOrder):
    """
    Modelo que representa una orden de compra de unidades de un fondo.
    """
    
    supplier_user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='purchase_orders'
    )
    
    # Relaciones específicas para órdenes de compra
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='created_purchase_orders'
    )
    fund = models.ForeignKey(
        Fund, 
        on_delete=models.PROTECT, 
        related_name='purchase_orders'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Orden de compra"
        verbose_name_plural = "Órdenes de compra"
    
    def __str__(self):
        return f"Purchase Order {self.order_number} - {self.status}"
    
    @property
    def min_acceptable_price(self):
        """
        Calcula el precio mínimo aceptable basado en el margen.
        Para órdenes de compra, esto representa cuánto por debajo del precio máximo 
        (price_per_unit) está dispuesto a pagar, pero nunca menos que el precio del fondo.
        """
        discount_factor = Decimal('1') - (self.margin / Decimal('100'))
        calculated_price = self.price_per_unit * discount_factor
        
        # Asegurar que el precio no sea menor que el precio de referencia del fondo
        return max(calculated_price, self.fund.price_per_unit)
    
    @property
    def max_acceptable_price(self):
        """
        Calcula el precio máximo aceptable basado en el margen.
        Para órdenes de venta, esto representa cuánto por encima del precio mínimo 
        (price_per_unit) está dispuesto a aceptar, pero nunca menos que el precio del fondo.
        """
        premium_factor = Decimal('1') + (self.margin / Decimal('100'))
        calculated_price = self.price_per_unit * premium_factor
        
        # Asegurar que el precio no sea menor que el precio de referencia del fondo
        return max(calculated_price, self.fund.price_per_unit)


class SalesOrder(BaseOrder):
    """
    Modelo que representa una orden de venta de unidades de un fondo.
    """
    
    seller_user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='sales_orders_seller'
    )
    
    # Relaciones específicas para órdenes de venta
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='created_sales_orders'
    )
    fund = models.ForeignKey(
        Fund, 
        on_delete=models.PROTECT, 
        related_name='sales_orders'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Orden de venta"
        verbose_name_plural = "Órdenes de venta"
    
    def __str__(self):
        return f"Sales Order {self.order_number} - {self.status}"
    
    @property
    def min_acceptable_price(self):
        """
        Calcula el precio mínimo aceptable basado en el margen.
        Para órdenes de compra, esto representa cuánto por debajo del precio máximo 
        (price_per_unit) está dispuesto a pagar, pero nunca menos que el precio del fondo.
        """
        discount_factor = Decimal('1') - (self.margin / Decimal('100'))
        calculated_price = self.price_per_unit * discount_factor
        
        # Asegurar que el precio no sea menor que el precio de referencia del fondo
        return max(calculated_price, self.fund.price_per_unit)
    
    @property
    def max_acceptable_price(self):
        """
        Calcula el precio máximo aceptable basado en el margen.
        Para órdenes de venta, esto representa cuánto por encima del precio mínimo 
        (price_per_unit) está dispuesto a aceptar, pero nunca menos que el precio del fondo.
        """
        premium_factor = Decimal('1') + (self.margin / Decimal('100'))
        calculated_price = self.price_per_unit * premium_factor
        
        # Asegurar que el precio no sea menor que el precio de referencia del fondo
        return max(calculated_price, self.fund.price_per_unit)
      
        
class Transaction(base_model.BaseModel):
    """
    Modelo que representa una transacción entre una orden de compra y una de venta.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='transactions')
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name='transactions')
    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='buyer_transactions')
    seller = models.ForeignKey(User, on_delete=models.PROTECT, related_name='seller_transactions')
    fund = models.ForeignKey(Fund, on_delete=models.PROTECT, related_name='transactions')
    units = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
    
    def __str__(self):
        return f"Transaction {self.id} - {self.units} units at {self.price_per_unit}"
    
    @property
    def amount(self):
        """
        Calcula el monto total de la transacción.
        """
        return self.units * self.price_per_unit


class OrderBook(base_model.BaseModel):
    """
        OrderBook maintains an up-to-date record of all open buy and sell orders for a specific fund,
        facilitating market visualization and trading operations.
        Attributes:
            fund (Fund): The fund this order book is associated with.
            last_price (Decimal): The most recent execution price of a trade for this fund.
            daily_high (Decimal): The highest price at which the fund has traded during the current day.
            daily_low (Decimal): The lowest price at which the fund has traded during the current day.
            daily_volume (int): The total number of units traded during the current day.
        Properties:
            buy_orders (QuerySet): All pending purchase orders for the fund, ordered by highest price first.
            sell_orders (QuerySet): All pending sales orders for the fund, ordered by lowest price first.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, on_delete=models.PROTECT, related_name='order_books')
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_volume = models.IntegerField(default=0)
    
    # Caches para acceso rápido a las órdenes abiertas
    @property
    def buy_orders(self):
        return PurchaseOrder.objects.filter(fund=self.fund, status='PENDING').order_by('-price_per_unit')
    
    @property
    def sell_orders(self):
        return SalesOrder.objects.filter(fund=self.fund, status='PENDING').order_by('price_per_unit')
    
    

    