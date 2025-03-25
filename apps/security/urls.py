from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.useradmin import ConfigRulesSecurityView, UnlockAttemptsView, UserLockedListView
from apps.security.views.api_views import UserLockedViewSet, UnlockUserAPIView, SecurityConfigurationViewSet

router = DefaultRouter()
router.register(r'config', SecurityConfigurationViewSet, basename='config')

urlpatterns = [
    path('api/', include(router.urls)),
    
    #============================= Templates Views Usuarios =================================

    path('view/lock/list/', UserLockedListView.as_view(), name=UserLockedListView.url_name),
    path('unlock/attempts/', UnlockAttemptsView.as_view(), name=UnlockAttemptsView.url_name),
    path('configure/rules/<int:pk>/', ConfigRulesSecurityView.as_view(), name=ConfigRulesSecurityView.url_name),
    
     #============================= APIREST Views Model =================================

    path('api/user/locked/', UserLockedViewSet.as_view({'get': 'list'}), name='user-locked-list-api'),
    path('api/user/unlock/', UnlockUserAPIView.as_view(), name='unlock-user-api'),
    #path('api/config/', SecurityConfigurationViewSet.as_view({'get': 'list'}), name='security-config-api'),
]