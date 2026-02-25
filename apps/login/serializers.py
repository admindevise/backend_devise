from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.user.models import User
from apps.security.models import SecurityConfiguration
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    
    def validate(self, attrs):
        # Mover la consulta aquí, dentro del método
        config = SecurityConfiguration.objects.first()
        if not config:
            raise ValidationError({'detail': 'Configuración de seguridad no encontrada'})
        
        max_failed_attempts = config.max_failed_login_attempts
        login_lockout_duration = config.login_lockout_duration.total_seconds() // 60
        cadena_minutos = f"{int(login_lockout_duration)} minutos"
        
        print("entra a validate")
        print("max_failed_attempts", max_failed_attempts)
        # Intenta recuperar la información del usuario y la solicitud
        try:
            request = self.context["request"]
            print("request ", request)
            email = attrs.get("email")
            print("emailemail ", email)
            if User.objects.filter(email=email).exists():
                usuario = User.objects.get(email=email)
                usuario.failed_attempts = usuario.failed_attempts + 1
                usuario.last_failed_access = timezone.now()
                usuario.save()
                if usuario.failed_attempts > max_failed_attempts:
                    print("Pailas tienes que intentar luego")
                    raise ValidationError(
                        detail={'detail': f'Ha alcanzado el maximo de intentos de ingreso intente despues de: {cadena_minutos}'},
                        code='reach_max_attempts'
                    )
            
        except KeyError:
            print("keyerror...")
            return super(CustomTokenObtainPairSerializer, self).validate(attrs)

        data = super(CustomTokenObtainPairSerializer, self).validate(attrs)
        usuario.failed_attempts = 0
        usuario.last_frontend_access = timezone.now()
        usuario.save()
        return data