"""
Views para el módulo de contabilidad.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from apps.fund.serializers.accounting_service_serializers import (
    AccountingFileValidateSerializer,
    AccountingFileImportSerializer,
    AccountingDefaultMappingSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def validate_accounting_file(request):
    """
    Valida un archivo de contabilidad y retorna información de estructura.
    
    Endpoint: POST /api/fund/accounting/validate-file/
    """
    serializer = AccountingFileValidateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        result = serializer.save()
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
    
    return Response({
        'success': False,
        'errors': serializer.errors,
        'message': 'Error validando archivo'
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def import_accounting_file(request):
    """
    Importa un archivo de contabilidad.
    
    Endpoint: POST /api/fund/accounting/import-file/
    """
    serializer = AccountingFileImportSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        result = serializer.save()
        response_data = serializer.to_representation(result)
        
        return Response(
            response_data,
            status=status.HTTP_201_CREATED if result.success else status.HTTP_400_BAD_REQUEST
        )
    
    return Response({
        'success': False,
        'errors': serializer.errors,
        'message': 'Error en datos de importación'
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_default_mapping(request):
    """
    Obtiene el mapeo de columnas por defecto según tipo de archivo.
    
    Endpoint: GET /api/fund/accounting/default-mapping/?file_type=txt
    """
    file_type = request.query_params.get('file_type', 'txt')
    
    serializer = AccountingDefaultMappingSerializer(data={'file_type': file_type})
    
    if serializer.is_valid():
        result = serializer.save()
        return Response(
            serializer.to_representation(result),
            status=status.HTTP_200_OK
        )
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)