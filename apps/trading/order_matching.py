from django.db.models import F, ExpressionWrapper, fields
from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from apps.trading.models import PurchaseOrder, SalesOrder, Transaction
from apps.fund.models import Fund

class OrderMatch:
    """
    Class responsible for matching purchase orders (buy) with sales orders (sell)
    based on compatible criteria like price, units, funds, etc.
    """
    
    def __init__(self):
        self.processed_matches = []
    
    def find_matches_for_order(self, order, limit=100, min_match_percentage=20):
        """
        Encuentra coincidencias para una orden específica (compra o venta).
        Permite que un usuario busque matches para su propia orden.
        """
        matches = []
        today = timezone.now().date()
        
        if isinstance(order, PurchaseOrder):
            # Buscar órdenes de venta compatibles para una orden de compra
            po = order
            po_min_price = po.min_acceptable_price
            # Limitar la búsqueda a órdenes de venta que expiran pronto
            soon_expiring = today + timedelta(days=5)
            
            sales_orders = SalesOrder.objects.filter(
                status='PENDING',
                fund=po.fund,
                price_per_unit__lte=po.price_per_unit,
                price_per_unit__gte=po_min_price,
                expiration_date__gte=today,
            ).annotate(
                days_to_expire = ExpressionWrapper(
                    F('expiration_date') - today,
                    output_field=fields.DurationField()
                )
            ).order_by('days_to_expire', 'price_per_unit')[:limit]
            
            for so in sales_orders:
                # No permitir operaciones con uno mismo
                if so.seller_user == po.supplier_user:
                    continue
                    
                # Verificar precios compatibles
                if po.price_per_unit <= so.max_acceptable_price:
                    available_units = min(po.units, so.units)
                    
                    match_percentage_po = (available_units / po.units) * 100
                    match_percentage_so = (available_units / so.units) * 100
                    
                    if match_percentage_po >= min_match_percentage:
                        matches.append({
                            'purchase_order': po,
                            'sales_order': so,
                            'matched_units': available_units,
                            'match_price': so.price_per_unit,
                            'total_amount': available_units * so.price_per_unit,
                            'match_percentage': match_percentage_po,
                            'is_partial': available_units < po.units
                        })
            
        elif isinstance(order, SalesOrder):
            # Buscar órdenes de compra compatibles para una orden de venta
            so = order
            so_max_price = so.max_acceptable_price
            
            purchase_orders = PurchaseOrder.objects.filter(
                status='PENDING',
                fund=so.fund,
                price_per_unit__gte=so.price_per_unit,
                price_per_unit__lte=so_max_price,
                expiration_date__gte=today,
                
            ).annotate(
                days_to_expire = ExpressionWrapper(
                    F('expiration_date') - today,
                    output_field=fields.DurationField()
                )
                ).order_by('days_to_expire','-price_per_unit')[:limit]  # Mejor precio primero
            
            for po in purchase_orders:
                # No permitir operaciones con uno mismo
                if po.supplier_user == so.seller_user:
                    continue
                    
                # Verificar precios compatibles
                po_min_price = po.min_acceptable_price
                if so.price_per_unit >= po_min_price:
                    available_units = min(po.units, so.units)
                    
                    match_percentage_po = (available_units / po.units) * 100
                    match_percentage_so = (available_units / so.units) * 100
                    
                    # Solo considerar coincidencias que cubran al menos  el procentaje mínimo
                    if match_percentage_so >= min_match_percentage:
                        matches.append({
                            'purchase_order': po,
                            'sales_order': so,
                            'matched_units': available_units,
                            'match_price': so.price_per_unit,
                            'total_amount': available_units * so.price_per_unit,
                            'match_percentage': match_percentage_so,
                            'is_partial': available_units < so.units
                        })
        
        matches.sort(key=lambda m: (m['match_percentage'], -m['match_price']
                                    if isinstance(order, PurchaseOrder)
                                    else m['match_price']), reverse=True)
        
        return matches[:limit]
    
    @db_transaction.atomic
    def execute_specific_match(self, purchase_order, sales_order, units=None):
        """
        Ejecuta un match específico entre dos órdenes seleccionadas.
        Permite que un usuario ejecute un match que ha seleccionado previamente.
        """
        try:
            # Refrescar datos dentro de la transacción
            po = PurchaseOrder.objects.select_for_update().get(id=purchase_order.id)
            so = SalesOrder.objects.select_for_update().get(id=sales_order.id)
            
            # Verificar estado actual
            if po.status != 'PENDING' or so.status != 'PENDING':
                return {
                    'success': False,
                    'error': 'Una o ambas órdenes ya no están disponibles'
                }
            
            # Determinar unidades a operar
            max_units = min(po.units, so.units)
            match_units = min(units, max_units) if units else max_units
            
            if match_units <= 0:
                return {
                    'success': False,
                    'error': 'No hay unidades disponibles para operar'
                }
            
            # Crear transacción
            transaction = self.create_transaction(po, so, match_units, so.price_per_unit)
            
            # Actualizar órdenes
            po.units -= match_units
            if po.units == 0:
                po.status = 'COMPLETED'
                po.completed_at = timezone.now()
            po.save()
            
            so.units -= match_units
            if so.units == 0:
                so.status = 'COMPLETED'
                so.completed_at = timezone.now()
            so.save()
            
            return {
                'success': True,
                'transaction_id': transaction.id,
                'units': match_units,
                'price': so.price_per_unit,
                'total': match_units * so.price_per_unit
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        

    def find_matches(self, limit=100):
        """
        Find matches between pending purchase and sales orders.
        """
        purchase_orders = PurchaseOrder.objects.filter(
            status='PENDING'
        ).order_by('created_at')[:limit]
        
        matches = []
        
        # For each purchase order, find potential matching sales orders
        for po in purchase_orders:
            # Only check if this purchase order hasn't been fully matched yet
            if po.units > 0:
                # Use min_acceptable_price to filter compatible sales orders
                po_min_price = po.min_acceptable_price
                
                # Find sales orders with compatible price
                sales_orders = SalesOrder.objects.filter(
                    status='PENDING',
                    fund=po.fund,
                    available_units__gt=0,
                    price_per_unit__lte=po.price_per_unit,  # Sales price <= Purchase max price
                    price_per_unit__gte=po_min_price,      # Sales price >= Purchase min acceptable price
                ).order_by('price_per_unit')  # Get the lowest price first
                
                for so in sales_orders:
                    # Skip if the seller is the same as the supplier (can't sell to yourself)
                    # En este caso el comprador (buyer) es el supplier_user 
                    if so.seller_user == po.supplier_user:
                        continue
                    
                    # Verificar márgenes de precio compatibles
                    so_max_price = so.max_acceptable_price
                    
                    # If purchase price is within acceptable range for sale
                    if po.price_per_unit <= so_max_price:
                        available_units = min(po.units, so.units)
                        
                        if available_units > 0:
                            matches.append({
                                'purchase_order': po,
                                'sales_order': so,
                                'matched_units': available_units,
                                'match_price': so.price_per_unit,
                                'total_amount': available_units * so.price_per_unit
                            })
                            break
        
        return matches
    
    @db_transaction.atomic
    def execute_matches(self, matches):
        """
        Execute the matching process by updating orders and creating transactions.
        """
        results = []
        
        for match in matches:
            po = match['purchase_order']
            so = match['sales_order']
            units = match['matched_units']
            price = match['match_price']
            
            try:
                # Re-query to get fresh data within the transaction
                po = PurchaseOrder.objects.select_for_update().get(id=po.id)
                so = SalesOrder.objects.select_for_update().get(id=so.id)
                
                # Make sure the orders are still valid
                if po.status != 'PENDING' or so.status != 'PENDING':
                    results.append({
                        'success': False,
                        'purchase_order_id': po.id,
                        'sales_order_id': so.id,
                        'error': 'One or both orders are no longer pending'
                    })
                    continue
                
                # Make sure the units are still available
                if po.units < units or so.units < units:
                    results.append({
                        'success': False,
                        'purchase_order_id': po.id,
                        'sales_order_id': so.id,
                        'error': 'Not enough units available'
                    })
                    continue
                
                # Update the purchase order
                po.units -= units
                if po.units == 0:
                    po.status = 'COMPLETED'
                    po.completed_at = timezone.now()
                po.save()
                
                # Update the sales order
                so.units -= units
                if so.units == 0:
                    so.status = 'COMPLETED'
                    so.completed_at = timezone.now()
                so.save()
                
                # Create a transaction record
                transaction = self.create_transaction(po, so, units, price)
                
                results.append({
                    'success': True,
                    'purchase_order_id': po.id,
                    'sales_order_id': so.id,
                    'matched_units': units,
                    'price': price,
                    'total_amount': units * price,
                    'transaction_id': transaction.id
                })
                
            except Exception as e:
                results.append({
                    'success': False,
                    'purchase_order_id': po.id,
                    'sales_order_id': so.id,
                    'error': str(e)
                })
        
        self.processed_matches.extend(results)
        return results
    
    def create_transaction(self, purchase_order, sales_order, units, price):
        """
        Create a transaction record for the matched orders.
        """
        # En esta implementación, el comprador (buyer) es el supplier_user de la orden de compra
        # y el vendedor (seller) es el seller_user de la orden de venta
        transaction = Transaction.objects.create(
            purchase_order=purchase_order,
            sales_order=sales_order,
            buyer=purchase_order.supplier_user,  # El comprador es el supplier_user
            seller=sales_order.seller_user,
            fund=purchase_order.fund,
            units=units,
            price_per_unit=price,
            total_amount=units * price,
            created_at=timezone.now()
        )
        
        return transaction
    
    def run_matching_cycle(self, batch_size=50):
        """
        Run a full cycle of matching: find matches and execute them.
        """
        matches = self.find_matches(limit=batch_size)
        return self.execute_matches(matches)

# Example usage in a management command or scheduled task
def match_orders():
    matcher = OrderMatch()
    results = matcher.run_matching_cycle()
    return results