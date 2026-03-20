from rest_framework import serializers
from ..models import User

class UserBasicInfoSerializer(serializers.ModelSerializer):
    
    class Meta:
        fields = [
                'id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_superuser',
                'is_natural_person', 'first_name', 'last_name', 'phone',
                'birth_date','birth_country','birth_region','birth_city',
                'local_id_type',
                'document_number', 'document_front_image', 'document_back_image', 'selfie', #weetrust
                'doc_country_expedition', 'doc_region_expedition', 'doc_city_expedition',
                'expedition_date', 'mail_delivery', 
                ]
        model = User
        
    def validate(self, attrs):
        from apps.user.models_permission import UserAdminPermission
        from django.utils import timezone
        
        user = self.context['request'].user
        pk = self.context.get('pk')
        target_id = self.context.get('target_id')
        
        target_user = User.objects.get(id=target_id)
        
        can_manage = user.is_superuser or user.is_staff
        it_self = user.pk == pk
        
        permissions = UserAdminPermission.objects.filter(
            user=target_user,
            admin_user=user,
            permission_type__in=['EDIT_PROFILE', 'FULL_ACCESS'],
            status='ACTIVE',
            expires_at__gt=timezone.now()
        ).first()
        print("PERMISSIONS", permissions)
        
        if not (can_manage or it_self):
             raise serializers.ValidationError({"detail": "No puedes modificar datos de otro usuario."})
        
        if not (can_manage and permissions):
            raise serializers.ValidationError({"detail": f"No tienes permisos para modificar los datos de este usuario."})
        
        if permissions:
            permissions.mark_used()  # Marca el permiso como usado recientemente
             
        return attrs

class UserShortInfoSerializer(serializers.ModelSerializer):
    
    class Meta:
        fields = ['id', 'email', 'first_name', 'last_name', 'phone']
        model = User