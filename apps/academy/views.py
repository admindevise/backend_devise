from django.utils.translation import gettext_lazy as _

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.academy.serializers import CategorySerializer, Articleserializer
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.utils.views.global_utils_views import validate_entity_exists
from apps.financial_institution.models.core import FinancialInstitution
from apps.academy.models import Articles, Category

class CategoriesViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Categoria que provee automáticamente las acciones:
    `list`, `create`, `retrieve`, `update`, `partial_update` y `destroy`
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        if self.kwargs.get('pk'):
            validate_entity_exists(Category, 'Categoría', self.kwargs.get('pk'))
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)
    
    def get_queryset(self):
        return Category.objects.all().order_by('name')

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 5  # Establece el tamaño de la página
    page_size_query_param = 'page_size'  # Parámetro para ajustar el tamaño de la página desde la solicitud
    max_page_size = 100  # Establece el tamaño máximo de la página

    def get_page_range(self, start, end):
        # Personaliza el rango de páginas disponibles, por ejemplo, limitándolo de 1 a 10
        return range(max(start, 1), min(end, 11))

class ArticlesViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Articulo que provee automáticamente las acciones CRUD:
    `list`, `create`, `retrieve`, `update`, `partial_update` y `destroy`
    
    Incluye capacidades de filtrado, búsqueda y ordenamiento.
    """
    queryset = Articles.objects.all()
    serializer_class = Articleserializer
    permission_classes = [IsAuthenticated, RegistryPermission]
    pagination_class = CustomPageNumberPagination
    
    # Configuración de filtrado y búsqueda
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'status']  # Campos para filtrado exacto
    search_fields = ['title', 'content']     # Campos para búsqueda de texto
    ordering_fields = ['title', 'date']       # Campos para ordenamiento
    ordering = ['title']                       # Ordenamiento predeterminado
    
    def initial(self, request, *args, **kwargs):
        if self.kwargs.get('pk'):
            validate_entity_exists(Articles, 'Artículo', self.kwargs.get('pk'))
        validate_entity_exists(FinancialInstitution, 'Institución financiera', self.kwargs.get('fi_id'))
        super().initial(request, *args, **kwargs)
    