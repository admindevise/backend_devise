from django.utils import timezone
# from apps.security.models import SecurityConfiguration
from apps.user.models import User, IdType
from apps.info_residential.models import Residentialplace
from apps.info_workplace.models import Workplace
from apps.info_financial.models import Financial
from apps.info_socioeconomic.models import Socioeconomic
from apps.sponsor_company.models import SponsorCompany

from rest_framework import serializers
from .role_serializer import RoleSerializerDetail
from django.contrib.auth.password_validation import validate_password
from apps.security.security_settings import PASSWORD_EXPIRY_DAYS
import datetime as dt


# config = SecurityConfiguration.objects.first()
# PASSWORD_EXPIRY_DAYS = config.PASSWORD_EXPIRY_DAYS
class UserBasicInfoSerializer(serializers.ModelSerializer):
    role = RoleSerializerDetail(read_only=True)
    subrole = serializers.SerializerMethodField('get_subrole_info')
    has_datos_basicos =  serializers.SerializerMethodField('datos_basicos')
    has_resident_info =  serializers.SerializerMethodField('resident_info')
    has_workplace_info =  serializers.SerializerMethodField('workplace_info')
    has_financial_info =  serializers.SerializerMethodField('financial_info')
    has_socioeconomic_info = serializers.SerializerMethodField('socioeconomic_info')
    full_name = serializers.SerializerMethodField('get_full_name')
    perfil_image = serializers.SerializerMethodField('get_perfil_image')
    last_login =serializers.SerializerMethodField('get_last_login')
    password_expires = serializers.SerializerMethodField('get_password_expires')

    class Meta:
        model = User
        fields = [
            'id', 'email', 'code', 'phone', 'role', 'subrole',
            'full_name',
            'perfil_image',
            'has_datos_basicos',
            'has_resident_info',
            'has_workplace_info',
            'has_financial_info',
            'has_socioeconomic_info',
            'last_login',
            'password_expires'
            ]

    def get_subrole_info(self, obj):
        dict = {}
        try:
            dict['id'] = obj.groups.all()[0].id
            dict['name'] = obj.groups.all()[0].name
        except:
            dict['id'] = ''
            dict['name'] = ''
        return dict
    
    def get_full_name(self, obj):
        if obj.first_name != '':
            return f'{obj.first_name} {obj.last_name}'
        return ''
    
    def get_perfil_image(self, obj):
        if obj.selfie != '':
            return obj.selfie.url
        return ''
    
    def datos_basicos(self, obj):
        if obj.first_name != None:
            return True
        return False
    
    def resident_info(self, obj):
        if Residentialplace.objects.filter(user = obj).exists():
            return True
        return False
    
    def workplace_info(self, obj):
        if Workplace.objects.filter(user = obj).exists():
            return True
        return False
    
    def financial_info(self, obj):
        if Financial.objects.filter(user = obj).exists():
            return True
        return False
    
    def socioeconomic_info(self, obj):
        if Socioeconomic.objects.filter(user = obj).exists():
            return True
        return False
    
    def get_last_login(self, obj):
        hora = obj.last_frontend_access.astimezone(timezone.get_current_timezone())
        return hora.strftime('%I:%M%p %d/%m/%Y')
    def get_password_expires(self, obj):
        today = dt.date.today()
        if obj.last_password_change:
            delta = today - obj.last_password_change
        else:
            obj.last_password_change = today
            obj.save()

        diferencia = PASSWORD_EXPIRY_DAYS - int(delta.days)
        return f'{diferencia} días'
    
    
class UserSponsorInfoSerializer(serializers.ModelSerializer):
    role = RoleSerializerDetail(read_only=True)
    subrole = serializers.SerializerMethodField('get_subrole_info')
    has_datos_basicos =  serializers.SerializerMethodField('datos_basicos')
    has_resident_info =  serializers.SerializerMethodField('resident_info')
    has_financial_info =  serializers.SerializerMethodField('financial_info')
    has_sponsor_company = serializers.SerializerMethodField('sponsor_company_info')
    full_name = serializers.SerializerMethodField('get_full_name')
    perfil_image = serializers.SerializerMethodField('get_perfil_image')
    last_login =serializers.SerializerMethodField('get_last_login')
    password_expires = serializers.SerializerMethodField('get_password_expires')

    class Meta:
        model = User
        fields = [
            'id', 'email', 'code', 'phone', 'role', 'subrole',
            'full_name',
            'perfil_image',
            'has_datos_basicos',
            'has_resident_info',
            'has_financial_info',
            'has_sponsor_company',
            'last_login',
            'password_expires'
            ]

    def get_subrole_info(self, obj):
        dict = {}
        try:
            dict['id'] = obj.groups.all()[0].id
            dict['name'] = obj.groups.all()[0].name
        except:
            dict['id'] = ''
            dict['name'] = ''
        return dict
    
    def get_full_name(self, obj):
        if obj.first_name != '':
            return f'{obj.first_name} {obj.last_name}'
        return ''
    
    def get_perfil_image(self, obj):
        if obj.selfie != '':
            return obj.selfie.url
        return ''
    
    def datos_basicos(self, obj):
        if obj.first_name != None:
            return True
        return False
    
    def resident_info(self, obj):
        if Residentialplace.objects.filter(user = obj).exists():
            return True
        return False
    
    def financial_info(self, obj):
        if Financial.objects.filter(user = obj).exists():
            return True
        return False
    
    
    def sponsor_company_info(self, obj):
        if SponsorCompany.objects.filter(user = obj).exists():
            return True
        return False
    
    def get_last_login(self, obj):
        hora = obj.last_frontend_access.astimezone(timezone.get_current_timezone())
        return hora.strftime('%I:%M%p %d/%m/%Y')
    
    def get_password_expires(self, obj):
        today = dt.date.today()
        delta = today - obj.last_password_change
        diferencia = PASSWORD_EXPIRY_DAYS - int(delta.days)
        PASSWORD_EXPIRY_DAYS
        return f'{diferencia} días'
    
    
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetFormSerializer(serializers.Serializer):
    password_confirmation = serializers.CharField()
    password = serializers.CharField()

class CreateUserFormSerializer(serializers.ModelSerializer):

    class Meta:
        
        model = User
        fields = ['id', 'email', 'referred_by_code', 'phone', 'password', 'role', 'groups']
        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'slug': {
                'read_only': True
            },
        }
        
    def _save_user_password(self, user, password):
        user.set_password(password)
        user.save()
        return user

    def create(self, validated_data):
        password = validated_data.pop('password')
        phone = validated_data.pop('phone', None)
        if phone:
            indicativo, numero_telefono = phone.split('*')
            validated_data['indicative'] = indicativo
            validated_data['phone'] = numero_telefono
        user = super(CreateUserFormSerializer, self).create(validated_data)
        # user.is_active = False  OJO POR AHORA TODOS VAN ACTIVOS
        user.verify_email()
        return self._save_user_password(user, password)

    

    # def create(self, validated_data):
    #     
    #     user = super(CreateUserFormSerializer, self).create(validated_data)
    #     user.is_active = False
    #     user.verify_email()
    #     return 
    
class IdtypesListSerializer(serializers.ModelSerializer):

    class Meta:
        model = IdType
        fields = [ 'id', 'value', 'name', 'description']
