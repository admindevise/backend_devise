from rest_framework import generics
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone

from ..models import User
from apps.user.models_permission import UserAdminPermission
from ..serializers.basic_info_user_serializer import UserBasicInfoSerializer

@permission_classes([AllowAny])
class VerifyReferredCode(APIView):
    queryset = User.objects.all()

    def get(self, request, *args, **kwargs):
        referred_code =self.kwargs.get('referred_code')
        try:
            user_referred = User.objects.get(code = referred_code)
            data = {

                    "user": f'{user_referred.first_name} {user_referred.last_name}',
                    "found": True,
                    "message": "User with this code exists",
                }
            return JsonResponse(data)
        
        except:
            data = {
                    "user": "not exist",
                    "found": False,
                    "message": "User with this code not exists",
                }
            return JsonResponse(data)

@permission_classes([IsAuthenticated])
class UpdateReadUserBasicInfo(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserBasicInfoSerializer

    def get_object(self):
        # Returns the User related 
        return self.request.user
    def perform_update(self, serializer):
        print("pasando por el update donde conecto el KYC")
        try:
            if serializer.validated_data['document_front_image']:
                print("Contiene la imagen")
                serializer.validated_data['kyc_validated'] = 'ready_for_kyc'
        except:
            print("Sin cambio en la imagen")

        serializer.save()

@permission_classes([IsAuthenticated])
class AdminUpdateUserBasicInfo(generics.RetrieveUpdateAPIView):
    """Vista para que admin edite cualquier usuario por ID"""
    queryset = User.objects.all()
    serializer_class = UserBasicInfoSerializer
    lookup_field = 'pk'

    def get_object(self):
        """Valida permisos de admin antes de permitir acceso"""
        user_id = self.kwargs.get('pk')
        current_user = self.request.user
        
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise User.DoesNotExist(f"Usuario con ID {user_id} no encontrado")
        
        # ✅ CASO 1: Superusuario - acceso total
        if current_user.is_superuser:
            print(f"🔑 Superuser {current_user.email} editing user {target_user.email}")
            return target_user
        
        # ✅ CASO 2: Admin con permiso específico del usuario
        if current_user.is_staff:
            permission = UserAdminPermission.objects.filter(
                user=target_user,
                admin_user=current_user,
                permission_type__in=['EDIT_PROFILE', 'FULL_ACCESS'],
                status='ACTIVE',
                expires_at__gt=timezone.now()
            ).first()
            
            if permission:
                # Marcar como usado
                permission.mark_used()
                print(f"✅ Admin {current_user.email} has valid permission to edit {target_user.email}")
                return target_user
            else:
                print(f"❌ Admin {current_user.email} has no valid permission for user {target_user.email}")
                raise PermissionDenied(
                    f"No tienes permiso para editar al usuario {target_user.email}. "
                    "Solicita al usuario que te otorgue permisos temporales."
                )
        
        # ✅ CASO 3: Usuario normal - solo su propio perfil
        if current_user == target_user:
            print(f"👤 User {current_user.email} editing own profile")
            return current_user
        
        # ❌ CASO 4: Sin permisos
        raise PermissionDenied("No tienes permisos para editar este usuario")

    def perform_update(self, serializer):
        """Lógica de actualización con logs de permisos"""
        target_user = self.get_object()
        current_user = self.request.user
        
        print(f"🔄 UPDATING USER DATA:")
        print(f"  └─ Target user: {target_user.email} (ID: {target_user.id})")
        print(f"  └─ Updated by: {current_user.email} (Admin: {current_user.is_staff})")
        
        # Lógica KYC (mantener la existente)
        try:
            if serializer.validated_data.get('document_front_image'):
                print("  └─ Document image provided, setting KYC status")
                serializer.validated_data['kyc_validated'] = 'ready_for_kyc'
        except Exception as e:
            print(f"  └─ No document image change: {str(e)}")

        serializer.save()
        print(f"✅ User {target_user.email} updated successfully")