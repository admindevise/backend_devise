
from django.urls import  path, include
from rest_framework.routers import DefaultRouter

from apps.academia.views.categoria_views import CategoriaViewSet, CategoriaDeactivateView, CategoriaCreateView, CategoriaDeleteView, CategoriaDetailView, CategoriaListView, CategoriaUpdateView
from apps.academia.views.articulo_views import ArticuloViewSet, ArticuloDeactivateView, ArticuloCreateView, ArticuloDeleteView, ArticuloDetailView, ArticuloListView, ArticuloUpdateView

router = DefaultRouter()
router.register(r'categoria/api', CategoriaViewSet, basename='categoria')
router.register(r'articulo/api', ArticuloViewSet, basename='articulo')

urlpatterns = [
    path('', include(router.urls)),
   
    #============================= Backoffice Views Categoria =================================
    path('categoria/create/', CategoriaCreateView.as_view(), name=CategoriaCreateView.url_name),
    path('categoria/list/', CategoriaListView.as_view(), name=CategoriaListView.url_name),
    path('categoria/<int:pk>/update/', CategoriaUpdateView.as_view(), name=CategoriaUpdateView.url_name),
    path('categoria/<int:pk>/detail/', CategoriaDetailView.as_view(), name=CategoriaDetailView.url_name),
    path('categoria/delete/', CategoriaDeleteView.as_view(), name=CategoriaDeleteView.url_name),
    path('categoria/deactivate/', CategoriaDeactivateView.as_view(), name='academia-categoria-deactivate'),

    #============================= Backoffice Views Articulo =================================
    path('articulo/create/', ArticuloCreateView.as_view(), name=ArticuloCreateView.url_name),
    path('articulo/list/', ArticuloListView.as_view(), name=ArticuloListView.url_name),
    path('articulo/<int:pk>/update/', ArticuloUpdateView.as_view(), name=ArticuloUpdateView.url_name),
    path('articulo/<int:pk>/detail/', ArticuloDetailView.as_view(), name=ArticuloDetailView.url_name),
    path('articulo/delete/', ArticuloDeleteView.as_view(), name=ArticuloDeleteView.url_name),
    path('articulo/deactivate/', ArticuloDeactivateView.as_view(), name='academia-articulo-deactivate'),
]