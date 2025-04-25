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
from apps.utils.views.Mixins import DateFilterMixin
from apps.fund.models import Fund
from apps.trading.serializers import (
    PurchaseOrderSerializer,
    SalesOrderSerializer,
    TransactionSerializer,
    OrderBookSerializer
)

class PurchaseOrderViewSet(mixins.CreateModelMixin,
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

    def perform_create(self, serializer):
        """
        Al crear una orden, asigna el usuario actual como created_by 
        a menos que sea admin y haya especificado otro valor
        """
        user = self.request.user
        data = serializer.validated_data
        
        if not user.is_staff or 'supplier_user' not in data:
            data['supplier_user'] = user
            
        serializer.save(created_by=user)

    def get_queryset(self):
        """Filtra órdenes del usuario o todas si es admin"""
        user = self.request.user
        queryset = PurchaseOrder.objects.all()
        
        # Filtrar por usuario si no es admin
        if not user.is_staff:
            queryset = queryset.filter(
                Q(supplier_user=user) | Q(created_by=user)
            )
        
        # Solo excluir canceladas si no se está filtrando específicamente por ellas
        status_param = self.request.query_params.get('status')
        if status_param != 'CANCELLED':
            queryset = queryset.exclude(status='CANCELLED')
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """
        Si es administrador: elimina la orden
        Si es usuario normal: cambia el estado a cancelada
        """
        instance = self.get_object()
        
        # Si es administrador, elimina físicamente
        if request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        
        # Si no es admin o la orden no está en estado válido para cancelar
        if instance.status not in ['PENDING', 'APPROVED']:
            return Response(
                {"detail": "Solo órdenes en estado PENDING o APPROVED pueden ser canceladas"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Cancela la orden para usuarios normales
        instance.update_status('CANCELLED')
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class SalesOrderViewSet(mixins.CreateModelMixin,
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

    def perform_create(self, serializer):
        """
        Al crear una orden, asigna el usuario actual como created_by 
        a menos que sea admin y haya especificado otro valor
        """
        user = self.request.user
        data = serializer.validated_data
        
        if not user.is_staff or 'seller_user' not in data:
            data['seller_user'] = user
            
        serializer.save(created_by=user)

    def get_queryset(self):
        """Filtra órdenes del usuario o todas si es admin, excluyendo canceladas"""
        user = self.request.user
        queryset = SalesOrder.objects.all()
        
        # Filtrar por usuario si no es admin
        if not user.is_staff:
            queryset = queryset.filter(
                Q(seller_user=user) | Q(created_by=user)
            )
        
        # Solo excluir canceladas si no se está filtrando específicamente por ellas
        status_param = self.request.query_params.get('status')
        if status_param != 'CANCELLED':
            queryset = queryset.exclude(status='CANCELLED')
            
        return queryset
        
    def destroy(self, request, *args, **kwargs):
        """
        Si es administrador: elimina la orden
        Si es usuario normal: cambia el estado a cancelada
        """
        instance = self.get_object()
        
        # Si es administrador, elimina físicamente
        if request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        
        # Si no es admin o la orden no está en estado válido para cancelar
        if instance.status not in ['PENDING', 'APPROVED']:
            return Response(
                {"detail": "Solo órdenes en estado PENDING o APPROVED pueden ser canceladas"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Cancela la orden para usuarios normales
        instance.update_status('CANCELLED')
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class TransactionViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para gestionar transacciones entre órdenes de compra y venta.
    Solo lectura para usuarios normales, creación permitida para administradores.
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['purchase_order__order_number', 'sales_order__order_number', 'fund__name']
    ordering_fields = ['created_at', 'price_per_unit', 'total_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filtra transacciones del usuario o todas si es admin"""        
        user = self.request.user
        
        if user.is_staff:
            queryset = Transaction.objects.all()
        else:
            queryset = Transaction.objects.filter(
                Q(buyer=user) | Q(seller=user)
            )
        
        queryset = self.apply_date_filters(queryset)
        
        return queryset

class OrderBookViewSet(DateFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para visualizar el libro de órdenes (solo lectura).
    Permite ver todas las órdenes abiertas para un fondo específico.
    """
    serializer_class = OrderBookSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_staff:
            return OrderBook.objects.none()
        
        queryset = OrderBook.objects.all()
        queryset = self.apply_date_filters(queryset)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_fund(self, request):
        """Ver el libro de órdenes para un fondo específico"""
        fund_id = request.query_params.get('fund_id')
        if not fund_id:
            return Response(
                {"detail": "Se requiere el parámetro fund_id"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            fund = Fund.objects.get(id=fund_id)
            order_book, created = OrderBook.objects.get_or_create(fund=fund)
            serializer = self.get_serializer(order_book)
            return Response(serializer.data)
        except Fund.DoesNotExist:
            return Response(
                {"detail": "Fondo no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )


class ActiveOrdersAPIView(APIView):
    """
    API endpoint para obtener todas las órdenes activas (PENDING o APPROVED) del usuario autenticado.
    Devuelve tanto las órdenes de compra como de venta en una sola respuesta.
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
        purchase_serializer = PurchaseOrderSerializer(purchase_orders, many=True)
        sales_serializer = SalesOrderSerializer(sales_orders, many=True)
        
        # Combinar resultados en una respuesta
        return Response({
            'purchase_orders': purchase_serializer.data,
            'sales_orders': sales_serializer.data,
            'total_active_orders': purchase_orders.count() + sales_orders.count()
        })
        

