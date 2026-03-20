from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.audit.views import AuditLogViewSet, AuditActionViewSet, AuditCategoryViewSet

router = DefaultRouter()
router.register(
    r'fi/(?P<fi_id>[^/.]+)/logs',
    AuditLogViewSet,
    basename='logs'
)
router.register(
    r'fi/(?P<fi_id>[^/.]+)/actions',
    AuditActionViewSet,
    basename='audit-actions'
)
router.register(
    r'fi/(?P<fi_id>[^/.]+)/categories',
    AuditCategoryViewSet,
    basename='audit-categories'
)

urlpatterns = [
    path('', include(router.urls)),
]