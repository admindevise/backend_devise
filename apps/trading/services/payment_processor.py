from django.utils import timezone
from typing import Dict, Any
from decimal import Decimal
import random
import time

from apps.trading.models.core_models import PurchaseOrder
from apps.trading.models.selection_models import PaymentRecord

class PaymentProcessingService:
    """
    Servicio de Procesamiento de Pagos - Maneja solo el pago bancario (ficticio)
    
    Responsabilidades:
    - Generar datos ficticios de pago bancario
    - Simular procesamiento bancario
    - Actualizar estados relacionados con el pago
    """
    
    def process_payment(self, purchase_order: PurchaseOrder, payment_data: dict) -> dict:
        """Procesa el pago bancario completo y registra PaymentRecord"""
        # 1. Preparar/enriquecer datos
        enriched_payment_data = self.prepare_payment_data(payment_data, purchase_order)

        # 2. Crear PaymentRecord (INITIATED)
        amount = Decimal(str(enriched_payment_data.get('amount') or purchase_order.total_amount))
        payment_record = PaymentRecord.objects.create(
            purchase_order=purchase_order,
            amount=amount,
            payment_method=enriched_payment_data.get('method') or 'automatic',
            reference=enriched_payment_data.get('reference') or f"REF-{int(time.time())}",
            status=PaymentRecord.PaymentStatus.INITIATED,
            metadata={'request': enriched_payment_data.get('metadata', {})}
        )

        try:
            # 3. Marcar PROCESSING y simular banco
            payment_record.status = PaymentRecord.PaymentStatus.PROCESSING
            payment_record.save(update_fields=['status'])

            self.simulate_bank_processing(purchase_order, enriched_payment_data)

            # 4. Completar PaymentRecord
            payment_record.status = PaymentRecord.PaymentStatus.COMPLETED
            payment_record.processed_at = purchase_order.paid_at or timezone.now()
            payment_record.completed_at = timezone.now()
            # Datos bancarios ficticios
            record_meta = payment_record.metadata or {}
            record_meta.update(enriched_payment_data.get('metadata', {}))
            payment_record.metadata = record_meta
            payment_record.bank_transaction_id = enriched_payment_data['metadata'].get('transaction_id')
            payment_record.bank_reference = enriched_payment_data['reference']
            payment_record.save(update_fields=[
                'status', 'processed_at', 'completed_at',
                'metadata', 'bank_transaction_id', 'bank_reference'
            ])

            # 5. Construir respuesta
            result = self.build_payment_result(purchase_order, enriched_payment_data)
            result['payment_record'] = {
                'id': payment_record.id,
                'status': payment_record.status,
                'reference': payment_record.reference,
                'processed_at': payment_record.processed_at,
                'completed_at': payment_record.completed_at,
            }
            return result

        except Exception as e:
            # Marcar FAILED
            payment_record.status = PaymentRecord.PaymentStatus.FAILED
            payment_record.failed_at = timezone.now()
            record_meta = payment_record.metadata or {}
            record_meta.update({'error': str(e)})
            payment_record.metadata = record_meta
            payment_record.save(update_fields=['status', 'failed_at', 'metadata'])
            raise
        
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


    # =========================
    # Helpers internos
    # =========================

    def prepare_payment_data(self, payment_data: Dict[str, Any], purchase_order: PurchaseOrder) -> Dict[str, Any]:
        """
        Enrich: method, reference, amount y metadata mínima.
        - amount: prioritiza payment_data.amount; fallback a metadata.selection_summary.total_amount; por último, 0.
        """
        data = dict(payment_data or {})

        # Método por defecto
        data.setdefault('method', 'automatic')

        # Referencia por defecto
        default_ref_base = getattr(purchase_order, 'order_number', str(purchase_order.id))
        data.setdefault('reference', f"PAY-{default_ref_base}-{int(time.time())}")

        # Metadata base
        meta = data.get('metadata') or {}
        if not isinstance(meta, dict):
            meta = {'raw_metadata': str(meta)}
        meta.setdefault('requested_at', timezone.now().isoformat())
        data['metadata'] = meta

        # Amount
        amount = data.get('amount')
        if amount is None:
            # Intentar desde metadata de la orden (selection_summary.total_amount)
            try:
                if purchase_order.metadata and purchase_order.metadata.get('selection_summary'):
                    amount = purchase_order.metadata['selection_summary'].get('total_amount')
            except Exception:
                amount = None
        # Normalizar a Decimal en el caller (process_payment) para persistencia
        data['amount'] = amount

        return data

    def simulate_bank_processing(self, purchase_order: PurchaseOrder, payment_data: Dict[str, Any]) -> None:
        """
        Simula el procesamiento bancario:
        - Cambia estado de la orden a PROCESSING_PAYMENT -> PAID
        - Setea timestamps processing_payment_at y paid_at
        - Genera un transaction_id ficticio en payment_data['metadata']
        """
        # Estados seguros
        status_cls = getattr(PurchaseOrder, 'PurchaseOrderStatus', None)
        processing_status = getattr(status_cls, 'PROCESSING_PAYMENT', 'PROCESSING_PAYMENT') if status_cls else 'PROCESSING_PAYMENT'
        paid_status = getattr(status_cls, 'PAID', 'PAID') if status_cls else 'PAID'

        # A PROCESSING_PAYMENT
        purchase_order.status = processing_status
        purchase_order.processing_payment_at = timezone.now()
        try:
            purchase_order.save(update_fields=['status', 'processing_payment_at'])
        except Exception:
            purchase_order.save()

        # Simulación de latencia bancaria corta
        time.sleep(random.uniform(0.05, 0.15))

        # Resultado "aprobado" + transaction_id
        tx_id = f"BNK-{int(time.time())}-{random.randint(1000, 9999)}"
        payment_data.setdefault('metadata', {})
        payment_data['metadata']['transaction_id'] = tx_id

        # A PAID
        purchase_order.status = paid_status
        purchase_order.paid_at = timezone.now()
        try:
            purchase_order.save(update_fields=['status', 'paid_at'])
        except Exception:
            purchase_order.save()