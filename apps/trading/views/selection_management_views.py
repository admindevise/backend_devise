from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q

from apps.trading.models.selection_models import MatchSelection
from apps.trading.serializers_flow.selection_management_serializers import (
    UnifiedMatchSelectionSerializer,
    SelectionStatusSerializer,
    SelectionValidationSerializer,
    SelectionCancellationSerializer
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_match_selection(request):
    """
    Endpoint unificado para crear selecciones de matches.
    
    Maneja tanto órdenes de compra como de venta, y tanto selección manual como automática.
    
    Parámetros:
    - order_id: UUID de la orden (compra o venta)
    - order_type: 'purchase' o 'sales'
    - selection_method: 'manual' o 'auto'
    - selected_matches: Lista de matches (solo para method='manual')
    - force_partial: Boolean (solo para method='auto')
    """
    
    serializer = UnifiedMatchSelectionSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.process_selection()
        
        # Verificar si es advertencia de unidades/compradores insuficientes
        if result.get('warning_type') in ['INSUFFICIENT_UNITS', 'INSUFFICIENT_BUYERS']:
            return Response(result, status=status.HTTP_206_PARTIAL_CONTENT)
        
        return Response(result, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_selection_capability(request):
    """
    Valida si una orden puede crear selecciones y devuelve matches disponibles.
    
    Útil para que el frontend sepa si puede mostrar la interfaz de selección.
    """
    
    serializer = SelectionValidationSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'valid': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        validation_info = serializer.get_validation_info()
        
        return Response({
            'valid': validation_info.get('can_create_selection', False),
            'validation_info': validation_info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'valid': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_selection(request):
    """
    Cancela una selección existente y restaura el estado de la orden.
    """
    
    serializer = SelectionCancellationSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = serializer.cancel_selection()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


class MatchSelectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar selecciones existentes.
    
    Proporciona:
    - list: Lista selecciones del usuario
    - retrieve: Detalle de una selección específica
    - my_active_selections: Acción personalizada para selecciones activas
    - cleanup_expired: Acción para limpiar selecciones expiradas (solo admin)
    """
    
    serializer_class = SelectionStatusSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'metadata__order_type', 'metadata__selection_method']
    search_fields = ['purchase_order__order_number', 'sales_order__order_number']
    ordering_fields = ['selected_at', 'expires_at', 'total_amount']
    ordering = ['-selected_at']
    
    def get_queryset(self):
        """Filtrar selecciones del usuario autenticado"""
        user = self.request.user
        
        queryset = MatchSelection.objects.select_related(
            'purchase_order__fund',
            'purchase_order__supplier_user',
            'sales_order__fund', 
            'sales_order__seller_user',
            'created_by'
        ).prefetch_related('items__sales_order', 'items__purchase_order')
        
        if not user.is_staff:
            # Filtrar por usuario: puede ver selecciones donde es el comprador o vendedor
            queryset = queryset.filter(
                Q(purchase_order__supplier_user=user) |
                Q(sales_order__seller_user=user) |
                Q(created_by=user)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_active_selections(self, request):
        """
        Devuelve todas las selecciones activas del usuario.
        
        Útil para mostrar en dashboard o para verificar selecciones pendientes.
        """
        user = request.user
        
        active_selections = self.get_queryset().filter(
            status='ACTIVE',
            expires_at__gt=timezone.now()
        )
        
        serializer = self.get_serializer(active_selections, many=True)
        
        return Response({
            'count': active_selections.count(),
            'active_selections': serializer.data,
            'user_email': user.email,
            'retrieved_at': timezone.now().isoformat()
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def cleanup_expired(self, request):
        """
        Limpia selecciones expiradas del sistema.
        
        Solo disponible para staff/admin.
        """
        if not request.user.is_staff:
            return Response({
                'error': 'Solo administradores pueden ejecutar esta acción'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from apps.trading.services_core.selection_service import MatchSelectionService
        
        selection_service = MatchSelectionService()
        cleanup_results = selection_service.check_and_clean_expired_selections()
        
        return Response({
            'success': True,
            'message': f"Se limpiaron {cleanup_results['total_cleaned_selections']} selecciones expiradas",
            'cleanup_results': cleanup_results
        })


class UserSelectionStatsAPIView(APIView):
    """
    Vista para obtener estadísticas de selecciones del usuario.
    
    Útil para dashboards y métricas.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtiene estadísticas de selecciones del usuario"""
        
        user = request.user
        
        # Obtener selecciones del usuario
        user_selections = MatchSelection.objects.filter(
            Q(purchase_order__supplier_user=user) |
            Q(sales_order__seller_user=user) |
            Q(created_by=user)
        )
        
        # Calcular estadísticas
        total_selections = user_selections.count()
        active_selections = user_selections.filter(status='ACTIVE').count()
        completed_selections = user_selections.filter(status='COMPLETED').count()
        expired_selections = user_selections.filter(status='EXPIRED').count()
        cancelled_selections = user_selections.filter(status='CANCELLED').count()
        
        # Estadísticas por tipo de orden
        purchase_selections = user_selections.filter(purchase_order__isnull=False).count()
        sales_selections = user_selections.filter(sales_order__isnull=False).count()
        
        # Estadísticas por método
        manual_selections = user_selections.filter(
            metadata__selection_method='manual'
        ).count()
        auto_selections = user_selections.filter(
            metadata__selection_method='automatic'
        ).count()
        
        # Totales monetarios (solo completadas)
        completed_selections_qs = user_selections.filter(status='COMPLETED')
        total_amount_selected = sum(
            float(s.total_amount) for s in completed_selections_qs
        )
        total_savings_achieved = sum(
            float(s.expected_savings) for s in completed_selections_qs if s.expected_savings > 0
        )
        
        return Response({
            'user_email': user.email,
            'selection_stats': {
                'total_selections': total_selections,
                'active_selections': active_selections,
                'completed_selections': completed_selections,
                'expired_selections': expired_selections,
                'cancelled_selections': cancelled_selections
            },
            'selection_by_order_type': {
                'purchase_selections': purchase_selections,
                'sales_selections': sales_selections
            },
            'selection_by_method': {
                'manual_selections': manual_selections,
                'auto_selections': auto_selections
            },
            'financial_summary': {
                'total_amount_selected': total_amount_selected,
                'total_savings_achieved': total_savings_achieved,
                'average_selection_amount': total_amount_selected / completed_selections if completed_selections > 0 else 0
            },
            'generated_at': timezone.now().isoformat()
        })
