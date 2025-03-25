from rest_framework import serializers
from apps.security.models import SecurityConfiguration

class SecurityConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityConfiguration
        fields = '__all__'