from django.urls import  path, include
from rest_framework.routers import DefaultRouter

from apps.academy.views import CategoriesViewSet, ArticlesViewSet

router = DefaultRouter()
router.register(
    r'fi/(?P<fi_id>[^/.]+)/categories',
    CategoriesViewSet,
    basename='category'
)
router.register(
    r'fi/(?P<fi_id>[^/.]+)/articles',
    ArticlesViewSet,
    basename='article'
)

urlpatterns = [
    path('', include(router.urls)),
]