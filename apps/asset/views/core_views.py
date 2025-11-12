from rest_framework import permissions, response, status, viewsets
from rest_framework.decorators import api_view, permission_classes

from apps.asset.models.core import Asset, AssetType
from apps.asset.serializers.core_serializers import AssetCreateSerializer, AssetTypeSerializer

class AssetTypeViewSet(viewsets.ModelViewSet):
    queryset = AssetType.objects.all()
    serializer_class = AssetTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_asset(request):
    serializer = AssetCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        asset = serializer.save()
        return response.Response(
            {'message': 'Activo creado exitosamente', 'asset_id': asset.id},
            status=status.HTTP_201_CREATED
        )
    
    return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)