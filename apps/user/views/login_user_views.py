from datetime import datetime
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from apps.user.models import User, IdType, Role, PasswordReset
from ..serializers.create_new_user_serializer import (
    CreateUserFormSerializer, CreateUserAdminSerializer, UserBasicInfoSerializer, UserSponsorInfoSerializer, PasswordResetSerializer, PasswordResetDoneSerializer, IdtypesListSerializer
    )

from rest_framework import generics
from rest_framework import status

from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.financial_institution.models.core import FinancialInstitution
from apps.kaleido.models import Wallet
from apps.kaleido.views import kaleido_views

# =============================================================================
#                           APIREST USER RESOURCE
# =============================================================================

class UserViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    """
        Create and update user
    """
    permission_classes = [RegistryPermission]
    http_method_names = ['post', 'get', 'patch']
    queryset = User.objects.all()
    # lookup_field = 'slug'
    
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.kwargs.get('pk'):
            validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            user_type = self.request.query_params.get('user_type')
            if user_type == 'admin':
                return CreateUserAdminSerializer
        
        return CreateUserFormSerializer
    
    
@permission_classes([IsAuthenticated, RegistryPermission])
class MeApiView(RetrieveAPIView):
    """
        Returns basic information of the current user, depending if are sponsor return diferent array seializer
    """
    serializer_class = UserBasicInfoSerializer
    
    def get_object(self):
        return self.request.user


class ActiveEmailView(APIView):
    """
        Active by slug the user email so can log on
    """
    permission_classes = [RegistryPermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not self.request.query_params.get('verify_email'):
            raise ValidationError(
                detail = { 'verify_email': 'Este parametro es requerido'},
                code = status.HTTP_400_BAD_REQUEST
            )

    def get(self, request, *args, **kwargs):
        slug_user = request.query_params.get('verify_email')

        if not (User.objects.filter(slug=slug_user).exists()):
            raise ValidationError(
                detail = { 'verify_email': 'Este enlace no es válido'},
                code = status.HTTP_403_FORBIDDEN
            )
        
        if User.objects.filter(slug=slug_user, is_active=True).exists():
            raise ValidationError(
                detail = { 'verify_email': 'Este enlace ya ha sido utilizado anteriormente o el usuario ya se encuentra activo'},
                code = status.HTTP_403_FORBIDDEN
            )
            
        user = User.objects.get(slug=slug_user)
        user.is_active = True
        user.save()

        return Response({
            'active': True
        })


@permission_classes([IsAuthenticated, RegistryPermission])
class UserUpdateApiView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserBasicInfoSerializer
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        return super().initial(request, *args, **kwargs)

    def perform_update(self, serializer):
        user_pk = self.kwargs.get('pk')  # Obtiene el valor de la clave primaria (PK) de la URL
        user = self.request.user  # Obtiene el usuario actual autenticado
        
        if not user.is_superuser and user.pk != user_pk:
            raise ValidationError(
                detail = {'detail': 'No puedes editar los datos de otro usuario'},
                code = status.HTTP_403_FORBIDDEN
            )
        serializer.save()


class PasswordResetView(APIView):
    permission_classes = [IsAuthenticated, RegistryPermission]

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        return super().initial(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        ''' Valida que el email enviado por el usuario sea valido '''
        serializer = PasswordResetSerializer(
            data=request.data,
            context={
                'request': request,
                'pk': self.kwargs.get('pk')
            }
        )
        serializer.is_valid(raise_exception=True)

        return Response({
            'success': True,
            'message': 'Se ha enviado un correo electrónico con las instrucciones para restablecer tu contraseña',
        }, status=201)


class PasswordResetDoneView(APIView):
    permission_classes = [IsAuthenticated, RegistryPermission]

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        return super().initial(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetDoneSerializer(
            data=request.data,
            context={
                'request': request,
                "pk": self.kwargs.get("pk"),
                "slug": self.kwargs.get("slug"),
            },
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"success": True, "message": "Contraseña actualizada correctamente"},
            status=status.HTTP_201_CREATED
        )


class CheckSlugView(APIView):
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        return super().initial(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        ''' Verificar código slug '''
        print(f"Slug-----------------> ")
        print(f"Slug: {kwargs.get('slug')}")
        password_reset = PasswordReset.objects.filter(slug=kwargs.get('slug')).first()
        
        if not password_reset:
            return Response(
                        {
                            "type": "validation_error",
                            "errors": [
                                {   "code": "not_exists",
                                    "detail": "Este enlace no existe",
                                    "attr": "Password Token"
                                }
                            ] }, 401
                    )
       

        return Response(
            status=200
        )


class IdtypesListView(ListAPIView):
    """
        Returns list of id types
    """
    queryset = IdType.objects.filter(status=True)
    serializer_class = IdtypesListSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    pagination_class = None
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        return super().initial(request, *args, **kwargs)

