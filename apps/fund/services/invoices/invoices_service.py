"""
Servicio simplificado para gestión de InvoiceRecord
"""

from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from apps.audit.audit_service import AuditService
from apps.fund.models.core import Fund
from apps.fund.models.accounting import InvoiceRecord


class InvoiceRecordService:
    """
    Servicio para operaciones de InvoiceRecord
    Responsabilidades:
    - Crear, actualizar y eliminar registros de facturas
    - Consultar facturas por diversos criterios
    """
    
    @staticmethod
    @transaction.atomic
    def create_invoice_record(user, invoice_data: Dict[str, Any], request=None) -> InvoiceRecord:
        """Crear un nuevo registro de factura"""
        initial_audit = None
        #print("Creating invoice record with data:", invoice_data)
        try:
            # Generar número de factura si no viene en los datos
            if 'invoice_number' not in invoice_data or not invoice_data.get('invoice_number'):
                invoice_data['invoice_number'] = InvoiceRecordService.generate_invoice_number(
                        invoice_data['fund']
                    )
            
            # Calcular monto total
            invoice_data['total_amount'] = InvoiceRecordService.calculate_total_amount(invoice_data)

            # Guarda el log inicial (antes de crear la factura)
            initial_audit = InvoiceRecordService.initial_audit_log_invoice_action(
                user=user,
                invoice_data=invoice_data,
                action_code="INVOICE_RECORD_CREATE",
                request=request
            )

            invoice_record = InvoiceRecord.objects.create(**invoice_data)

            if initial_audit:
                InvoiceRecordService.update_audit_log_invoice_success(initial_audit, invoice_record)

            return invoice_record
        
        except Exception as e:
            # Actualizar auditoría a error
            if initial_audit:
                InvoiceRecordService.update_audit_log_invoice_error(initial_audit, e)
            raise 
        
    # ==================================
    # FUNCIONES AUXILIARES
    # ==================================
    @staticmethod
    def generate_invoice_number(fund: Fund) -> str:
        """
        Genera un número de factura único para un fondo dado.
        Formato: INV-{DDMMYY}-{FUND_ID}-{SECUENCIAL}
        """
        from django.db.models import Max
        
        today_str = timezone.now().strftime("%d%m%y")
        
        # Obtener el último número secuencial usado hoy para este fondo
        last_invoice = InvoiceRecord.objects.filter(
            fund=fund,
            issued_date__date=timezone.now().date()
        ).aggregate(Max('invoice_number'))
        
        if last_invoice['invoice_number__max']:
            last_number = int(last_invoice['invoice_number__max'].split('-')[-1])
            new_sequential = last_number + 1
        else:
            new_sequential = 1
        
        return f"INV-{today_str}-{fund.id}-{new_sequential:04d}"
    
    @staticmethod
    def calculate_total_amount(invoice_data: Dict[str, Any]) -> float:
        """
        Calcula el monto total de la factura basado en el subtotal y los impuestos.
        """
        return invoice_data.get('subtotal', 0.0) + invoice_data.get('value_iva', 0.0) - invoice_data.get('withholding_tax', 0.0) - invoice_data.get('ica_withholding_tax', 0.0)
    
    # ==================================
    # AUDITORÍA
    # ==================================
    @staticmethod
    def initial_audit_log_invoice_action(user, invoice_data: Dict[str, Any], action_code: str, request) -> Optional[Any]:
        """Crea un log de auditoría inicial con estado pendiente para acciones de InvoiceRecord."""
        if not request:
            return None
        
        fund = invoice_data.get('fund')
        
        return AuditService.log_action(
            request=request,
            action_code=action_code,
            obj=user,  # Temporalmente usa user
            details={
                "user_email": getattr(user, "email", "anonymous"),
                "fund_name": fund.name if fund else 'N/A',
                "invoice_number": invoice_data.get('invoice_number', 'N/A'),
            },
            status="PENDING",
        )
        
    @staticmethod
    def update_audit_log_invoice_success(audit_log, invoice_record: InvoiceRecord):
        """Actualiza el log de auditoría con información de éxito para acciones de InvoiceRecord."""
        if not audit_log:
            return
        
        # Actualizar el objeto auditado
        audit_log.content_type = ContentType.objects.get_for_model(invoice_record)
        audit_log.object_id = str(invoice_record.id)
        audit_log.status = 'SUCCESS'
        
        # Agregar detalles adicionales
        audit_log.details.update({
            'invoice_id': str(invoice_record.id),
            'invoice_number': invoice_record.invoice_number,
            'total_amount': str(invoice_record.total_amount),
        })
        
        audit_log.save(update_fields=['content_type', 'object_id', 'status', 'details'])
    
    @staticmethod
    def update_audit_log_invoice_error(audit_log, error):
        """Actualiza el log de auditoría con información del error para acciones de InvoiceRecord."""
        if not audit_log:
            return
            
        audit_log.status = 'ERROR'
        audit_log.details.update({
            'error': str(error),
            'error_type': type(error).__name__,
        })
        
        audit_log.save(update_fields=['status', 'details'])
    
    