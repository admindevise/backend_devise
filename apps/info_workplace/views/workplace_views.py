from ..models import Workplace
from ..serializers.workplace_serializers import CreateWorkplaceSerializer
from rest_framework.exceptions import ValidationError

from rest_framework import generics

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


@permission_classes([IsAuthenticated])
class CreateWorkplace(generics.CreateAPIView):
    queryset = Workplace.objects.all()
    serializer_class = CreateWorkplaceSerializer

    def perform_create(self, serializer):
        if Workplace.objects.filter(user = self.request.user).exists():
             raise ValidationError(
                detail = {'detail': 'Workplace info already created'},
                code = status.HTTP_403_FORBIDDEN
            )
        serializer.save(user=self.request.user)

@permission_classes([IsAuthenticated])
class UpdateReadWorkplace(generics.RetrieveUpdateAPIView):
    queryset = Workplace.objects.all()
    serializer_class = CreateWorkplaceSerializer

    def get_object(self):

        if Workplace.objects.filter(user = self.request.user).exists():
            return Workplace.objects.get(user=self.request.user)
        
        raise ValidationError(
                detail = {'detail': 'Workplace info not created'},
                code = status.HTTP_403_FORBIDDEN
            )
        