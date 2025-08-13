from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal
import requests

from apps.trading.models.selection_models import MatchSelection, MatchSelectionItem
from apps.trading.models.core_models import PurchaseOrder, SalesOrder
from apps.trading.models.core_models import OrderContract
from apps.trading.order_matching import OrderMatch
from apps.audit.audit_service import AuditService

class SelectionServiceError(Exception):
    """Excepción personalizada para errores en SelectionService"""
    pass

class InsufficientUnitsWarning(Exception):
    """Excepción para advertir sobre unidades insuficientes"""
    def __init__(self, message, available_units, warning_data):
        super().__init__(message)
        self.available_units = available_units
        self.warning_data = warning_data

class MatchSelectionCore:
    """Core compartido para servicios de selección de matches"""
    
    def __init__(self):
        self.matcher = OrderMatch()
        self.selection_expiry_minutes = 15
    
    # ========================================
    # VALIDACIONES COMPARTIDAS
    # ========================================
    
    def _validate_selection_request_base(
        self,
        order: Union[PurchaseOrder, SalesOrder],
        selected_matches: List[Dict[str, Any]],
        user
    ) -> None:
        """Validaciones base para cualquier tipo de selección"""
        
        # Verificar estado de la orden
        if order.status not in ['PENDING', 'PARTIALLY_EXECUTED']:
            raise SelectionServiceError(
                f'La orden debe estar PENDING o PARTIALLY_EXECUTED. Estado actual: {order.status}'
            )
        
        # Validar formato de selecciones para selección manual
        if selected_matches is not None and isinstance(selected_matches, list) and len(selected_matches) > 0:
            for i, match in enumerate(selected_matches):
                if not isinstance(match, dict):
                    raise SelectionServiceError(f'Match {i+1} debe ser un objeto válido')
                if not (match.get('sales_order_id') or match.get('purchase_order_id') or match.get('match_index') is not None):
                    raise SelectionServiceError(f'Match {i+1} debe tener identificador válido')

    def _resolve_target_order(
        self,
        selection: Dict[str, Any],
        available_matches: List[Dict[str, Any]],
        order_type: str  # 'sales' o 'purchase'
    ) -> Union[SalesOrder, PurchaseOrder]:
        """Resuelve la orden objetivo desde selección por ID o índice"""
        
        if order_type == 'sales':
            order_id = selection.get('sales_order_id')
            order_key = 'sales_order'
            model_class = SalesOrder
        else:
            order_id = selection.get('purchase_order_id')
            order_key = 'purchase_order'
            model_class = PurchaseOrder
            
        match_index = selection.get('match_index')
        
        if not order_id and match_index is None:
            raise SelectionServiceError(f'Cada selección debe tener {order_type}_order_id o match_index')
        
        # Resolver por índice
        if match_index is not None:
            try:
                match = available_matches[match_index]
                return match[order_key]
            except (IndexError, KeyError):
                raise SelectionServiceError(f'Índice de match inválido: {match_index}')
        
        # Resolver por ID
        try:
            order = model_class.objects.select_for_update().get(
                id=order_id,
                status__in=['PENDING', 'PARTIALLY_EXECUTED']
            )
            return order
        except model_class.DoesNotExist:
            raise SelectionServiceError(f'Orden {order_type} no encontrada o no disponible: {order_id}')

    def _validate_and_get_units(
        self,
        selection: Dict[str, Any],
        source_order: Union[SalesOrder, PurchaseOrder],
        target_order: Union[PurchaseOrder, SalesOrder],
        total_selected_units: int
    ) -> int:
        """Valida y obtiene las unidades a seleccionar (genérico)"""
        
        requested_units = selection.get('units')
        
        # Usar automático si no se especifica
        if not requested_units:
            remaining_target_units = target_order.available_units - total_selected_units
            available_source_units = source_order.available_units
            requested_units = min(available_source_units, remaining_target_units)
        
        # Validar límites
        remaining_target_units = target_order.available_units - total_selected_units
        available_source_units = source_order.available_units
        max_available = min(available_source_units, remaining_target_units)
        
        if requested_units <= 0:
            raise SelectionServiceError('Las unidades solicitadas deben ser mayor que 0')
        
        if requested_units > max_available:
            raise SelectionServiceError(
                f'Unidades solicitadas ({requested_units}) exceden disponibles ({max_available}) para orden {source_order.order_number}'
            )
        
        return requested_units

    # ========================================
    # GESTIÓN DE CARRITO COMPARTIDA
    # ========================================
    
    @transaction.atomic
    def _clean_existing_selection(self, main_order: Union[PurchaseOrder, SalesOrder]) -> None:
        """Limpia selección existente si hay una"""
        
        try:
            existing_selection = main_order.match_selection
            existing_selection.delete()  # Cascade elimina items
        except MatchSelection.DoesNotExist:
            pass

    def _calculate_selection_totals(
        self,
        validated_selections: List[Dict[str, Any]],
        main_order: Union[PurchaseOrder, SalesOrder]
    ) -> Dict[str, Decimal]:
        """Calcula totales de una selección"""
        
        total_amount = sum(sel['subtotal'] for sel in validated_selections)
        total_units = sum(sel['units'] for sel in validated_selections)
        
        # Calcular ahorros basado en el presupuesto original
        if hasattr(main_order, 'total_amount'):  # PurchaseOrder
            total_savings = main_order.total_amount - total_amount
        else:  # SalesOrder - potencial ganancia
            total_savings = total_amount  # Toda la venta es ganancia
        
        return {
            'total_amount': total_amount,
            'total_units': total_units,
            'total_savings': total_savings
        }

    @transaction.atomic
    def _create_match_selection_base(
        self,
        main_order: Union[PurchaseOrder, SalesOrder],
        validated_selections: List[Dict[str, Any]],
        user,
        selection_method: str = 'manual'
    ) -> MatchSelection:
        """Crea la selección base (sin especificar tipo de orden)"""
        
        # Calcular totales
        totals = self._calculate_selection_totals(validated_selections, main_order)
        
        # Limpiar selección anterior si existe
        self._clean_existing_selection(main_order)
        
        # Determinar qué campos usar según el tipo de orden
        if isinstance(main_order, PurchaseOrder):
            purchase_order = main_order
            sales_order = None
        else:
            purchase_order = None
            sales_order = main_order
        
        # Crear la selección principal (carrito)
        selection = MatchSelection.objects.create(
            purchase_order=purchase_order,
            sales_order=sales_order,
            total_amount=totals['total_amount'],
            total_units=totals['total_units'],
            expected_savings=totals['total_savings'],
            expires_at=timezone.now() + timezone.timedelta(minutes=self.selection_expiry_minutes),
            created_by=user,
            metadata={
                'selection_method': selection_method,
                'original_matches_count': len(validated_selections),
                'created_at': timezone.now().isoformat(),
                'order_type': 'purchase' if isinstance(main_order, PurchaseOrder) else 'sales'
            }
        )
        
        # Crear items del carrito
        for validated_selection in validated_selections:
            # Determinar purchase_order y sales_order para el item
            if isinstance(main_order, PurchaseOrder):
                item_purchase_order = main_order
                item_sales_order = validated_selection['sales_order']
            else:
                item_purchase_order = validated_selection['purchase_order']
                item_sales_order = main_order
                
            item_total_amount = Decimal(str(validated_selection['units'])) * validated_selection['price_per_unit']

            
            MatchSelectionItem.objects.create(
                selection=selection,
                sales_order=item_sales_order,
                purchase_order=item_purchase_order,
                units=validated_selection['units'],
                price_per_unit=validated_selection['price_per_unit'],
                total_amount=item_total_amount,
                buyer_savings=Decimal('0'),  # Calcular si es necesario
                seller_gain=Decimal('0'),    # Calcular si es necesario
                metadata={
                    'selected_at': validated_selection['selected_at'].isoformat() if isinstance(validated_selection['selected_at'], timezone.datetime) else validated_selection['selected_at'],
                    'auto_selected': validated_selection.get('auto_selected', False),
                    'available_units': validated_selection.get('available_units', 0)
                }
            )
        
        # Actualizar estado de la orden principal
        main_order.status = 'MATCHES_SELECTED'
        main_order.matched_at = timezone.now()
        
        # Mantener metadata como backup/cache
        main_order.metadata = main_order.metadata or {}
        main_order.metadata.update({
            'selection_id': str(selection.id),
            'selection_summary': {
                'total_amount': str(totals['total_amount']),
                'total_units': totals['total_units'],
                'expires_at': selection.expires_at.isoformat(),
                'items_count': len(validated_selections)
            }
        })
        main_order.save(update_fields=['status', 'matched_at', 'metadata'])
        self._create_contracts_for_selection_unified(main_order, validated_selections)
        
        return selection

    # ========================================
    # OBTENCIÓN DE MATCHES
    # ========================================
    
    def _get_available_matches_for_purchase(self, purchase_order: PurchaseOrder) -> List[Dict[str, Any]]:
        """Obtiene matches disponibles para una orden de compra"""
        
        try:
            available_matches = self.matcher.find_matches_for_order(purchase_order)
            
            if not available_matches:
                raise SelectionServiceError('No hay matches disponibles para esta orden de compra')
            
            return available_matches
            
        except Exception as e:
            raise SelectionServiceError(f'Error obteniendo matches disponibles: {str(e)}')

    def _get_available_matches_for_sales(self, sales_order: SalesOrder) -> List[Dict[str, Any]]:
        """Obtiene matches disponibles para una orden de venta"""
        
        try:
            # Buscar órdenes de compra compatibles
            available_matches = self.matcher.find_matches_for_order(sales_order)
            
            print(f"matches disponibles: {available_matches}")
            if not available_matches:
                raise SelectionServiceError('No hay órdenes de compra disponibles para esta orden de venta')
            
            return available_matches
            
        except Exception as e:
            raise SelectionServiceError(f'Error obteniendo matches disponibles: {str(e)}')

    # ========================================
    # RESPUESTAS COMPARTIDAS
    # ========================================
    
    def _build_base_selection_response(
        self,
        main_order: Union[PurchaseOrder, SalesOrder],
        selection: MatchSelection
    ) -> Dict[str, Any]:
        """Construye respuesta base de selección"""
        
        # Obtener items del carrito
        items = selection.items.select_related('sales_order', 'purchase_order').all()
        
        selected_matches = []
        for item in items:
            selected_matches.append({
                'sales_order_id': str(item.sales_order.id),
                'sales_order_number': item.sales_order.order_number,
                'purchase_order_id': str(item.purchase_order.id),
                'purchase_order_number': item.purchase_order.order_number,
                'seller_email': item.sales_order.seller_user.email,
                'buyer_email': item.purchase_order.supplier_user.email,
                'units': item.units,
                'price_per_unit': float(item.price_per_unit),
                'subtotal': float(item.units * item.price_per_unit),
                'selected_at': item.metadata.get('selected_at'),
                'auto_selected': item.metadata.get('auto_selected', False)
            })
        
        # Determinar el endpoint según el tipo de orden
        order_type = selection.metadata.get('order_type', 'purchase')
        endpoint = '/trading/pay-selection/' if order_type == 'purchase' else '/trading/confirm-sales-selection/'
        
        return {
            'success': True,
            'selection_method': selection.metadata.get('selection_method', 'manual'),
            'order_type': order_type,
            'message': f'Matches seleccionados exitosamente: {len(selected_matches)} matches',
            'selection_summary': {
                'selection_id': str(selection.id),
                'total_units_selected': selection.total_units,
                'total_amount': float(selection.total_amount),
                'expected_result': float(selection.expected_savings),
                'deadline': selection.expires_at.isoformat(),
                'matches_count': len(selected_matches),
                'status': selection.status
            },
            'selected_matches': selected_matches,
            'order_status': main_order.status,
            'next_step': {
                'action': 'Proceder con la selección' if order_type == 'purchase' else 'Confirmar ventas seleccionadas',
                'endpoint': endpoint,
                'order_id': str(main_order.id),
                'selection_id': str(selection.id),
                'amount': float(selection.total_amount),
                'deadline': selection.expires_at.isoformat()
            }
        }

    # ========================================
    # GESTIÓN DE SELECCIONES
    # ========================================
    
    def get_active_selection(self, main_order: Union[PurchaseOrder, SalesOrder]) -> Optional[MatchSelection]:
        """Obtiene la selección activa de una orden"""
        
        try:
            selection = main_order.match_selection
            if selection.is_expired:
                self._mark_selection_as_expired(selection)
                return None
            return selection
        except MatchSelection.DoesNotExist:
            return None

    @transaction.atomic
    def _mark_selection_as_expired(self, selection: MatchSelection) -> None:
        """Marca una selección como expirada y limpia el estado"""
        
        selection.status = 'EXPIRED'
        selection.save(update_fields=['status'])
        
        # Limpiar estado de la orden principal
        main_order = selection.purchase_order or selection.sales_order
        main_order.status = 'PENDING'
        main_order.matched_at = None
        main_order.metadata = {
            'selection_expired_at': timezone.now().isoformat(),
            'expired_selection_id': selection.id
        }
        main_order.save(update_fields=['status', 'matched_at', 'metadata'])

    # ========================================
    # GESTION DE CONTRATOS
    # ========================================
    
    def _create_contracts_for_selection_unified(
        self,
        main_order: Union[PurchaseOrder, SalesOrder],
        validated_selections: List[Dict[str, Any]]
    ) -> None:
        """Crea contratos automáticamente para cualquier tipo de orden (unificado)"""
        
        # URL del webhook de Power Automate
        CONTRACT_WEBHOOK_URL = "https://default9e1ecd40015d4075a74499df58eb13.4a.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/22b5fe5748b74df988cf4544fe393fa3/triggers/manual/paths/invoke/?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=QLNPpiG_c_Y6SLdieFMPwXnecNtaZ4Y6g_ptVQ8EglQ"
        
        contracts_created = []
        is_purchase_order = isinstance(main_order, PurchaseOrder)
        
        for selection in validated_selections:
            try:
                # Obtener las órdenes según el tipo principal
                if is_purchase_order:
                    # Purchase order es la principal, sales_order viene en la selección
                    purchase_order = main_order
                    sales_order = selection.get('sales_order')  # Es objeto ya
                    if not sales_order:
                        print(f"No sales_order found in selection for purchase order {main_order.order_number}")
                        continue
                else:
                    # Sales order es la principal, purchase_order viene en la selección
                    sales_order = main_order
                    purchase_order = selection.get('purchase_order')  # Es objeto ya
                    if not purchase_order:
                        print(f"No purchase_order found in selection for sales order {main_order.order_number}")
                        continue
                
                # Verificar si ya existe un contrato
                existing_contract = OrderContract.objects.filter(
                    purchase_order=purchase_order,
                    sales_order=sales_order
                ).first()
                
                if existing_contract:
                    print(f"Contract already exists: {existing_contract.id}")
                    continue
                
                # Crear contrato
                contract = OrderContract.objects.create(
                    purchase_order=purchase_order,
                    sales_order=sales_order,
                    status='PENDING'
                )
                
                contracts_created.append(contract)
                
                # ✅ ENVIAR DATOS AL WEBHOOK DE POWER AUTOMATE
                contract_data = {
                    "test": "example",
                }
                
                # Enviar al webhook
                try:
                    response = requests.post(
                        CONTRACT_WEBHOOK_URL,
                        json=contract_data,
                        timeout=10,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code == 200:
                        print(f"✅ Contract webhook success - {contract.id}")
                    else:
                        print(f"❌ Webhook failed with status code: {response.status_code}")
                        print(f"Response: {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"🔗 Webhook error: {str(e)}")
                    # No fallar por esto, el contrato se creó correctamente
                    
            except Exception as e:
                target_order_type = "sales" if is_purchase_order else "purchase"
                target_order_id = selection.get('sales_order', {}).get('id', 'unknown') if is_purchase_order else selection.get('purchase_order', {}).get('id', 'unknown')
                print(f"❌ Error creating contract for {target_order_type} order {target_order_id}: {str(e)}")
                continue
        
        order_type = "purchase" if is_purchase_order else "sales"
        print(f"📊 Created {len(contracts_created)} contracts for {order_type} order {main_order.order_number}")

    # ========================================
    # AUDITORÍA COMPARTIDA
    # ========================================
    
    def _log_selection_audit_base(
        self,
        main_order: Union[PurchaseOrder, SalesOrder],
        selection: MatchSelection,
        user,
        action_code: str,
        operation: str,
        request=None
    ) -> None:
        """Registra auditoría base de selección"""
        
        if request:
            AuditService.log_action(
                request=request,
                action_code=action_code,
                obj=main_order,
                details={
                    'order_number': main_order.order_number,
                    'order_type': 'purchase' if isinstance(main_order, PurchaseOrder) else 'sales',
                    'selection_id': str(selection.id),
                    'selection_method': selection.metadata.get('selection_method', 'manual'),
                    'matches_selected': selection.items.count(),
                    'total_units_selected': selection.total_units,
                    'total_amount_selected': float(selection.total_amount),
                    'expected_result': float(selection.expected_savings),
                    'selection_expires_at': selection.expires_at.isoformat(),
                    'selected_by': user.email,
                    'operation': operation
                },
                status='SUCCESS'
            )

    def _log_error_audit_base(
        self,
        main_order: Union[PurchaseOrder, SalesOrder],
        error_msg: str,
        user,
        request=None
    ) -> None:
        """Registra auditoría de error base"""
        
        if request:
            AuditService.log_action(
                request=request,
                action_code='MATCH_SELECTION_ERROR',
                obj=main_order,
                details={
                    'order_number': main_order.order_number,
                    'order_type': 'purchase' if isinstance(main_order, PurchaseOrder) else 'sales',
                    'error': error_msg,
                    'selected_by': user.email,
                    'operation': 'match_selection_error'
                },
                status='ERROR'
            )