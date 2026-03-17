from rest_framework.routers import DefaultRouter
from django.urls import path, include

from apps.financial_institution.views.core_views import (
    FinancialInstitutionViewSet,
    FIApplicationActionsViewSet
)
from apps.financial_institution.views.utils_views import (
    MembersFinancialInstitutionViewSet,
    FinancialInstitutionApplicationViewSet,
    PendingFinancialInstitutionApplicationViewSet,
    RetrieveDashboardStatsView,
)
from apps.financial_institution.views.permission_views import (
    FIPermissionViewSet,
    FICustomGroupViewSet,
    FIUserGroupMembershipViewSet,
    FIGroupMembershipActionsViewSet,
)

router = DefaultRouter()
router.register(r'institutions', FinancialInstitutionViewSet, basename='financial_institution')
router.register(
    r'(?P<fi_id>[^/.]+)/list-applications',
    FinancialInstitutionApplicationViewSet,
    basename='financial_institution_applications'
)
router.register(
    r'(?P<fi_id>[^/.]+)/members',
    MembersFinancialInstitutionViewSet,
    basename='financial_institution_members'
)
router.register(
    r'(?P<fi_id>[^/.]+)/pending-applications',
    PendingFinancialInstitutionApplicationViewSet,
    basename='financial_institution_pending_applications'
)
router.register(
    r'(?P<fi_id>[^/.]+)/application-actions',
    FIApplicationActionsViewSet,
    basename='financial_institution_application_actions'
)

router.register(
    r'(?P<fi_id>[^/.]+)/permissions',
    FIPermissionViewSet,
    basename='financial_institution_permissions'
)
router.register(
    r'(?P<fi_id>[^/.]+)/group-membership-actions',
    FIGroupMembershipActionsViewSet,
    basename='fi-group-membership-actions'
)
router.register(
    r'(?P<fi_id>[^/.]+)/groups',
    FICustomGroupViewSet,
    basename='financial_institution_groups'
)
router.register(
    r'(?P<fi_id>[^/.]+)/memberships',
    FIUserGroupMembershipViewSet,
    basename='fi-user-group-memberships'
)

urlpatterns = [
    path('', include(router.urls)),
    
    # ===================================================
    # DASHBOARD STATS
    # ===================================================
    path('<int:fi_id>/dashboard-stats/', RetrieveDashboardStatsView.as_view(), name='dashboard-stats'),
]
