from rest_framework import serializers
from apps.audit.models import AuditCategory, AuditAction, AuditLog
from apps.user.serializers.basic_info_user_serializer import UserBasicInfoSerializer

class AuditCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditCategory
        fields = ['id', 'name', 'code', 'description']

class AuditActionSerializer(serializers.ModelSerializer):
    category = AuditCategorySerializer()
    
    class Meta:
        model = AuditAction
        fields = ['id', 'category', 'name', 'code', 'description', 'severity']

class AuditLogSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    user = UserBasicInfoSerializer()
    action = AuditActionSerializer()
    content_type_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'action', 'content_type_name', 'object_id',
            'transaction_id', 'blockchain_tx_hash', 'ip_address',
            'details', 'status', 'created_at'
        ]
    
    def get_content_type_name(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"