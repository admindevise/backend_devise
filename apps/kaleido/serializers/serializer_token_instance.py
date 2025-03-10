from rest_framework import serializers
from apps.kaleido.models import InstanceOfTokenContract721

class InstanceOfTokenContract721Serializer(serializers.ModelSerializer):
    #created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    class Meta:
        model=InstanceOfTokenContract721
        fields = ['id', 'user', 'name', 'symbol', 'promote_contract']
        read_only_fields = ['id', 'user']
