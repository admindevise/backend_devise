from django.db import transaction
from typing import Dict, Any

from apps.trading.models.core_models import PurchaseOrder
from apps.trading.models.selection_models import MatchSelection  # ← Agregado
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

    @transaction.atomic
    def execute_with_selection(
        self,
        purchase_order: PurchaseOrder,
        payment_data: Dict[str, Any],
        user,
        request=None
    ) -> Dict[str, Any]:
        """
        Ejecuta el flujo de pago completo usando la selección activa del PurchaseOrder.
        """
        # 1) Obtener selección activa (limpia expiradas automáticamente)
        selection = self._get_active_selection_for_purchase_order(purchase_order)
        if not selection:
            raise PaymentCoreError("No hay una selección de matches activa para esta orden")

        # 2) Verificar que los contratos estén aprobados
        self._verify_contracts_approved(selection)

        # 3) Validaciones mínimas usando datos de modelos
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
            # 4) Pago bancario (ficticio) - usando datos de modelo
            payment_result = self.processor.process_payment(purchase_order, prepared_payment_data)

            # 5) Transferencias reales de tokens (basadas en selección activa)
            transfer_result = self.transfer.execute_selection_transfers(purchase_order)

            # 6) ✅ EVALUAR RESULTADO DE TRANSFERENCIAS CORRECTAMENTE
            total_transferred = transfer_result.get('total_transferred', 0)
            total_errors = transfer_result.get('total_errors', 0)
            selection_status = transfer_result.get('selection_final_status')
            
            print(f"🔍 Transfer result analysis:")
            print(f"   - Total transferred: {total_transferred}")
            print(f"   - Total errors: {total_errors}")
            print(f"   - Selection final status: {selection_status}")
            
            # ✅ PARTIALLY_COMPLETED es un ÉXITO PARCIAL, no un error
            if total_transferred > 0:
                # 7) Finalización exitosa (total o parcial)
                final_result = self.finalizer.finalize_payment(
                    purchase_order=purchase_order,
                    payment_result=payment_result,
                    transfer_result=transfer_result,
                    user=user,
                    request=request
                )
                
                # ✅ INDICAR ESTADO EN LA RESPUESTA
                if selection_status == 'PARTIALLY_COMPLETED' or total_errors > 0:
                    final_result['payment_status'] = 'partial_success'
                    final_result['warning'] = f'Pago completado parcialmente: {total_transferred} tokens transferidos, {total_errors} errores'
                    final_result['partial_completion'] = True
                else:
                    final_result['payment_status'] = 'success'
                    final_result['partial_completion'] = False
                
                return final_result
            else:
                # Sin transferencias exitosas - fallo total
                raise PaymentCoreError(f"No se pudieron transferir tokens: {transfer_result.get('errors', [])}")

        except PaymentCoreError:
            # Re-lanzar errores de core sin modificar
            raise
            
        except Exception as e:
            # ✅ MANEJO MEJORADO: No tratar estados de selección como errores
            error_message = str(e)
            
            print(f"🔍 Exception caught: {error_message}")
            print(f"🔍 Transfer result when exception: {transfer_result}")
            
            # Si el error es solo un estado de selección válido, verificar si hubo transferencias
            if error_message in ['PARTIALLY_COMPLETED', 'COMPLETED', 'PROCESSING'] and transfer_result:
                total_transferred = transfer_result.get('total_transferred', 0)
                
                if total_transferred > 0:
                    # Hubo transferencias exitosas - considerar éxito parcial
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
                        final_result['warning'] = f'Algunos tokens no se pudieron transferir. Estado de selección: {error_message}'
                        final_result['partial_completion'] = True
                        return final_result
                        
                    except Exception as finalize_error:
                        error_message = f"Error en finalización después de transferencias parciales: {str(finalize_error)}"
            
            # Registrar error y limpiar estado solo para errores reales
            try:
                self.finalizer.handle_payment_error(purchase_order, error_message, user, request)
            except Exception:
                pass  # No fallar por problemas de auditoría
            
            raise PaymentCoreError(f"Error ejecutando pago y transferencias: {error_message}")


    def _verify_contracts_approved(self, selection: MatchSelection) -> None:
        """
        Verifica que todos los contratos relacionados con la selección estén aprobados.
        Solo procede al pago si el admin ha aprobado los documentos.
        """
        from apps.trading.models.core_models import OrderContract
        
        # Obtener todos los contratos relacionados con la selección
        selection_items = selection.items.select_related('purchase_order', 'sales_order').all()
        
        if not selection_items.exists():
            raise PaymentCoreError("No hay items en la selección para verificar contratos")
        
        pending_contracts = []
        missing_contracts = []
        
        for item in selection_items:
            # Buscar contrato entre purchase_order y sales_order
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
        
        # Validar que todos los contratos existan y estén aprobados
        if missing_contracts:
            raise PaymentCoreError(
                f"Faltan contratos para proceder al pago. "
                f"Contratos faltantes: {len(missing_contracts)}. "
                f"Primero se deben crear los contratos para todas las órdenes."
            )
        
        if pending_contracts:
            raise PaymentCoreError(
                f"No se puede proceder al pago. Hay {len(pending_contracts)} contratos pendientes de aprobación del administrador. "
                f"Estados encontrados: {[c['status'] for c in pending_contracts]}"
            )
        
        print(f"✅ Verificación de contratos exitosa: {len(selection_items)} contratos aprobados")

    def _prepare_payment_data_from_selection(
        self, 
        selection: MatchSelection, 
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepara datos de pago usando el modelo MatchSelection como fuente de verdad.
        NO usa metadata de órdenes.
        """
        # ✅ FUENTE DE VERDAD: Usar campos del modelo MatchSelection
        prepared_data = dict(payment_data or {})
        
        # Datos obligatorios desde el modelo
        prepared_data['amount'] = float(selection.total_amount)
        prepared_data['selection_id'] = str(selection.id)
        
        # Datos opcionales con defaults
        prepared_data.setdefault('method', 'automatic')
        prepared_data.setdefault('currency', 'COP')
        prepared_data.setdefault('metadata', {})
        
        # ✅ ENRIQUECER: Agregar información de la selección para auditoría
        prepared_data['metadata'].update({
            'selection_total_units': selection.total_units,
            'selection_expected_savings': float(selection.expected_savings),
            'selection_items_count': selection.items.count(),
            'selection_status': selection.status,
            'selection_expires_at': selection.expires_at.isoformat(),
            'payment_source': 'selection_model',  # Indicar fuente de datos
        })
        
        return prepared_data

    def get_payment_validation_info(self, purchase_order: PurchaseOrder) -> Dict[str, Any]:
        """
        Obtiene información para validación de pago usando modelos como fuente de verdad.
        Reemplaza la dependencia en metadata.
        """
        # 1. Verificar selección activa
        selection = self._get_active_selection_for_purchase_order(purchase_order)
        if not selection:
            return {
                'can_pay': False,
                'reason': 'no_active_selection',
                'message': 'No hay una selección de matches activa para esta orden'
            }
            
        # 2. Verificar estado de contratos
        try:
            self._verify_contracts_approved(selection)
            contracts_status = 'approved'
            contracts_message = 'Todos los contratos están aprobados'
        except PaymentCoreError as e:
            contracts_status = 'pending'
            contracts_message = str(e)
        
        # 3. ✅ INFORMACIÓN DESDE MODELOS: No metadata
        selection_items = selection.items.select_related(
            'purchase_order', 'sales_order'
        ).all()
        
        items_detail = []
        for item in selection_items:
            items_detail.append({
                'purchase_order_number': item.purchase_order.order_number,
                'sales_order_number': item.sales_order.order_number,
                'units': item.units,
                'price_per_unit': float(item.price_per_unit),
                'total_amount': float(item.units * item.price_per_unit),
                'buyer_savings': float(item.buyer_savings),
                'seller_gain': float(item.seller_gain)
            })
        
        return {
            'can_pay': contracts_status == 'approved',
            'reason': contracts_status,
            'message': contracts_message,
            'order_details': {
                'order_id': str(purchase_order.id),
                'order_number': purchase_order.order_number,
                'order_status': purchase_order.status,
                'buyer_email': purchase_order.supplier_user.email,
            },
            'selection_summary': {
                'selection_id': str(selection.id),
                'total_amount': float(selection.total_amount),
                'total_units': selection.total_units,
                'expected_savings': float(selection.expected_savings),
                'status': selection.status,
                'expires_at': selection.expires_at.isoformat(),
                'items_count': len(items_detail),
                'time_remaining_seconds': selection.time_remaining.total_seconds()
            },
            'items_detail': items_detail,
            'contracts_status': contracts_status
        }

    def get_payment_validation_info(self, purchase_order: PurchaseOrder) -> Dict[str, Any]:
        """
        ✅ NUEVO: Obtiene información completa de validación de pago
        """
        try:
            # 1. Buscar selección activa
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
                    'warning': 'No hay selección de matches activa.',
                    'action_required': 'select_matches'
                }
            
            # 2. Verificar expiración
            if selection.is_expired:
                return {
                    'can_pay': False,
                    'reason': 'expired',
                    'message': 'La selección de matches ha expirado',
                    'order_number': purchase_order.order_number,
                    'order_id': str(purchase_order.id),
                    'status': purchase_order.status,
                    'ready_for_payment': False,
                    'has_active_selection': False,
                    'warning': 'La selección ha expirado.',
                    'action_required': 'select_new_matches',
                    'selection_id': str(selection.id),
                    'expired_at': selection.expires_at.isoformat()
                }
            
            # 3. Verificar contratos aprobados
            try:
                self._verify_contracts_approved(selection)
                contracts_approved = True
                contracts_message = None
            except PaymentCoreError as e:
                contracts_approved = False
                contracts_message = str(e)
            
            # 4. Información completa para selección válida
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
                'selection_created_by': selection.sales_order.seller_user.email if selection.sales_order else 'Unknown',
                'contracts_status': 'approved' if contracts_approved else 'pending',
                'warning': contracts_message if not contracts_approved else None,
                'action_required': 'approve_contracts' if not contracts_approved else 'proceed_payment'
            }
            
        except Exception as e:
            return {
                'can_pay': False,
                'reason': 'validation_error',
                'message': f'Error en validación: {str(e)}',
                'order_number': purchase_order.order_number,
                'order_id': str(purchase_order.id),
                'status': purchase_order.status,
                'ready_for_payment': False,
                'has_active_selection': False,
                'warning': f'Error en validación: {str(e)}',
                'action_required': 'check_error'
            }

    # =========================
    # Métodos legacy (compatibilidad)
    # =========================

    def _ensure_minimum_payment_data(self, selection, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ⚠️ DEPRECATED: Usar _prepare_payment_data_from_selection() en su lugar.
        Método de compatibilidad con código legacy.
        """
        data = dict(payment_data or {})
        data.setdefault('method', 'automatic')
        # reference es generado por el processor si no viene (opcional)
        data.setdefault('amount', float(selection.total_amount) if hasattr(selection, 'total_amount') else None)
        # útil para trazabilidad
        data.setdefault('selection_id', str(selection.id))
        data.setdefault('metadata', data.get('metadata', {}))
        return data
    

    def _get_active_selection_for_purchase_order(self, purchase_order: PurchaseOrder) -> MatchSelection:
        """
        Busca selecciones activas que incluyan esta purchase order en sus items.
        """
        try:
            from apps.trading.models.selection_models import MatchSelection
            
            # Buscar selecciones que incluyan esta purchase order en sus items
            selection = MatchSelection.objects.filter(
                items__purchase_order=purchase_order,
                status__in=['ACTIVE', 'PROCESSING']  # ✅ Permitir PROCESSING también
            ).select_related('sales_order').prefetch_related(
                'items__purchase_order',
                'items__sales_order'
            ).first()
            
            print(f"🔍 Selection found: {selection.id if selection else 'None'}")
            if selection:
                print(f"🔍 Selection status: {selection.status}")
                print(f"🔍 Selection items count: {selection.items.count()}")
            
            # Verificar que no esté expirada
            if selection and selection.is_expired:
                selection.status = 'EXPIRED'
                selection.save(update_fields=['status'])
                return None
                
            return selection
            
        except Exception as e:
            print(f"❌ Error buscando selección activa: {str(e)}")
            return None