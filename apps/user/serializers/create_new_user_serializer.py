from django.utils import timezone
# from apps.security.models import SecurityConfiguration
from apps.user.models import User, IdType, Role
from apps.info_residential.models import Residentialplace
from apps.info_workplace.models import Workplace
from apps.info_financial.models import Financial
from apps.info_socioeconomic.models import Socioeconomic
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers
from .role_serializer import RoleSerializerDetail
from apps.security.security_settings import get_password_expiry_days
import datetime as dt


# config = SecurityConfiguration.objects.first()
# PASSWORD_EXPIRY_DAYS = config.PASSWORD_EXPIRY_DAYS
class UserBasicInfoSerializer(serializers.ModelSerializer):
    role = RoleSerializerDetail(read_only=True)
    subrole = serializers.SerializerMethodField('get_subrole_info')
    has_basic_info =  serializers.SerializerMethodField('basic_info')
    has_resident_info =  serializers.SerializerMethodField('resident_info')
    has_workplace_info =  serializers.SerializerMethodField('workplace_info')
    has_financial_info =  serializers.SerializerMethodField('financial_info')
    has_socioeconomic_info = serializers.SerializerMethodField('socioeconomic_info')
    profile_image = serializers.SerializerMethodField('get_profile_image')
    last_login =serializers.SerializerMethodField('get_last_login')
    password_expires = serializers.SerializerMethodField('get_password_expires')

    class Meta:
        model = User
        fields = [
            'id', 'email', 'code', 'phone', 'role', 'subrole',
            'first_name', 'last_name',
            'profile_image',
            'has_basic_info',
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
    
    def get_profile_image(self, obj):
        if obj.selfie != '':
            return obj.selfie.url
        return ''
    
    def basic_info(self, obj):
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
            delta = today - obj.last_password_change

        diferencia = get_password_expiry_days() - int(delta.days)
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
    
    def get_last_login(self, obj):
        hora = obj.last_frontend_access.astimezone(timezone.get_current_timezone())
        return hora.strftime('%I:%M%p %d/%m/%Y')
    
    def get_password_expires(self, obj):
        today = dt.date.today()
        delta = today - obj.last_password_change
        diferencia = get_password_expiry_days() - int(delta.days)
        return f'{diferencia} días'
    

class UserAdminInfoSerializer(serializers.ModelSerializer):
    role = RoleSerializerDetail(read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'entity_nit', 'is_active', 'is_staff', 'is_superuser', 'role', 'date_joined')
        read_only_fields = ('id', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
        
    
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
        
    def validate(self, attrs):
        from apps.user.models import PasswordReset
        
        user = self.context['request'].user
        pk = self.context['pk']
        email = attrs.get('email')
        
        user_url = validate_it_self_user(pk, user)
        
        if user_url.email != email:
            raise serializers.ValidationError({"email": f"El correo electrónico no coincide con el usuario seleccionado. Usuario: {user_url.email}"})
        
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "No se encontró un usuario con este correo electrónico"})

        password_reset, _ = PasswordReset.objects.get_or_create(user=user_url)
        password_reset_slug = password_reset.slug

        user_url.password_reset_mail(
            password_reset_slug=password_reset_slug,
        )        
        print('slug enviado', password_reset_slug)
        return attrs

class PasswordResetDoneSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True)
    password_confirmation = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        from apps.user.models import PasswordReset
        
        password = attrs.get("password")
        password_confirmation = attrs.get("password_confirmation")
        user = self.context['request'].user
        slug = self.context.get("slug")
        pk = self.context.get("pk")
        
        _ = validate_it_self_user(pk, user)

        print('objetos de password reset', PasswordReset.objects.all())
        if password != password_confirmation:
            raise serializers.ValidationError({"password_confirmation": "Las contraseñas no coinciden"})

        password_reset = PasswordReset.objects.select_related("user").filter(
            slug=slug,
            user_id=pk
        ).first()

        if not password_reset:
            raise serializers.ValidationError({"token": "Este enlace no existe"})

        # Mantiene tu lógica actual: True = enlace vencido
        if password_reset.get_is_valid_time():
            password_reset.delete()
            raise serializers.ValidationError(
                {"token": "Se ha vencido el enlace de recuperación, debe solicitar uno nuevo"}
            )

        try:
            validate_password(password, password_reset.user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        attrs["password_reset"] = password_reset
        return attrs

    def save(self, **kwargs):
        password = self.validated_data["password"]
        password_reset = self.validated_data["password_reset"]
        user = password_reset.user

        user.set_password(password)
        user.last_password_change = timezone.now()
        user.save(update_fields=["password", "last_password_change"])

        password_reset.delete()
        return user

class CreateUserFormSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'referred_by_code', 'phone', 'password', 'role', 'groups']
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

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # Validar contraseña
        password = attrs.get('password')
        if not password:
            raise serializers.ValidationError({"password": "La contraseña es obligatoria"})
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        except Exception as e:
            raise serializers.ValidationError({"password": str(e)})

        # Validar teléfono (formato indicativo*número + unicidad)
        phone_number = attrs.get('phone')
        if not phone_number:
            raise serializers.ValidationError({"phone": "El número de teléfono es obligatorio"})

        try:
            indicative, phone = phone_number.split('*')
        except ValueError:
            raise serializers.ValidationError({
                "phone": "Formato de teléfono inválido. Use 'indicativo*número'"
            })

        if User.objects.filter(phone=phone, indicative=indicative).exists():
            raise serializers.ValidationError({
                "phone": "El número de teléfono ya se encuentra registrado"
            })

        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        phone = validated_data.pop('phone', None)
        if phone:
            indicativo, numero_telefono = phone.split('*')
            validated_data['indicative'] = indicativo
            validated_data['phone'] = numero_telefono
        user = super(CreateUserFormSerializer, self).create(validated_data)
        user.is_active = False  #OJO POR AHORA TODOS VAN ACTIVOS
        user.verify_email()
        print('se envio el correo con status is_active', {user.is_active})
        return self._save_user_password(user, password)

class CreateUserAdminSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'password', 'role', 'entity_nit', 'groups']
        read_only_fields = ['id', 'groups']
        extra_kwargs = {
            'password': {
                'write_only': True,
            },
            'slug': {
                'read_only': True
                },
            'entity_nit': {
                'required': True
                }
            }
        
    def _save_user_password(self, user, password):
        user.set_password(password)
        user.save()
        return user        
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        phone = validated_data.pop('phone', None)
        
        # Obtener el rol ADMINISTRADOR antes de crear el usuario
        admin_role = Role.objects.get(name='ADMINISTRADOR')
        validated_data['role'] = admin_role 
        
        if phone:
            indicativo, numero_telefono = phone.split('*')
            validated_data['indicative'] = indicativo
            validated_data['phone'] = numero_telefono
            
        user = super(CreateUserAdminSerializer, self).create(validated_data)
        user.is_active = False
        user.save()
        user.verify_email()
        print('se envio el correo para user admin con status is_active', {user.is_active})
        return self._save_user_password(user, password)
    
class IdtypesListSerializer(serializers.ModelSerializer):

    class Meta:
        model = IdType
        fields = [ 'id', 'value', 'name', 'description']


# ===========================================================
# Metodos auxiliares
# ===========================================================

def validate_it_self_user(pk, user):
    user_url = User.objects.filter(pk=pk).first()
    can_manage_passwords = user.is_superuser or user.is_staff
    is_self = user.pk == pk
    
    if not (can_manage_passwords or is_self):
        raise serializers.ValidationError({"detail": "No puedes restablecer la contraseña de otro usuario"})
    
    return user_url