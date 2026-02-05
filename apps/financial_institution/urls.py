from rest_framework.routers import DefaultRouter
from django.urls import path, include

from apps.financial_institution.views.core_views import (
    FinancialInstitutionViewSet,
    create_application,
    pre_approve_fi_application,
    send_contract_fi_application,
    sign_contract_fi_application,
    approve_application,
    reject_application,
)
from apps.financial_institution.views.utils_views import (
    MembersFinancialInstitutionViewSet,
    FinancialInstitutionApplicationViewSet,
    PendingFinancialInstitutionApplicationViewSet,
    get_dashboard_stats
)
from apps.financial_institution.views.permission_views import (
    FIPermissionViewSet,
    FICustomGroupViewSet,
    FIUserGroupMembershipViewSet,
    assign_user_to_group,
    remove_user_from_group,
    my_fi_permissions
)

router = DefaultRouter()
router.register(r'institutions', FinancialInstitutionViewSet, basename='financial_institution')
router.register(r'list-applications', FinancialInstitutionApplicationViewSet, basename='financial_institution_application')
router.register(r'members', MembersFinancialInstitutionViewSet, basename='members_financial_institution')
router.register(r'pending-applications', PendingFinancialInstitutionApplicationViewSet, basename='pending_financial_institution_application')

router.register(r'permissions', FIPermissionViewSet, basename='fi-permissions'),
router.register(r'groups', FICustomGroupViewSet, basename='fi-groups'),
router.register(r'memberships', FIUserGroupMembershipViewSet, basename='fi-memberships')

urlpatterns = [
    path('api/', include(router.urls)),
    
    # ==================================
    # Application Processing Endpoints
    # ==================================
    path('api/create-application/', create_application, name='financial_institution_approval'),
    path('api/applications/<int:application_id>/pre-approve/', pre_approve_fi_application, name='financial_institution_pre_approve'),
    path('api/applications/<int:application_id>/send-contract/', send_contract_fi_application, name='financial_institution_send_contract'),
    path('api/applications/<int:application_id>/sign-contract/', sign_contract_fi_application, name='financial_institution_sign_contract'),
    
    path('api/applications/<int:application_id>/approve/', approve_application, name='financial_institution_approve'),
    path('api/applications/<int:application_id>/reject/', reject_application, name='financial_institution_reject'),
    
    # ================================
    # PERMISSIONS
    # ================================
    path('api/permission/assing-user-to-group/', assign_user_to_group, name='assing-user-from-group'),
    path('api/permission/remove-user-from-group/', remove_user_from_group, name='rermove-user-from-group'),
    path('api/permission/my-permissions/', my_fi_permissions, name='my-permissions'),
    
    # ================================
    # DASHBOARD STATS
    # ================================
    path('api/dashboard/stats/', get_dashboard_stats, name='financial_institution_dashboard_stats'),
]
