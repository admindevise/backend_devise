from rest_framework import generics
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone

from ..models import User
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.user.models_permission import UserAdminPermission
from ..serializers.basic_info_user_serializer import UserBasicInfoSerializer


class VerifyReferredCode(APIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, RegistryPermission]

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        super().initial(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        referred_code =self.kwargs.get('referred_code')
        try:
            user_referred = User.objects.get(code=referred_code)
            data = {

                    "user": f'{user_referred.first_name} {user_referred.last_name}',
                    "found": True,
                    "message": "El código de referido es válido",
                }
            return JsonResponse(data)
        
        except:
            data = {
                    "user": "not exist",
                    "found": False,
                    "message": "El código de referido no es válido",
                }
            return JsonResponse(data)

class UpdateReadUserBasicInfo(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserBasicInfoSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]

    def initial(self, request, *args, **kwargs):
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))
        return super().initial(request, *args, **kwargs)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['pk'] = self.kwargs.get('pk')
        return context
    
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

class AdminUpdateUserBasicInfo(generics.RetrieveUpdateAPIView):
    """Vista para que admin edite cualquier usuario por ID"""
    from apps.user.models_permission import UserAdminPermission
    
    queryset = User.objects.all()
    serializer_class = UserBasicInfoSerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    lookup_field = 'pk'

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        validate_entity_exists(User, 'Usuario', self.kwargs.get('pk'))        
        validate_entity_exists(User, 'Usuario', self.kwargs.get('target_id'))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['pk'] = self.kwargs.get('pk')
        context['target_id'] = self.kwargs.get('target_id')
        return context
  

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