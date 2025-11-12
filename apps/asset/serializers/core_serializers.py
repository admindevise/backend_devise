from rest_framework import serializers
from apps.asset.models.core import Asset, AssetType
from apps.asset.services.assets.asset_service import AssetCreationService

class AssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = '__all__'

class AssetCreateSerializer(serializers.Serializer):
    
    fund_id = serializers.IntegerField(required=True)
    asset_type_id = serializers.IntegerField(required=True)
    name = serializers.CharField(required=True, allow_blank=False)
    description = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    total_area_m2 = serializers.IntegerField()
    acquisition_value = serializers.IntegerField()
    acquisition_date = serializers.DateField()
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        
        try:
            asset = AssetCreationService.create_asset(
                user=user,
                asset_data=validated_data,
                request=request
            )
            return asset
        except Exception as e:
            raise serializers.ValidationError(str(e))