from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from apps.fund.models.core import Fund
from apps.fund.models.distributions import DistributionPeriod, InvestmentDistributionRecord
from apps.fund.serializers.distributions_serializers import (
    CreateDistributionPeriodSerializer,
    DistributionPeriodPreviewSerializer,
    DistributionPeriodListSerializer,
    DistributionPeriodDetailSerializer,
    
    InvestmentDistributionRecordSerializer,
    CreateDistributionRecordsSerializer,
)
from apps.fund.services.distributions.distributions_service import DistributionService, DistributionServiceError


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_distribution_period(request):
    """
    Vista específica para crear períodos de distribución.
    Alternativa al ViewSet para casos específicos.
    """
    serializer = CreateDistributionPeriodSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_distribution(request):
    """
    Vista para calcular vista previa de distribución sin crearla.
    """
    serializer = DistributionPeriodPreviewSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        preview_data = serializer.save()
        
        return Response({
            'success': True,
            'preview': preview_data,
            'message': 'Vista previa calculada exitosamente'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fund_distributions_history(request, fund_id):
    """
    Obtiene el historial de distribuciones de un fondo específico.
    """
    try:
        fund = Fund.objects.get(id=fund_id)
        
        # Verificar permisos de acceso al fondo
        if not request.user.is_staff:
            # Agregar validación de acceso al fondo según tu lógica de negocio
            pass
        
        distribution_service = DistributionService(fund)
        limit = int(request.GET.get('limit', 10))
        
        history = distribution_service.get_fund_distribution_history(limit)
        
        return Response({
            'success': True,
            'fund_id': fund_id,
            'fund_name': fund.name,
            'distributions_history': history,
            'total_count': len(history)
        }, status=status.HTTP_200_OK)
        
    except Fund.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Fondo no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def distribution_detail(request, distribution_id):
    """
    Obtiene detalles completos de una distribución específica.
    """
    try:
        distribution = DistributionPeriod.objects.select_related(
            'fund',
            'created_by',
            'approved_by'
        ).get(id=distribution_id)
        
        # Verificar permisos
        if not request.user.is_staff:
            # Agregar validación según tu lógica de negocio
            pass
        
        serializer = DistributionPeriodDetailSerializer(distribution)
        
        return Response({
            'success': True,
            'distribution': serializer.data
        }, status=status.HTTP_200_OK)
        
    except DistributionPeriod.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Distribución no encontrada'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================================
# DISTRIBUTION RECORDS BY INVESTMENT
# ================================================
class InvestmentDistributionRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InvestmentDistributionRecord.objects.all()
    serializer_class = InvestmentDistributionRecordSerializer
    permission_classes = []

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def distributions_records(request):
    """
    Vistra para crear registros de distribuciones para todos los ususarios
    """
    serializer = CreateDistributionRecordsSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
