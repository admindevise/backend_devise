from rest_framework import serializers
from django.contrib.auth.models import Group
from apps.user.models import Role

class SubroleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField('get_user_permissions')
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        required=True,
        write_only=True
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'role_id']
    
    def get_user_permissions(self, obj):
        array = []
        for permission in obj.permissions.all():
            array.append(permission.codename)
        return array
    
    def create(self, validated_data):
        # Extraer role_id de los datos validados
        role_id = validated_data.pop('role_id', None)
        
        # Crear el grupo (subrol)
        group = Group.objects.create(**validated_data)
        
        # Si se proporcionó role_id, asignar el grupo al rol
        if role_id:
            role = Role.objects.get(pk=role_id.pk)
            role.groups.add(group)
        
        return group

class SubroleSerializerBackoffice(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

