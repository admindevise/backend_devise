from ..models import User
from ..serializers.basic_info_user_serializer import UserBasicInfoSerializer

from django.shortcuts import get_object_or_404


from rest_framework import generics

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import JsonResponse
from rest_framework.views import APIView


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
        



    #     


   