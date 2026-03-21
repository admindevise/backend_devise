from django.urls import  path, include
from rest_framework import routers

from .views.login_user_views import (
    UserViewSet,
    MeApiView,
    UserUpdateApiView,
    ActiveEmailView,
    PasswordResetView,
    PasswordResetDoneView,
    IdtypesListView,
    CheckSlugView
    )


from .views.roles_views import (RoleApiListView, RoleViewSet)

from .views.subrole_views import (SubRoleApiListView, SubroleViewSet)

from .views.api_user_views import ( VerifyReferredCode, UpdateReadUserBasicInfo, AdminUpdateUserBasicInfo)

from apps.user.views.import_users import ImportUsersAPIView

from apps.user.views.users_api import ListUsersAPIView

from apps.user.views.grant_permission_view import (
    GrantAdminPermissionView,
    ListUserPermissionsView,
    RevokeAdminPermissionView,
    RevokeAllPermissionsView
)


router = routers.DefaultRouter()

router.register('', UserViewSet, basename='urls_user')
router.register('role/', RoleViewSet, basename='urls_role')
router.register('subrole/', SubroleViewSet, basename='urls_subrole')

urlpatterns = [   
    # ==========================================================
    # API Views User
    # ==========================================================
    path('active/', ActiveEmailView.as_view()),
    path('me/', MeApiView.as_view()),
    path('<int:pk>/', UserUpdateApiView.as_view()),
    path('<int:pk>/password/reset/', PasswordResetView.as_view()),
    path('<int:pk>/password/reset/done/<slug:slug>/', PasswordResetDoneView.as_view()),
    path('<int:pk>/password/verify/code/<slug:slug>/', CheckSlugView.as_view()),

    # ==========================================================
    # API Views Basic Info User
    # ==========================================================
    path('<int:pk>/basicdata/', UpdateReadUserBasicInfo.as_view()), #same url Patch or Get
    path('<int:pk>/admin/users/<int:target_id>/basicdata/', AdminUpdateUserBasicInfo.as_view()), #admin update user basic info by pk
    path('<int:pk>/verify/referred/<str:referred_code>/code/', VerifyReferredCode.as_view(), name='verify-referred-code'),

    # ==========================================================
    # API Views Id Types
    # ==========================================================
    path('<int:pk>/idtypes/list/', IdtypesListView.as_view(), name="id-apilist"),

    # ==========================================================
    # API Views Roles y Subroles
    # ==========================================================
    #path('role/api/list/', RoleApiListView.as_view(), name="role-apilist"),
    #path('subrole/api/list/<int:role_id>/', SubRoleApiListView.as_view(), name="subrole-apilist"),
    
    # ==========================================================
    # API Views Import Users
    # ==========================================================
    path('<int:pk>/import/', ImportUsersAPIView.as_view(), name='import-users'),
    
    # ==========================================================
    # API Views List Users
    # ==========================================================
    path('<int:pk>/list/', ListUsersAPIView.as_view(), name='user-apilist'),

    # ==========================================================
    # API Views Permissions    
    # ==========================================================
    path('<int:pk>/fund/<int:fund_id>/permissions/grant/', GrantAdminPermissionView.as_view(), name='grant-admin-permission'),
    path('<int:pk>/fund/<int:fund_id>/permissions/list/', ListUserPermissionsView.as_view(), name='list-user-permissions'),
    path('<int:pk>/fund/<int:fund_id>/permissions/revoke/', RevokeAdminPermissionView.as_view(), name='revoke-admin-permission'),
    path('<int:pk>/fund/<int:fund_id>/permissions/revoke/all/', RevokeAllPermissionsView.as_view(), name='revoke-all-permissions'),
    
    path('', include(router.urls)), 
]

urlpatterns += router.urls