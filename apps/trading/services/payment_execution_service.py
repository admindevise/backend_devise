from django.db import transaction
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
import logging

from apps.trading.models import PurchaseOrder, SalesOrder, Transaction
from apps.fund.models import FundToken
from apps.kaleido.utils import safe_transfer_721
from apps.trading.security.token_validators import TokenReservationManager
from apps.audit.audit_service import AuditService

# Nuevos servicios especializados
from apps.trading.services.payment_validator import PaymentValidator, PaymentValidationError
from apps.trading.services.payment_processor import PaymentProcessingService
from apps.trading.services.token_transfer_service import TokenTransferService, TokenTransferError
from apps.trading.services.payment_finalizer import PaymentFinalizerService

logger = logging.getLogger('trading.payment_execution')

class PaymentExecutionError(Exception):
    """Excepción personalizada para errores de ejecución de pagos"""
    pass

class PaymentExecutionService:
    """
    🏦 Servicio Orquestador de Ejecución de Pagos - Coordina el flujo completo
    
    Responsabilidades:
    - Orquestar el flujo completo de pago
    - Coordinar validación, pago, transferencias y finalización
    - Manejo unificado de errores
    - Proporcionar interfaz simple para el exterior
    """
    
    def __init__(self):
        # Servicios especializados
        self.validator = PaymentValidator()
        self.payment_processor = PaymentProcessingService()
        self.token_transfer = TokenTransferService()
        self.finalizer = PaymentFinalizerService()
        
        # Mantener compatibilidad con código existente
        self.reservation_manager = TokenReservationManager()
        self.payment_methods = self.payment_processor.payment_methods
    
    # ========================================
    # MÉTODO PRINCIPAL SIMPLIFICADO
    # ========================================
    
    @transaction.atomic
    def execute_payment_and_matches(
        self, 
        purchase_order: PurchaseOrder, 
        payment_data: Dict[str, Any], 
        user, 
        request=None
    ) -> Dict[str, Any]:
        """
        Ejecuta el pago completo y todas las transacciones seleccionadas
        
        Args:
            purchase_order: Orden de compra con matches seleccionados
            payment_data: Datos del pago (método, referencia, etc.)
            user: Usuario que ejecuta el pago
            request: Request HTTP para auditoría
            
        Returns:
            Dict con resultados completos de la ejecución
            
        Raises:
            PaymentExecutionError: Si hay errores en la ejecución
        """
        try:
            logger.info(f"Starting payment execution for order {purchase_order.order_number}")
            
            # 1. VALIDACIÓN
            self.validator.validate_payment_execution(purchase_order)
            
            # Verificar nuevamente el estado después de validaciones
            purchase_order.refresh_from_db()
            if purchase_order.status == 'PENDING':
                raise PaymentExecutionError(
                    'La orden ha sido revertida a PENDING durante las validaciones. '
                    'Posiblemente la selección expiró.'
                )
            
            # 2. ENRIQUECER DATOS DE PAGO
            enriched_payment_data = self._enrich_payment_data(purchase_order, payment_data)
            
            # 3. VALIDAR PRECONDICIONES DE PAGO
            self.validator.validate_payment_preconditions(purchase_order, enriched_payment_data)
            
            # 4. PROCESAR PAGO BANCARIO
            payment_result = self.payment_processor.process_payment(purchase_order, enriched_payment_data)
            
            # 5. EJECUTAR TRANSFERENCIAS DE TOKENS
            transfer_result = self.token_transfer.execute_transfers(purchase_order)
            
            # 6. FINALIZAR Y AUDITAR
            final_result = self.finalizer.finalize_payment(
                purchase_order, payment_result, transfer_result, user, request
            )
            
            logger.info(f"Payment execution completed successfully for order {purchase_order.order_number}")
            return final_result
            
        except (PaymentValidationError, TokenTransferError) as e:
            # Errores de validación y transferencia - no registrar como errores internos
            logger.warning(f"Payment execution validation error for order {purchase_order.order_number}: {str(e)}")
            raise PaymentExecutionError(str(e))
            
        except Exception as e:
            # Errores inesperados - registrar y manejar
            logger.error(f"Unexpected error in payment execution for order {purchase_order.order_number}: {str(e)}")
            self.finalizer.handle_payment_error(purchase_order, str(e), user, request)
            raise PaymentExecutionError(f"Error en ejecución de pago: {str(e)}")
    
    def _enrich_payment_data(self, purchase_order: PurchaseOrder, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquece los datos de pago con información automática"""
        
        enriched_data = payment_data.copy()
        
        # Extraer información de selección
        selection_info = self._extract_selection_info(purchase_order)
        
        # Usar monto de la selección si no se especifica
        if 'amount' not in enriched_data:
            enriched_data['amount'] = selection_info['total_amount']
        
        # Generar referencia automática si no existe
        if 'reference' not in enriched_data:
            enriched_data['reference'] = f'PAY-{purchase_order.order_number}'
        
        # Método automático si no se especifica
        if 'method' not in enriched_data:
            enriched_data['method'] = 'automatic'
        
        # Enriquecer metadata
        metadata = enriched_data.get('metadata', {})
        metadata.update({
            'auto_extracted_amount': True,
            'selection_summary': selection_info,
            'payment_date': timezone.now().isoformat(),
            'order_number': purchase_order.order_number
        })
        enriched_data['metadata'] = metadata
        
        return enriched_data
    
    def _extract_selection_info(self, purchase_order: PurchaseOrder) -> Dict[str, Any]:
        """Extrae información de la selección de matches"""
        try:
            selection_summary = purchase_order.metadata['selection_summary']
            return {
                'total_amount': float(str(selection_summary['total_amount'])),
                'total_units': selection_summary.get('total_units', 0),
                'matches_count': len(purchase_order.metadata.get('selected_matches', [])),
                'expires_at': selection_summary.get('expires_at'),
                'savings': selection_summary.get('savings', 0)
            }
        except KeyError as e:
            raise PaymentExecutionError(f'Información de selección incompleta: {str(e)}')
    
    # ========================================
    # MÉTODOS DE COMPATIBILIDAD (OBSOLETOS)
    # ========================================
    
    # Los siguientes métodos se mantienen temporalmente para compatibilidad
    # pero deben ser reemplazados por los nuevos servicios especializados
    
    def _process_payment(
        self, 
        purchase_order: PurchaseOrder, 
        payment_data: Dict[str, Any], 
        request=None
    ) -> Dict[str, Any]:
        """
        OBSOLETO: Usar payment_processor.process_payment() directamente
        Mantenido solo para compatibilidad con código existente
        """
        logger.warning("Using deprecated _process_payment method. Consider using payment_processor.process_payment() directly.")
        return self.payment_processor.process_payment(purchase_order, payment_data)
    
    def _validate_payment_execution(self, purchase_order: PurchaseOrder) -> None:
        """
        OBSOLETO: Usar validator.validate_payment_execution() directamente
        Mantenido solo para compatibilidad con código existente
        """
        logger.warning("Using deprecated _validate_payment_execution method. Consider using validator.validate_payment_execution() directly.")
        return self.validator.validate_payment_execution(purchase_order)
    
    # ========================================
    # MÉTODOS COMPLETAMENTE OBSOLETOS
    # ========================================
    
    # Los siguientes métodos ya NO se usan en el flujo principal
    # y serán eliminados en futuras versiones
    
    def _finalize_purchase_order_simple(self, purchase_order: PurchaseOrder) -> None:
        """OBSOLETO: Funcionalidad movida a PaymentFinalizerService"""
        logger.warning("Method _finalize_purchase_order_simple is obsolete")
        pass
    
    def _log_success_audit_simple(self, purchase_order: PurchaseOrder, payment_result: Dict[str, Any], user, request=None) -> None:
        """OBSOLETO: Funcionalidad movida a PaymentFinalizerService"""
        logger.warning("Method _log_success_audit_simple is obsolete")
        pass
    
    def _build_success_response_simple(self, purchase_order: PurchaseOrder, payment_result: Dict[str, Any], selection_info: Dict[str, Any]) -> Dict[str, Any]:
        """OBSOLETO: Funcionalidad movida a PaymentFinalizerService"""
        logger.warning("Method _build_success_response_simple is obsolete")
        return {
            'success': True,
            'message': 'Payment processed successfully (using deprecated method)',
            'warning': 'This method is obsolete and will be removed'
        }
    
    def _log_error_audit(self, purchase_order: PurchaseOrder, error_msg: str, user, request=None) -> None:
        """OBSOLETO: Funcionalidad movida a PaymentFinalizerService"""
        logger.warning("Method _log_error_audit is obsolete")
        self.finalizer.handle_payment_error(purchase_order, error_msg, user, request)
