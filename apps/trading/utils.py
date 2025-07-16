from django.utils import timezone
from django.db import models

def check_trading_liquidity(fund_id, required_quantity):
    """
    Verifica la liquidez del mercado secundario - CORREGIDO
    """
    from apps.trading.models import SalesOrder, PurchaseOrder
    from apps.fund.models import FundToken
    
    # 1. Contar unidades en órdenes de venta activas
    active_sales_units = SalesOrder.objects.filter(
        fund_id=fund_id,
        status__in=['PENDING', 'PARTIALLY_EXECUTED'],  # ✅ Incluir parcialmente ejecutadas
        expiration_date__gte=timezone.now().date()
    ).aggregate(
        total_units=models.Sum('available_units')  # ✅ Usar available_units
    )['total_units'] or 0
    
    # 2. Contar tokens que usuarios PUEDEN vender (aunque no estén en órdenes)
    potential_sellable_tokens = FundToken.objects.filter(
        fund_id=fund_id,
        status=True,
        owner_user__isnull=False,
        owner_user__is_staff=False,  # Solo usuarios regulares
        reserved_for_sale=False  # No reservados
    ).count()
    
    # 3. Verificar historial de mercado
    total_sales_orders = SalesOrder.objects.filter(fund_id=fund_id).count()
    total_purchase_orders = PurchaseOrder.objects.filter(fund_id=fund_id).count()
    
    # 4. LÓGICA INTELIGENTE DE LIQUIDEZ
    
    # Caso A: Mercado completamente nuevo
    if total_sales_orders == 0 and total_purchase_orders == 0:
        print(f"🆕 New market: Allowing first purchase order")
        return {
            'available': True,
            'available_count': potential_sellable_tokens,
            'required_count': required_quantity,
            'shortage': 0,
            'source': 'new_market',
            'message': 'First order in new market - always allowed'
        }
    
    # Caso B: Hay órdenes de venta activas suficientes
    if active_sales_units >= required_quantity:
        print(f"✅ Sufficient active sales orders: {active_sales_units} >= {required_quantity}")
        return {
            'available': True,
            'available_count': active_sales_units,
            'required_count': required_quantity,
            'shortage': 0,
            'source': 'active_sales_orders'
        }
    
    # Caso C: No hay suficientes órdenes activas, pero hay tokens vendibles
    if potential_sellable_tokens >= required_quantity:
        print(f"✅ Sufficient potential tokens: {potential_sellable_tokens} >= {required_quantity}")
        return {
            'available': True,
            'available_count': potential_sellable_tokens,
            'required_count': required_quantity,
            'shortage': 0,
            'source': 'potential_sellers',
            'message': f'Users own {potential_sellable_tokens} tokens that could be sold'
        }
    
    # Caso D: Mercado con actividad - permitir órdenes que motiven ventas
    if total_sales_orders > 0 or total_purchase_orders > 0:
        total_liquidity = active_sales_units + potential_sellable_tokens
        
        if total_liquidity >= required_quantity:
            print(f"✅ Combined liquidity sufficient: {total_liquidity} >= {required_quantity}")
            return {
                'available': True,
                'available_count': total_liquidity,
                'required_count': required_quantity,
                'shortage': 0,
                'source': 'combined_liquidity'
            }
    
    # Caso E: Realmente no hay liquidez suficiente
    total_available = active_sales_units + potential_sellable_tokens
    shortage = required_quantity - total_available
    
    print(f"❌ Insufficient liquidity: Available {total_available}, Required {required_quantity}")
    
    return {
        'available': False,
        'available_count': total_available,
        'required_count': required_quantity,
        'shortage': shortage,
        'source': 'insufficient_liquidity',
        'details': {
            'active_sales_units': active_sales_units,
            'potential_sellable_tokens': potential_sellable_tokens
        }
    }