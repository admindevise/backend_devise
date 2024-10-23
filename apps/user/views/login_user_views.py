from datetime import datetime
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password

from apps.user.models import User, IdType, Role, PasswordReset
from apps.utils.permissions import CustomDjangoModelPermission
from ..serializers.create_new_user_serializer import (CreateUserFormSerializer,
                                        UserBasicInfoSerializer, UserSponsorInfoSerializer,
                                        PasswordResetSerializer, PasswordResetFormSerializer,
                                        IdtypesListSerializer,
                                        )

from rest_framework import generics
from rest_framework import status

from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from apps.kaleido.models import Wallet
from apps.kaleido.views import kaleido_views

# =============================================================================
#                           APIREST USER RESOURCE
# =============================================================================

class UserViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    """
        Create and update user
    """
    http_method_names = ['post', 'get', 'patch']
    serializer_class = CreateUserFormSerializer
    queryset = User.objects
    # lookup_field = 'slug'

    def create(self, request, *args, **kwargs):
        # Validar la contraseña utilizando validate_password
        password = request.data.get('password')
        try:
            validate_password(password)
        except Exception as e:
            return Response(
                {
                    "type": "validation_error",
                    "errors": [
                        {
                            "code": "password_validation_error",
                            "detail": str(e),
                            "attr": "Password"
                        }
                    ]
                }, status.HTTP_400_BAD_REQUEST
            )
        #Verificar teléfono
        phone_number = request.data.get('phone')
        phone = phone_number.split('*')
        phone_exists = User.objects.filter(phone=phone[1],indicative=phone[0]).exists()

        if phone_exists:
            return Response(
                    {
                        "type": "validation_error",
                        "errors": [
                            {
                                "code": "phone_validation_error",
                                "detail": "¡El numero de teléfono ya se encuentra registrado!",
                                "attr": "Phone"
                            }
                        ]
                    }, status.HTTP_400_BAD_REQUEST
                )

        created_user = super().create(request, *args, **kwargs)
        #******************WALLET********************#
        print("*************************>CREATE USER<*************************")
        success = False
        if created_user.status_code == 201:
            id_user = created_user.data.get('id')
            success = createSaveWallet(id_user)
            print(f"Id user from createSaveWallet: {success}")
            if not success:
                usuario = User.objects.get(id=id_user)
                usuario.delete()
                return Response(
                    {
                        "type": "wallet_creation",
                        "errors": [
                            {
                                "code": "walle_err",
                                "detail": "¡No se ha podido crear la billetera asociada!",
                                "attr": "wallet"
                            }
                        ]
                    }, status.HTTP_400_BAD_REQUEST
                )
         #******************WALLET********************#
        
        return created_user
    
    def get_permissions(self):
        """
            Instantiates and returns the list of permissions that this view requires.
        """
        permission_classes = (
            IsAuthenticated,
        )

        if self.action == 'create':
            permission_classes = []

        return [permission() for permission in permission_classes]

def createSaveWallet(id_user):
    id = id_user
    success = False
    keleido_response = kaleido_views.createWallet()
    print(f"data--------------->{keleido_response['id']}")
    if keleido_response != None:
        #data = keleido_response.json()  # Si la respuesta es JSON
        data = keleido_response
        usuario = User.objects.get(id=id)

        response = Wallet.objects.create(user=usuario,id_wallet=data.get("id"), secret=data.get("secret"),environment_id=data.get("environment_id"),wallet_service=data.get("wallet_service"),zone_domain=data.get("zone_domain"),consortia=data.get("consortia"))
        if response:
            success = True   
    
    return success

@permission_classes([IsAuthenticated])
class MeApiView(RetrieveAPIView):
    """
        Returns basic information of the current user, depending if are sponsor return diferent array seializer
    """

    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        user = self.request.user
        group_names = user.groups.values_list('name', flat=True)
        if 'SPONSOR' in group_names:
            return UserSponsorInfoSerializer
        else:
            return UserBasicInfoSerializer
        


class ActiveEmailView(APIView):
    """
        Active by slug the user email so can log on
    """
    permission_classes = []

    def get(self, request, *args, **kwargs):
        slug_user = request.query_params.get('verify_email')

        if not (User.objects.filter(slug=slug_user).exists()):
            raise ValidationError(
                detail = { 'verify_email': 'token_invalid'},
                code = status.HTTP_403_FORBIDDEN
            )
        user = User.objects.get(slug=slug_user)
        user.is_active = True
        user.save()

        return Response({
            'active': True
        })

@permission_classes([CustomDjangoModelPermission])
class UserDetailApiView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserBasicInfoSerializer

@permission_classes([CustomDjangoModelPermission])
class UserUpdateApiView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserBasicInfoSerializer

    def perform_update(self, serializer):
        user_pk = self.kwargs.get('pk')  # Obtiene el valor de la clave primaria (PK) de la URL
        user = self.request.user  # Obtiene el usuario actual autenticado

        if user.pk != user_pk:
            print("pasando por aca")
            raise ValidationError(
                detail = {'detail': 'No puedes editar los datos de otro usuario'},
                code = status.HTTP_403_FORBIDDEN
            )
        serializer.save()

class PasswordResetView(APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        ''' Valida que el email enviado por el usuario sea valido '''
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email=serializer.validated_data.get('email')).first()

        if user:
            password_reset, _ = PasswordReset.objects.get_or_create(user=user)
            password_reset_slug = password_reset.slug

            user.password_reset_mail(
                password_reset_slug=password_reset_slug,
            )
            print(password_reset.slug)
            return Response(
                {
                    'email': serializer.validated_data.get('email')
                },
                201
            )

        return Response(
            {

                "type": "validation_error",
                "errors": [
                    {
                        "code": "not_exists",
                        "detail": "user with this email does not exists.",
                        "attr": "email"
                    }
                ]
            },
            400
        )

class PasswordResetDoneView(APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        ''' EJECUTA EL CAMBIO DE CLAVE '''
        if request.data.get('password') != request.data.get('password_confirmation'):
            return Response(
                        {
                            "type": "validation_error",
                            "errors": [
                                {   "code": "not_exists",
                                    "detail": "Boot password don't match ",
                                    "attr": "Password "
                                }
                            ] }, 401
                    )
        password_reset = PasswordReset.objects.filter(slug=kwargs.get('slug')).first()

        # Validar la contraseña utilizando validate_password
        password = request.data.get('password')
        try:
            validate_password(password, password_reset.user)
        except Exception as e:
            return Response(
                {
                    "type": "validation_error",
                    "errors": [
                        {
                            "code": "password_validation_error",
                            "detail": str(e),
                            "attr": "Password"
                        }
                    ]
                }, status.HTTP_400_BAD_REQUEST
            )

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
        if password_reset.get_is_valid_time() :
            password_reset.delete()
            return Response(
                        {
                            "type": "validation_error",
                            "errors": [
                                {   "code": "not_exists",
                                    "detail": "Se ha vencido el enlace de recuperación, debe solicitar uno nuevo",
                                    "attr": "Password Token"
                                }
                            ] }, 401
                    )
        serializer = PasswordResetFormSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password_reset.user.set_password(serializer.validated_data.get('password'))
        password_reset.user.last_password_change = datetime.now()
        password_reset.user.save()
        password_reset.delete()

        return Response(
            status=201
        )

@permission_classes([AllowAny]) 
class CheckSlugView(APIView):
    permission_classes = []
    
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


@permission_classes([IsAuthenticated])
class IdtypesListView(ListAPIView):
    """
        Returns list of id types
    """
    queryset = IdType.objects.filter(status=True)
    serializer_class = IdtypesListSerializer
    pagination_class = None

