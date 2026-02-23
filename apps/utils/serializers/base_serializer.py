from rest_framework import serializers

class BaseSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S")