from rest_framework import serializers
from apps.user.models import Role

from ..serializers.subrole_serializer import SubroleSerializer


class RoleSerializer(serializers.ModelSerializer):
    subroles =  serializers.SerializerMethodField('get_role_list')

    class Meta:
        model = Role
        fields = ['name', 'id', 'subroles']
    
    def get_role_list(self, obj):
        array = []
        groups = obj.groups.all()
        for group in groups:
            dict = {}
            dict['name'] = group.name
            dict['subrol_id']= group.id
            dict['role_id']= obj.id
            array.append(dict)
        return array
    

class RoleSerializerDetail (serializers.ModelSerializer):

    class Meta:
        model = Role
        fields = ['id', 'name']
