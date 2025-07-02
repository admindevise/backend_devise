from rest_framework import viewsets, status, permissions, filters, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q

from apps.trading.models import PurchaseOrder, SalesOrder, Transaction, OrderBook
from apps.trading.order_matching import OrderMatch
from apps.trading.service.order_service import (
    OrderCreationService, 
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
    filterset_fields = ['status', 'created_by', 'supplier_user']
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
    filterset_fields = ['status', 'created_by', 'seller_user']
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

class ActiveOrdersAPIView(APIView):
    """
    API endpoint para obtener órdenes activas del usuario autenticado
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Definir estados activos
        active_statuses = ['PENDING', 'APPROVED']
        
        # Filtrar órdenes de compra activas
        if user.is_staff and 'user_id' in request.query_params:
            # Administradores pueden ver órdenes de cualquier usuario
            user_id = request.query_params.get('user_id')
            purchase_orders = PurchaseOrder.objects.filter(
                Q(supplier_user_id=user_id) | Q(created_by_id=user_id),
                status__in=active_statuses
            )
            sales_orders = SalesOrder.objects.filter(
                Q(seller_user_id=user_id) | Q(created_by_id=user_id),
                status__in=active_statuses
            )
        else:
            # Usuarios normales solo ven sus propias órdenes
            purchase_orders = PurchaseOrder.objects.filter(
                Q(supplier_user=user) | Q(created_by=user),
                status__in=active_statuses
            )
            sales_orders = SalesOrder.objects.filter(
                Q(seller_user=user) | Q(created_by=user),
                status__in=active_statuses
            )
        
        # Serializar resultados
        purchase_serializer = PurchaseOrderSerializer(purchase_orders, many=True, context={'request': request})
        sales_serializer = SalesOrderSerializer(sales_orders, many=True, context={'request': request})
        
        # Combinar resultados en una respuesta
        return Response({
            'purchase_orders': purchase_serializer.data,
            'sales_orders': sales_serializer.data,
            'total_active_orders': purchase_orders.count() + sales_orders.count()
        })

# ✅ NUEVO: Vista para gestión de tokens reservados
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


