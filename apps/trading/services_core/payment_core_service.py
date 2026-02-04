from django.db import transaction
from typing import Dict, Any

from apps.trading.models.core_models import PurchaseOrder, OrderContract
from apps.trading.models.selection_models import MatchSelection
from apps.trading.services.payment_validator import PaymentValidator, PaymentValidationError
from apps.trading.services.payment_processor import PaymentProcessingService
from apps.trading.services.payment_finalizer import PaymentFinalizerService
from apps.trading.services_core.selection_service import MatchSelectionService
from apps.trading.services_core.transfer_service import TokenTransferService as CoreTokenTransferService


class PaymentCoreError(Exception):
    """Errores de orquestación de pago en services_core"""
    pass


class PaymentCoreService:
    """
    Core Payment Service (services_core)
    - Orquesta: selección activa → verificación de contratos → pago → transferencias → finalización
    - Delegación a servicios especializados
    - Usa selection_models como fuente de verdad (NO metadata)
    - Requiere aprobación de contratos antes de proceder
    """

    def __init__(self):
        self.validator = PaymentValidator()
        self.processor = PaymentProcessingService()
        self.finalizer = PaymentFinalizerService()
        self.selection_service = MatchSelectionService()
        self.transfer = CoreTokenTransferService()

    # ========================================
    # 1️⃣ MÉTODO PRINCIPAL: Ejecución de Pago
    # ========================================

    @transaction.atomic
    def execute_with_selection(
        self,
        purchase_order: PurchaseOrder,
        payment_data: Dict[str, Any],
        user,
        request=None
    ) -> Dict[str, Any]:
        """
        ✅ FLUJO PRINCIPAL: Ejecuta el flujo de pago completo
        
        Pasos:
        1. Obtener selección activa
        2. Verificar contratos aprobados
        3. Validar precondiciones de pago
        4. Procesar pago bancario
        5. Ejecutar transferencias de tokens
        6. Finalizar pago
        """
        # Paso 1: Obtener selección activa
        selection = self._get_active_selection_for_purchase_order(purchase_order)
        if not selection:
            raise PaymentCoreError("No hay una selección de matches activa para esta orden")

        # Paso 2: Verificar que los contratos estén aprobados
        self._verify_contracts_approved(selection)

        # Paso 3: Validaciones usando datos de modelos
        try:
            self.validator.validate_payment_execution(purchase_order)
            
            prepared_payment_data = self._prepare_payment_data_from_selection(selection, payment_data)
            
            self.validator.validate_payment_preconditions_from_selection(
                purchase_order, selection, prepared_payment_data
            )
            
        except PaymentValidationError as e:
            raise PaymentCoreError(str(e))

        # Variables para tracking
        payment_result = None
        transfer_result = None

        try:
            # Paso 4: Procesar pago bancario (ficticio)
            payment_result = self.processor.process_payment(purchase_order, prepared_payment_data)

            # Paso 5: Ejecutar transferencias de tokens
            transfer_result = self.transfer.execute_selection_transfers(purchase_order)

            # Paso 6: Evaluar resultado de transferencias
            total_transferred = transfer_result.get('total_transferred', 0)
            total_errors = transfer_result.get('total_errors', 0)
            selection_status = transfer_result.get('selection_final_status')
            
            print(f"🔍 Transfer result analysis:")
            print(f"   - Total transferred: {total_transferred}")
            print(f"   - Total errors: {total_errors}")
            print(f"   - Selection final status: {selection_status}")
            
            # Si hay transferencias exitosas (total o parcial)
            if total_transferred > 0:
                final_result = self.finalizer.finalize_payment(
                    purchase_order=purchase_order,
                    payment_result=payment_result,
                    transfer_result=transfer_result,
                    user=user,
                    request=request
                )
                
                # Indicar estado en respuesta
                if selection_status == 'PARTIALLY_COMPLETED' or total_errors > 0:
                    final_result['payment_status'] = 'partial_success'
                    final_result['warning'] = f'Pago parcialmente completado: {total_transferred} tokens transferidos, {total_errors} errores'
                    final_result['partial_completion'] = True
                else:
                    final_result['payment_status'] = 'success'
                    final_result['partial_completion'] = False
                
                return final_result
            else:
                raise PaymentCoreError(f"No se pudieron transferir tokens: {transfer_result.get('errors', [])}")

        except PaymentCoreError:
            raise
            
        except Exception as e:
            error_message = str(e)
            
            print(f"🔍 Exception caught: {error_message}")
            print(f"🔍 Transfer result when exception: {transfer_result}")
            
            # Manejo de errores con transferencias parciales
            if error_message in ['PARTIALLY_COMPLETED', 'COMPLETED', 'PROCESSING'] and transfer_result:
                total_transferred = transfer_result.get('total_transferred', 0)
                
                if total_transferred > 0:
                    try:
                        final_result = self.finalizer.finalize_payment(
                            purchase_order=purchase_order,
                            payment_result=payment_result or {
                                'success': True, 
                                'method': 'automatic',
                                'reference': f'PAY-{purchase_order.order_number}'
                            },
                            transfer_result=transfer_result,
                            user=user,
                            request=request
                        )
                        final_result['payment_status'] = 'partial_success'
                        final_result['warning'] = f'Algunos tokens no se transfirieron. Estado: {error_message}'
                        final_result['partial_completion'] = True
                        return final_result
                        
                    except Exception as finalize_error:
                        error_message = f"Error en finalización: {str(finalize_error)}"
            
            # Registrar error
            try:
                self.finalizer.handle_payment_error(purchase_order, error_message, user, request)
            except Exception:
                pass
            
            raise PaymentCoreError(f"Error en pago y transferencias: {error_message}")

    # ========================================
    # 2️⃣ MÉTODOS DE VALIDACIÓN
    # ========================================

    def _verify_contracts_approved(self, selection: MatchSelection) -> None:
        """
        ✅ Verifica que todos los contratos de la selección estén aprobados
        - Requiere contrato para cada item
        - Status debe ser APPROVED
        """
        selection_items = selection.items.select_related('purchase_order', 'sales_order').all()
        
        if not selection_items.exists():
            raise PaymentCoreError("No hay items en la selección para verificar contratos")
        
        pending_contracts = []
        missing_contracts = []
        
        for item in selection_items:
            contract = OrderContract.objects.filter(
                purchase_order=item.purchase_order,
                sales_order=item.sales_order
            ).first()
            
            if not contract:
                missing_contracts.append({
                    'purchase_order': item.purchase_order.order_number,
                    'sales_order': item.sales_order.order_number
                })
            elif contract.status != 'APPROVED':
                pending_contracts.append({
                    'contract_id': str(contract.id),
                    'status': contract.status,
                    'purchase_order': item.purchase_order.order_number,
                    'sales_order': item.sales_order.order_number
                })
        
        if missing_contracts:
            raise PaymentCoreError(
                f"Faltan {len(missing_contracts)} contrato(s). Primero se deben crear los contratos."
            )
        
        if pending_contracts:
            raise PaymentCoreError(
                f"{len(pending_contracts)} contrato(s) pendiente(s) de aprobación del administrador."
            )
        
        print(f"✅ Verificación de contratos exitosa: {len(selection_items)} contratos aprobados")

    # ========================================
    # 3️⃣ MÉTODOS DE PREPARACIÓN DE DATOS
    # ========================================

    def _prepare_payment_data_from_selection(
        self, 
        selection: MatchSelection, 
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ Prepara datos de pago desde MatchSelection (fuente de verdad)
        
        NO usa metadata de órdenes individuales
        """
        prepared_data = dict(payment_data or {})
        
        # Datos obligatorios desde el modelo
        prepared_data['amount'] = float(selection.total_amount)
        prepared_data['selection_id'] = str(selection.id)
        
        # Datos con defaults
        prepared_data.setdefault('method', 'automatic')
        prepared_data.setdefault('currency', 'COP')
        prepared_data.setdefault('metadata', {})
        
        # Enriquecer para auditoría
        prepared_data['metadata'].update({
            'selection_total_units': selection.total_units,
            'selection_expected_savings': float(selection.expected_savings),
            'selection_items_count': selection.items.count(),
            'selection_status': selection.status,
            'selection_expires_at': selection.expires_at.isoformat(),
            'payment_source': 'selection_model',
        })
        
        return prepared_data

    # ========================================
    # 4️⃣ MÉTODOS DE INFORMACIÓN / CONSULTAS
    # ========================================

    def get_payment_validation_info(self, purchase_order: PurchaseOrder) -> Dict[str, Any]:
        """
        ✅ Obtiene información COMPLETA para validación de pago
        - Busca selección activa
        - Verifica estado de contratos
        - Retorna info detallada para UI
        """
        try:
            # Buscar selección activa
            selection = self._get_active_selection_for_purchase_order(purchase_order)
            
            if not selection:
                return {
                    'can_pay': False,
                    'reason': 'no_selection',
                    'message': 'No hay selección de matches activa',
                    'order_number': purchase_order.order_number,
                    'order_id': str(purchase_order.id),
                    'status': purchase_order.status,
                    'ready_for_payment': False,
                    'has_active_selection': False,
                    'action_required': 'select_matches'
                }
            
            # Verificar expiración
            if selection.is_expired:
                return {
                    'can_pay': False,
                    'reason': 'expired',
                    'message': 'La selección de matches ha expirado',
                    'order_number': purchase_order.order_number,
                    'order_id': str(purchase_order.id),
                    'ready_for_payment': False,
                    'has_active_selection': False,
                    'action_required': 'select_new_matches',
                    'expired_at': selection.expires_at.isoformat()
                }
            
            # Verificar contratos
            try:
                self._verify_contracts_approved(selection)
                contracts_approved = True
                contracts_message = None
            except PaymentCoreError as e:
                contracts_approved = False
                contracts_message = str(e)
            
            # Información de items
            po_items = selection.items.filter(purchase_order=purchase_order)
            po_total_amount = sum(item.total_amount for item in po_items)
            po_total_units = sum(item.units for item in po_items)
            
            return {
                'can_pay': contracts_approved,
                'reason': 'pending_contracts' if not contracts_approved else 'ready',
                'message': contracts_message if not contracts_approved else 'Listo para pagar',
                'order_number': purchase_order.order_number,
                'order_id': str(purchase_order.id),
                'status': purchase_order.status,
                'ready_for_payment': contracts_approved,
                'has_active_selection': True,
                'selection_id': str(selection.id),
                'total_amount': float(po_total_amount),
                'total_units': po_total_units,
                'matches_count': po_items.count(),
                'expires_at': selection.expires_at.isoformat(),
                'is_expired': False,
                'fund_name': purchase_order.fund.name,
                'contracts_status': 'approved' if contracts_approved else 'pending',
                'action_required': 'approve_contracts' if not contracts_approved else 'proceed_payment'
            }
            
        except Exception as e:
            return {
                'can_pay': False,
                'reason': 'validation_error',
                'message': f'Error: {str(e)}',
                'order_number': purchase_order.order_number,
                'order_id': str(purchase_order.id),
                'ready_for_payment': False,
                'action_required': 'check_error'
            }

    # ========================================
    # 5️⃣ MÉTODOS AUXILIARES
    # ========================================

    def _get_active_selection_for_purchase_order(self, purchase_order: PurchaseOrder) -> MatchSelection:
        """
        ✅ Busca selecciones ACTIVAS que incluyan esta purchase order
        - Limpia automáticamente selecciones expiradas
        - Retorna None si no encuentra
        """
        try:
            selection = MatchSelection.objects.filter(
                items__purchase_order=purchase_order,
                status__in=['ACTIVE', 'PROCESSING']
            ).select_related('sales_order').prefetch_related(
                'items__purchase_order',
                'items__sales_order'
            ).first()
            
            print(f"🔍 Selection found: {selection.id if selection else 'None'}")
            if selection:
                print(f"🔍 Selection status: {selection.status}, items: {selection.items.count()}")
            
            # Limpiar selecciones expiradas
            if selection and selection.is_expired:
                selection.status = 'EXPIRED'
                selection.save(update_fields=['status'])
                return None
                
            return selection
            
        except Exception as e:
            print(f"❌ Error buscando selección activa: {str(e)}")
            raise
        