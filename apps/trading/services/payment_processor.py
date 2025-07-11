from django.utils import timezone
from typing import Dict, Any
import logging
import random
import time

from apps.trading.models import PurchaseOrder

logger = logging.getLogger('trading.payment_processor')

class PaymentProcessingService:
    """
    💳 Servicio de Procesamiento de Pagos - Maneja solo el pago bancario (ficticio)
    
    Responsabilidades:
    - Generar datos ficticios de pago bancario
    - Simular procesamiento bancario
    - Actualizar estados relacionados con el pago
    """
    
    def __init__(self):
        # FICTICIOS: Métodos de pago disponibles
        self.payment_methods = ['PSE', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'EFECTY']
    
    def process_payment(self, purchase_order: PurchaseOrder, payment_data: dict) -> dict:
        """Procesa el pago bancario completo"""
        
        # 1. Preparar datos de pago
        enriched_payment_data = self.prepare_payment_data(payment_data, purchase_order)
        
        # 2. Simular procesamiento bancario
        self.simulate_bank_processing(purchase_order, enriched_payment_data)
        
        # 3. Construir respuesta
        return self.build_payment_result(purchase_order, enriched_payment_data)
    
    def prepare_payment_data(self, payment_data: dict, purchase_order: PurchaseOrder) -> dict:
        """Prepara y enriquece los datos de pago"""
        return self.generate_fake_payment_data(payment_data, purchase_order)
    
    def generate_fake_payment_data(self, payment_data: dict, purchase_order: PurchaseOrder) -> dict:
        """Genera datos ficticios SOLO para el pago bancario"""
        
        enriched_data = payment_data.copy()
        
        # Si no se especifica método, usar uno aleatorio
        if not enriched_data.get('method'):
            enriched_data['method'] = random.choice(self.payment_methods)
        
        # Generar referencia ficticia
        if not enriched_data.get('reference'):
            timestamp = int(time.time())
            enriched_data['reference'] = f"REF-{enriched_data['method']}-{timestamp}"
        
        # FICTICIOS: Solo metadatos bancarios
        enriched_data['metadata'] = {
            'bank_code': random.choice(['001', '002', '007', '009', '012']),
            'transaction_id': f"TXN-{random.randint(100000, 999999)}",
            'approval_code': f"APP-{random.randint(10000, 99999)}",
            'processing_time': f"{random.randint(5, 30)} seconds",
            'network_fee': round(random.uniform(1000, 5000), 2),
            'exchange_rate': "1.0" if enriched_data['method'] != 'USD' else str(round(random.uniform(4000, 4500), 2))
        }
        
        return enriched_data
    
    def simulate_bank_processing(self, purchase_order: PurchaseOrder, payment_data: dict) -> None:
        """Simula el procesamiento bancario del pago"""
        
        # ESTADO 1: PROCESSING_PAYMENT
        purchase_order.status = 'PROCESSING_PAYMENT'
        purchase_order.processing_payment_at = timezone.now()
        purchase_order.save(update_fields=['status', 'processing_payment_at'])
        
        logger.info(f"Starting bank payment processing for order {purchase_order.order_number}")
        
        # Simular tiempo de procesamiento bancario
        time.sleep(1)
        
        # ESTADO 2: PAID
        purchase_order.status = 'PAID'
        purchase_order.paid_at = timezone.now()
        purchase_order.save(update_fields=['status', 'paid_at'])
        
        logger.info(f"Bank payment completed for order {purchase_order.order_number}")
    
    def build_payment_result(self, purchase_order: PurchaseOrder, payment_data: dict) -> dict:
        """Construye el resultado del procesamiento de pago"""
        
        return {
            'success': True,
            'payment_method': payment_data['method'],
            'payment_reference': payment_data['reference'],
            'payment_metadata': payment_data['metadata'],
            'payment_processed_at': purchase_order.paid_at,
            'processing_started_at': purchase_order.processing_payment_at,
            'order_status': purchase_order.status
        }
