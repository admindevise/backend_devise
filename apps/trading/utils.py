from django.utils import timezone
from django.db import models

def check_trading_liquidity(fund_id, required_quantity):
    """
    Verifica la liquidez del mercado secundario con lógica mejorada
    """
    from apps.trading.models import SalesOrder, PurchaseOrder
    from apps.fund.models import FundToken
    
    # 1. Contar unidades en SalesOrders PENDING
    sales_orders_units = SalesOrder.objects.filter(
        fund_id=fund_id,
        status='PENDING',
        expiration_date__gte=timezone.now().date()
    ).aggregate(
        total_units=models.Sum('units')
    )['total_units'] or 0
    
    # 2. Verificar si es un mercado nuevo o con poca actividad
    total_sales_orders = SalesOrder.objects.filter(fund_id=fund_id).count()
    total_purchase_orders = PurchaseOrder.objects.filter(fund_id=fund_id).count()
    
    # 3. Contar tokens totales distribuidos entre usuarios (no staff)
    user_owned_tokens = FundToken.objects.filter(
        fund_id=fund_id,
        status=True,
        owner_user__isnull=False,
        owner_user__is_staff=False  # Solo usuarios regulares
    ).count()
    
    # 4. Lógica de validación inteligente
    if total_sales_orders == 0 and total_purchase_orders == 0:
        # Mercado completamente nuevo - siempre permitir la primera orden
        return {
            'available': True,
            'available_count': user_owned_tokens,
            'required_count': required_quantity,
            'shortage': 0,
            'source': 'new_market',
            'message': 'First purchase order in new market'
        }
    
    elif sales_orders_units == 0 and user_owned_tokens > 0:
        # Hay tokens en manos de usuarios pero ninguna orden de venta activa
        # Permitir órdenes de compra (podrían motivar órdenes de venta)
        return {
            'available': True,
            'available_count': user_owned_tokens,  # Potencial liquidez
            'required_count': required_quantity,
            'shortage': 0,
            'source': 'dormant_market',
            'message': f'{user_owned_tokens} tokens owned by users, potential for sales orders'
        }
    
    else:
        # Mercado con actividad - validación normal
        return {
            'available': sales_orders_units >= required_quantity,
            'available_count': sales_orders_units,
            'required_count': required_quantity,
            'shortage': max(0, required_quantity - sales_orders_units),
            'source': 'active_market'
        }