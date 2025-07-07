from rest_framework import viewsets, status, filters, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from collections import OrderedDict
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q

from apps.trading.models import PurchaseOrder, SalesOrder, Transaction
from apps.trading.service.order_query_service import OrderQueryService
from apps.trading.service.order_service import (
    OrderManagementService, 
    PaymentProcessingService
)
from apps.utils.views.Mixins import DateFilterMixin
from apps.trading.serializers import (
    PurchaseOrderSerializer,
    SalesOrderSerializer,
    TransactionSerializer,
    OrderBookSerializer,
    OrderCancellationSerializer
)

class PurchaseOrderViewSet(DateFilterMixin,
                           mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.DestroyModelMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    """
    API endpoint para gestionar órdenes de compra de unidades de fondos.
    """
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    filterset_fields = ['created_by', 'supplier_user']
    search_fields = ['order_number', 'fund__name']
    ordering_fields = ['created_at', 'price_per_unit', 'units', 'expiration_date']
    ordering = ['-created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_management_service = OrderManagementService()
        self.payment_service = PaymentProcessingService()

    def perform_create(self, serializer):
        """Override para usar el contexto de request"""
        # El serializer ya maneja la creación segura con servicios
        serializer.save()

    def get_queryset(self):
        """Filtra órdenes del usuario o todas si es admin"""
        user = self.request.user
        queryset = PurchaseOrder.objects.exclude(status='CANCELLED')
        
        if not user.is_staff:
            queryset = queryset.filter(
                Q(supplier_user=user) | Q(created_by=user)
            )
            
        queryset = self.apply_date_filters(queryset)
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """Cancela una orden de compra"""
        try:
            purchase_order = self.get_object()
            
            # Verificar permisos
            if not request.user.is_staff and purchase_order.created_by != request.user:
                return Response({
                    'error': 'No tienes permisos para cancelar esta orden'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Usar el serializer de cancelación
            cancellation_serializer = OrderCancellationSerializer(data=request.data)
            cancellation_serializer.is_valid(raise_exception=True)
            
            result = cancellation_serializer.cancel_order(
                purchase_order, request.user, request
            )
            
            return Response({
                'success': True,
                'message': 'Orden cancelada exitosamente',
                'order_status': result['order_status']
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Override para usar cancelación en lugar de eliminación"""
        try:
            purchase_order = self.get_object()
            
            # Usar cancelación en lugar de eliminación física
            cancellation_serializer = OrderCancellationSerializer(data={
                'cancellation_reason': 'Deleted via API', 'cancellation_at': timezone.now()
            })
            cancellation_serializer.is_valid(raise_exception=True)
            
            result = cancellation_serializer.cancel_order(
                purchase_order, request.user, request
            )
            
            return Response({
                'success': True,
                'message': 'Orden cancelada exitosamente'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class SalesOrderViewSet(DateFilterMixin,
                        mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.DestroyModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    API endpoint para gestionar órdenes de venta de unidades de fondos.
    """
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    filterset_fields = ['created_by', 'seller_user']
    search_fields = ['order_number', 'fund__name']
    ordering_fields = ['created_at', 'price_per_unit', 'units', 'expiration_date']
    ordering = ['-created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_management_service = OrderManagementService()

    def perform_create(self, serializer):
        """Override para usar el contexto de request"""
        # El serializer ya maneja la creación segura con servicios
        serializer.save()

    def get_queryset(self):
        """Filtra órdenes del usuario o todas si es admin"""
        user = self.request.user
        queryset = SalesOrder.objects.exclude(status='CANCELLED')
        
        if not user.is_staff:
            queryset = queryset.filter(
                Q(seller_user=user) | Q(created_by=user)
            )
        
        queryset = self.apply_date_filters(queryset)
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """Cancela una orden de venta y libera tokens reservados"""
        print('entro a action cancel')
        try:
            # ✅ DEBUGGING: Verificar la orden SIN filtros de queryset
            try:
                raw_order = SalesOrder.objects.get(id=pk)
                print(f"=== ORDEN ENCONTRADA (sin filtros) ===")
                print(f"Order ID: {raw_order.id}")
                print(f"seller_user: {raw_order.seller_user} (ID: {raw_order.seller_user.id})")
                print(f"created_by: {raw_order.created_by} (ID: {raw_order.created_by.id})")
                print(f"Status: {raw_order.status}")
                print(f"Usuario que cancela: {request.user} (ID: {request.user.id})")
                print(f"Usuario es staff: {request.user.is_staff}")
                
                # Verificar si el usuario está autorizado
                is_authorized = (
                    request.user.is_staff or 
                    raw_order.seller_user == request.user or 
                    raw_order.created_by == request.user
                )
                print(f"Usuario autorizado: {is_authorized}")
                
            except SalesOrder.DoesNotExist:
                print(f"ERROR: La orden {pk} NO existe en la base de datos")
                return Response({
                    'error': f'No se encontró la orden con ID {pk}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Ahora intentar get_object() que usa el queryset filtrado
            try:
                sales_order = self.get_object()
                print("✅ get_object() exitoso")
            except Exception as get_obj_error:
                print(f"❌ ERROR en get_object(): {str(get_obj_error)}")
                print("Esto confirma que el problema está en los filtros del queryset")
                
                # Si el usuario tiene permisos, usar la orden raw
                if (request.user.is_staff or 
                    raw_order.seller_user == request.user or 
                    raw_order.created_by == request.user):
                    
                    print("🔧 Usando orden sin filtros porque el usuario tiene permisos")
                    sales_order = raw_order
                else:
                    return Response({
                        'error': 'No tienes permisos para cancelar esta orden'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Verificar permisos
            if not request.user.is_staff and sales_order.created_by != request.user:
                return Response({
                    'error': 'No tienes permisos para cancelar esta orden'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Usar el serializer de cancelación
            cancellation_serializer = OrderCancellationSerializer(data=request.data)
            cancellation_serializer.is_valid(raise_exception=True)
            
            result = cancellation_serializer.cancel_order(
                sales_order, request.user, request
            )
            
            return Response({
                'success': True,
                'message': 'Orden de venta cancelada exitosamente',
                'order_status': result['order_status'],
                'released_tokens': result['released_tokens']
            })
            
        except Exception as e:
            print(f"ERROR EN CANCEL: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def reserved_tokens(self, request, pk=None):
        """Obtiene información de tokens reservados para esta orden"""
        try:
            sales_order = self.get_object()
            
            # Verificar permisos
            if request.user != sales_order.seller_user:
                print(f"{request.user} vendedor {sales_order.seller_user}")
                return Response({
                    'error': 'No tienes permisos para ver esta información'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Inicializar la estructura por defecto
            reserved_info = {
                'count': 0,
                'token_ids': [],
                'expires_at': None,
                'tokens_details': []
            }
            
            # Obtener información de tokens reservados
            if hasattr(sales_order, 'metadata') and sales_order.metadata:
                reserved_tokens = sales_order.metadata.get('reserved_tokens', [])
                
                if reserved_tokens:  # Solo si hay tokens reservados
                    # Obtener detalles de tokens
                    from apps.fund.models import FundToken
                    tokens = FundToken.objects.filter(
                        token_id__in=reserved_tokens,
                        fund=sales_order.fund
                    ).values('token_id', 'nickname', 'created_at')
                    
                    reserved_info = {
                        'count': len(reserved_tokens),
                        'token_ids': reserved_tokens,
                        'expires_at': sales_order.metadata.get('reservation_expires_at'),
                        'tokens_details': list(tokens)
                    }
            
            return Response({
                'success': True,
                'reserved_tokens': reserved_info
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Override para usar cancelación en lugar de eliminación"""
        try:
            sales_order = self.get_object()
            
            # Usar cancelación en lugar de eliminación física
            cancellation_serializer = OrderCancellationSerializer(data={
                'cancellation_reason': 'Deleted via API'
            })
            cancellation_serializer.is_valid(raise_exception=True)
            
            result = cancellation_serializer.cancel_order(
                sales_order, request.user, request
            )
            
            return Response({
                'success': True,
                'message': 'Orden de venta cancelada exitosamente',
                'released_tokens': result['released_tokens']
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class TransactionViewSet(DateFilterMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    API endpoint para gestionar transacciones entre órdenes de compra y venta.
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    filterset_fields = ['buyer', 'seller', 'fund']
    search_fields = ['purchase_order__order_number', 'sales_order__order_number']
    ordering_fields = ['created_at', 'total_amount', 'units']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filtra transacciones del usuario o todas si es admin"""
        user = self.request.user
        queryset = Transaction.objects.all()
        
        if not user.is_staff:
            queryset = queryset.filter(
                Q(buyer=user) | Q(seller=user)
            )
        
        queryset = self.apply_date_filters(queryset)
        return queryset

    def perform_create(self, serializer):
        """Override para agregar contexto de usuario"""
        # El serializer ya maneja la ejecución segura con servicios
        serializer.save()

class ActiveOrdersPagination(PageNumberPagination):
    """
    Paginación personalizada para órdenes activas
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Respuesta personalizada que mantiene la estructura de purchase_orders y sales_orders
        """
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_info', {
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.page_size,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            }),
            ('results', data)
        ]))

class ActiveOrdersAPIView(DateFilterMixin, APIView):
    """
    API endpoint para obtener órdenes activas del usuario autenticado con paginación
    """
    permission_classes = [IsAuthenticated]
    pagination_class = ActiveOrdersPagination
    
    def __init__(self):
        super().__init__()
        self.query_service = OrderQueryService()
    
    @property
    def paginator(self):
        """
        Inicializa el paginador si no existe
        """
        if not hasattr(self, '_paginator'):
            self._paginator = self.pagination_class()
        return self._paginator
    
    def get(self, request):
        """
        GET /api/orders/active/
        
        Query params:
        - all_orders: bool (admin only)
        - user_id: int (admin only)
        - start_date: date
        - end_date: date
        - include_stats: bool
        - min_price: float
        - max_price: float
        - exact_price: float
        - page: int (número de página)
        - page_size: int (tamaño de página, máximo 100)
        
        """
        try:
            # Extraer parámetros de consulta
            filters = self._extract_filters(request)
            
            # Usar el servicio para obtener órdenes
            result = self.query_service.get_active_orders(
                requesting_user=request.user,
                **filters
            )
            
            # NUEVO: Combinar órdenes para paginación
            combined_orders = self._combine_orders_for_pagination(
                result['purchase_orders'], 
                result['sales_orders']
            )
            
            # NUEVO: Aplicar paginación
            paginated_orders = self.paginator.paginate_queryset(
                combined_orders, 
                request, 
                view=self
            )
            
            # NUEVO: Separar órdenes paginadas
            paginated_data = self._separate_paginated_orders(paginated_orders)
            
            # Serializar datos paginados
            purchase_serializer = PurchaseOrderSerializer(
                paginated_data['purchase_orders'], 
                many=True, 
                context={'request': request}
            )
            sales_serializer = SalesOrderSerializer(
                paginated_data['sales_orders'], 
                many=True, 
                context={'request': request}
            )
            
            # Preparar respuesta con estructura original
            response_data = {
                'purchase_orders': purchase_serializer.data,
                'sales_orders': sales_serializer.data,
                'total_active_orders': result['metadata']['total_count'],
                'summary': result['metadata']
            }
            
            # NUEVO: Agregar información de paginación
            response_data['pagination'] = {
                'current_page': self.paginator.page.number,
                'total_pages': self.paginator.page.paginator.num_pages,
                'page_size': self.paginator.page_size,
                'total_count': self.paginator.page.paginator.count,
                'has_next': self.paginator.page.has_next(),
                'has_previous': self.paginator.page.has_previous(),
                'next_page_url': self.paginator.get_next_link(),
                'previous_page_url': self.paginator.get_previous_link()
            }
            
            # Agregar estadísticas si se solicitan
            if filters.get('include_stats'):
                stats = self.query_service.get_order_statistics(
                    requesting_user=request.user,
                    **filters
                )
                response_data['statistics'] = stats
            
            return Response(response_data)
            
        except Exception as e:
            return Response({
                'error': f'Error obteniendo órdenes activas: {str(e)}',
                'purchase_orders': [],
                'sales_orders': [],
                'total_active_orders': 0,
                'pagination': {
                    'current_page': 1,
                    'total_pages': 0,
                    'page_size': 20,
                    'total_count': 0,
                    'has_next': False,
                    'has_previous': False
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _combine_orders_for_pagination(self, purchase_orders, sales_orders):
        """
        Combina órdenes de compra y venta para paginación unificada
        """
        from itertools import chain
        
        # Agregar tipo de orden para poder separar después
        purchase_list = []
        for order in purchase_orders:
            order._order_type = 'purchase'
            purchase_list.append(order)
        
        sales_list = []
        for order in sales_orders:
            order._order_type = 'sales'
            sales_list.append(order)
        
        # Combinar y ordenar por fecha de creación (más recientes primero)
        combined = list(chain(purchase_list, sales_list))
        combined.sort(key=lambda x: x.created_at, reverse=True)
        
        return combined
    
    def _separate_paginated_orders(self, paginated_orders):
        """
        Separa órdenes paginadas en compra y venta
        """
        purchase_orders = []
        sales_orders = []
        
        for order in paginated_orders:
            if hasattr(order, '_order_type'):
                if order._order_type == 'purchase':
                    purchase_orders.append(order)
                elif order._order_type == 'sales':
                    sales_orders.append(order)
        
        return {
            'purchase_orders': purchase_orders,
            'sales_orders': sales_orders
        }
    
    def _extract_filters(self, request):
        """Extrae y valida filtros de la consulta"""
        filters = {}
        errors = []
        price_range = {}
        
        # Filtro por rango de precios
        try:
            if request.query_params.get('min_price'):
                min_price = float(request.query_params.get('min_price'))
                if min_price <= 0:
                    errors.append("El precio mínimo no puede ser cero o negativo")
                else:
                    price_range['min_price'] = min_price
            
            if request.query_params.get('max_price'):
                max_price = float(request.query_params.get('max_price'))
                if max_price <= 0:
                    errors.append("El precio máximo no puede ser cero o negativo")
                else:
                    price_range['max_price'] = max_price
            
            # Validar que min_price <= max_price
            if price_range.get('min_price') and price_range.get('max_price'):
                if price_range['min_price'] > price_range['max_price']:
                    errors.append("El precio mínimo no puede ser mayor que el precio máximo")
            
            if request.query_params.get('exact_price'):
                exact_price = float(request.query_params.get('exact_price'))
                if exact_price <= 0:
                    errors.append("El precio exacto no puede ser cero o negativo")
                else:
                    price_range['exact_price'] = exact_price
        
        except ValueError:
            errors.append("Los valores de precio deben ser números válidos")
        
        if price_range:
            filters['price_range'] = price_range
        
        # Si hay errores, lanzar excepción
        if errors:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"filter_errors": errors})
        
        # Filtros de permisos
        if request.query_params.get('all_orders', '').lower() == 'true':
            filters['all_orders'] = True
        
        if request.query_params.get('user_id'):
            filters['user_id'] = request.query_params.get('user_id')
        
        # Filtros de fecha
        date_range = {}
        if request.query_params.get('start_date'):
            date_range['start_date'] = request.query_params.get('start_date')
        if request.query_params.get('end_date'):
            date_range['end_date'] = request.query_params.get('end_date')
        
        if date_range:
            filters['date_range'] = date_range
        
        # Opciones adicionales
        if request.query_params.get('include_stats', '').lower() == 'true':
            filters['include_stats'] = True
        
        return filters


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cleanup_expired_reservations(request):
    """
    Endpoint para limpiar reservas de tokens expiradas (solo admin)
    """
    if not request.user.is_staff:
        return Response({
            'error': 'Solo administradores pueden ejecutar esta acción'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from apps.trading.security.token_validators import TokenReservationManager
        
        manager = TokenReservationManager()
        result = manager.cleanup_expired_reservations()
        
        return Response({
            'success': result['success'],
            'cleaned_count': result.get('cleaned_count', 0),
            'message': f"Se limpiaron {result.get('cleaned_count', 0)} reservas expiradas"
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


