from django.urls import  path
from rest_framework import routers
from .views.login_user_views import ( UserViewSet, MeApiView, UserDetailApiView,
                                    UserUpdateApiView, ActiveEmailView,
                                    PasswordResetView, PasswordResetDoneView, IdtypesListView,CheckSlugView,
                                    
                            )
from .views.backoffice_user_views import (  UserListView,  UserCreateView, UserDetailView, 
                                            UserDeactivateView, UserDeleteView,
                                            UserBasicInfoUpdateView, UserDocumentUpdateView,
                                            UserResidentialCreateView, UserResidentialUpdateView, UserSocieconomicUpdateView, UserSocioeconomicCreateView,
                                            UserWorkplaceUpdateView, UserWorkplaceCreateView,
                                            UserFinancialCreateView, UserFinancialUpdateView,
                                            UserListExportView
                                            )
from .views.roles_views import (RoleApiListView, RoleListView, RoleAddView, RoleDetailView, 
                                RoleUpdateView, RoleDeleteView)

from .views.subrole_views import (SubRoleApiListView, SubroleListView, SubroleCreateView, 
                                  SubroleDetailView, SubroleUpdateView)

from .views.api_user_views import ( VerifyReferredCode, UpdateReadUserBasicInfo)

from apps.user.views.backoffice_config_views import IdTypeCreateView, IdTypeDeleteView, IdTypeDetailView, IdTypeListView, IdTypeUpdateView, IdtypeDeactivateView
from apps.user.views.backoffice_config_views import AccountTypeCreateView, AccountTypeDeleteView, AccountTypeDetailView, AccountTypeListView, AccountTypeUpdateView, AccountTypeDeactivateView
from apps.user.views.backoffice_config_views import AccountSubtypeCreateView, AccountSubtypeDeleteView, AccountSubtypeDetailView, AccountSubtypeListView, AccountSubtypeUpdateView, AccountSubtypeDeactivateView
from apps.user.views.backoffice_config_views import BankCreateView, BankDeleteView, BankDetailView, BankListView, BankUpdateView, BankDeactivateView


router = routers.SimpleRouter()

router.register('', UserViewSet, basename='urls_user')


urlpatterns = [

    # ============================= Templates Views Role =================================
    path('role/list/', RoleListView.as_view(), name=RoleListView.url_name),
    path('role/create/', RoleAddView.as_view(), name=RoleAddView.url_name),
    path('role/<int:pk>/detail/', RoleDetailView.as_view(), name=RoleDetailView.url_name),
    path('role/<int:pk>/update/', RoleUpdateView.as_view(), name=RoleUpdateView.url_name),
    path('role/delete/', RoleDeleteView.as_view(), name=RoleDeleteView.url_name),


    # ============================= Templates Views SubRole extends from GROUP ===========
    path('subrole/list/', SubroleListView.as_view(), name=SubroleListView.url_name),
    path('subrole/create/', SubroleCreateView.as_view(), name=SubroleCreateView.url_name),
    path('subrole/<int:pk>/detail/', SubroleDetailView.as_view(), name=SubroleDetailView.url_name),
    path('subrole/<int:pk>/update/', SubroleUpdateView.as_view(), name=SubroleUpdateView.url_name),
    
    #============================= Templates Views Usuarios =================================
    path('viewlist/', UserListView.as_view(), name=UserListView.url_name),
    path('list/export/', UserListExportView.as_view(), name=UserListExportView.url_name),
    path('viewcreate/', UserCreateView.as_view(), name=UserCreateView.url_name),
    path('view/<int:pk>/detail/', UserDetailView.as_view(), name=UserDetailView.url_name),
    # path('view/<int:pk>/update/', UserUpdateView.as_view(), name=UserUpdateView.url_name),
    path('basic/<int:pk>/update/', UserBasicInfoUpdateView.as_view(), name=UserBasicInfoUpdateView.url_name),
    path('documental/<int:pk>/update/', UserDocumentUpdateView.as_view(), name=UserDocumentUpdateView.url_name),

    path('residencial/<int:pk>/update/', UserResidentialUpdateView.as_view(), name=UserResidentialUpdateView.url_name),
    path('residencial/<int:pk>/create/', UserResidentialCreateView.as_view(), name=UserResidentialCreateView.url_name),

    path('workplace/<int:pk>/update/', UserWorkplaceUpdateView.as_view(), name=UserWorkplaceUpdateView.url_name),
    path('workplace/<int:pk>/create/', UserWorkplaceCreateView.as_view(), name=UserWorkplaceCreateView.url_name),

    path('financial/<int:pk>/update/', UserFinancialUpdateView.as_view(), name=UserFinancialUpdateView.url_name),
    path('financial/<int:pk>/create/', UserFinancialCreateView.as_view(), name=UserFinancialCreateView.url_name),


    path('socieconomic/<int:pk>/create/', UserSocioeconomicCreateView.as_view(), name=UserSocioeconomicCreateView.url_name),
    path('socioeconomic/<int:pk>/update/', UserSocieconomicUpdateView.as_view(), name=UserSocieconomicUpdateView.url_name),

    path('deactivate/', UserDeactivateView.as_view(), name=UserDeactivateView.url_name),
    path('delete/', UserDeleteView.as_view(), name=UserDeleteView.url_name),

    

    # # ========================  Api User Endpoints  ===============================
    path('active/', ActiveEmailView.as_view()),
    path('me/', MeApiView.as_view()),
    path('view/<int:pk>/', UserDetailApiView.as_view()),
    path('update/<int:pk>/', UserUpdateApiView.as_view()),
    path('password/reset/', PasswordResetView.as_view()),
    path('password/reset/done/<slug:slug>/', PasswordResetDoneView.as_view()),
    path('password/verify/code/<slug:slug>/', CheckSlugView.as_view()),

    # # ========================  Api User basic data  ===============================
    path('basicdata/update_read/', UpdateReadUserBasicInfo.as_view()), #same url Patch or Get
    path('verify/referred/<slug:referred_code>/code/', VerifyReferredCode.as_view(), name='verify-referred-code'),

    # ============================= API Views IdTypes  ==================================
    path('idtypes/list/', IdtypesListView.as_view(), name="id-apilist"),

    # ============================= API Views SubRole  ==================================
    path('role/api/list/', RoleApiListView.as_view(), name="role-apilist"),
    path('subrole/api/list/<int:role_id>/', SubRoleApiListView.as_view(), name="subrole-apilist"), #BACKOFFICE

    ## ================= IdType Urls backoffice config
    path('idtype/create/', IdTypeCreateView.as_view(), name='idtype-create'),
    path('idtype/list/', IdTypeListView.as_view(), name='idtype-list'),
    path('idtype/<int:pk>/detail/', IdTypeDetailView.as_view(), name='idtype-detail'),
    path('idtype/<int:pk>/update/', IdTypeUpdateView.as_view(), name='idtype-update'),
    path('idtype/delete/', IdTypeDeleteView.as_view(), name='idtype-delete'),
    path('idtype/deactivate/', IdtypeDeactivateView.as_view(), name='idtype-deactivate'),
    ## ================= Account Type Urls backoffice config
    path('account_type/create/', AccountTypeCreateView.as_view(), name='accounttype-create'),
    path('account_type/list/', AccountTypeListView.as_view(), name='accounttype-list'),
    path('account_type/<int:pk>/detail/', AccountTypeDetailView.as_view(), name='accounttype-detail'),
    path('account_type/<int:pk>/update/', AccountTypeUpdateView.as_view(), name='accounttype-update'),
    path('account_type/delete/', AccountTypeDeleteView.as_view(), name='accounttype-delete'),
    path('account_type/deactivate/', AccountTypeDeactivateView.as_view(), name='accounttype-deactivate'),
    ## ================= Subaccount Type Urls backoffice config
    path('account_subtype/create/', AccountSubtypeCreateView.as_view(), name='accountsubtype-create'),
    path('account_subtype/list/', AccountSubtypeListView.as_view(), name='accountsubtype-list'),
    path('account_subtype/<int:pk>/detail/', AccountSubtypeDetailView.as_view(), name='accountsubtype-detail'),
    path('account_subtype/<int:pk>/update/', AccountSubtypeUpdateView.as_view(), name='accountsubtype-update'),
    path('account_subtype/delete/', AccountSubtypeDeleteView.as_view(), name='accountsubtype-delete'),
    path('account_subtype/deactivate/', AccountSubtypeDeactivateView.as_view(), name='accountsubtype-deactivate'),
    ## ================= Bank Urls backoffice config
    path('bank/create/', BankCreateView.as_view(), name='bank-create'),
    path('bank/list/', BankListView.as_view(), name='bank-list'),
    path('bank/<int:pk>/detail/', BankDetailView.as_view(), name='bank-detail'),
    path('bank/<int:pk>/update/', BankUpdateView.as_view(), name='bank-update'),
    path('bank/delete/', BankDeleteView.as_view(), name='bank-delete'),
    path('bank/deactivate/', BankDeactivateView.as_view(), name='bank-deactivate'),
    

]

urlpatterns += router.urls