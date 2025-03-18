from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.audit.views import AuditLogViewSet, AuditActionViewSet, AuditCategoryViewSet

router = DefaultRouter()
router.register(r'logs', AuditLogViewSet, basename='audit-logs')
router.register(r'actions', AuditActionViewSet, basename='audit-actions')
router.register(r'categories', AuditCategoryViewSet, basename='audit-categories')

urlpatterns = [
    path('api/', include(router.urls)),
]