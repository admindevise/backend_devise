from rest_framework import status, viewsets, generics, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from datetime import timedelta

from apps.security.serializers import SecurityConfigurationSerializer
from apps.security.models import SecurityConfiguration
from apps.user.models import User
from apps.user.serializers.basic_info_user_serializer import UserBasicInfoSerializer

class UserLockedViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing locked users (users with 3+ failed login attempts).
    Only accessible to staff users.
    
    list:
    Return a list of all locked users.
    
    retrieve:
    Return details of a specific locked user.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = UserBasicInfoSerializer
    
    def get_queryset(self):
        filter_list = self.request.query_params.getlist('filter')
        filters = Q()
        if filter_list:
            for filter_term in filter_list:
                fields = [
                    'email__icontains',
                    'phone__icontains',
                ]
                for str_field in fields:
                    filters |= Q(**{str_field: filter_term})
                    
        queryset = User.objects.filter(failed_attempts__gte=3)
        queryset = queryset.filter(filters).order_by('email')
        
        filter_verified = self.request.query_params.get('verified')
        if filter_verified:
            if filter_verified == '0':
                queryset = queryset.filter(status=False)
            elif filter_verified == '1':
                queryset = queryset.filter(status=True)
                
        return queryset


class UnlockUserAPIView(APIView):
    """
    API endpoint for unlocking users by resetting their failed login attempts.
    Only accessible to staff users.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user = get_object_or_404(User, pk=user_id)
        user.failed_attempts = 0
        user.save()
        
        return Response(
            {
                'status': 'success',
                'message': 'User login attempts have been reset successfully'
            },
            status=status.HTTP_200_OK
        )


class SecurityConfigurationViewSet(viewsets.GenericViewSet, 
                                   mixins.RetrieveModelMixin,
                                   mixins.UpdateModelMixin):
    """
    API endpoint for viewing and editing security configuration.
    Only accessible to staff users.
    
    retrieve:
    Return the security configuration settings
    
    update/partial_update:
    Update the security configuration settings
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = SecurityConfigurationSerializer
    queryset = SecurityConfiguration.objects.all()
    
    def get_object(self):
        """
        Always return the first security configuration instance,
        creating one if none exists.
        """
        queryset = self.get_queryset()
        obj = queryset.first()
        
        # Create default configuration if none exists
        if not obj:
            obj = SecurityConfiguration.objects.create(
                password_similarity_limit=5,
                max_failed_login_attempts=3,
                login_lockout_duration=timedelta(minutes=30),
                password_expiry_days=90,
                password_max_delta_change=timedelta(minutes=30)
            )
        
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj
    
    def list(self, request, *args, **kwargs):
        """
        Override list to return the single configuration instance
        """
        return self.retrieve(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """
        Update security configuration and return success message
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        response_data = serializer.data
        response_data['status'] = 'success'
        response_data['message'] = 'Security configuration updated successfully'
        
        return Response(response_data)