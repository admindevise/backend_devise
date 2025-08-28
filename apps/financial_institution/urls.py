from rest_framework.routers import DefaultRouter
from django.urls import path, include

from apps.financial_institution.views.core_views import (
    FinancialInstitutionViewSet,
    create_application,
    approve_application,
    reject_application,
)
from apps.financial_institution.views.utils_views import (
    MembersFinancialInstitutionViewSet,
    FinancialInstitutionApplicationViewSet,
    PendingFinancialInstitutionApplicationViewSet,
)

router = DefaultRouter()
router.register(r'institutions', FinancialInstitutionViewSet, basename='financial_institution')
router.register(r'list-applications', FinancialInstitutionApplicationViewSet, basename='financial_institution_application')
router.register(r'members', MembersFinancialInstitutionViewSet, basename='members_financial_institution')
router.register(r'pending-applications', PendingFinancialInstitutionApplicationViewSet, basename='pending_financial_institution_application')

urlpatterns = [
    path('api/', include(router.urls)),
    
    # =============================
    # Application Processing Endpoints
    # =============================
    path('api/create-application/', create_application, name='financial_institution_approval'),
    path('api/applications/<int:application_id>/approve/', approve_application, name='financial_institution_approve'),
    path('api/applications/<int:application_id>/reject/', reject_application, name='financial_institution_reject')
]
