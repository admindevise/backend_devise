#from apps.asset.models import ActivoInversion
from apps.user.models import Role

from django.contrib.auth.models import Group, Permission
from django.contrib.auth.decorators import login_required, permission_required
from django.db import models 

from django.db.models import Q

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import View, ListView, CreateView, DetailView, UpdateView


from rest_framework.decorators import permission_classes
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from ..serializers.subrole_serializer import SubroleSerializer, SubroleSerializerBackoffice


# =============================================================================
#                               API VIEWS
# =============================================================================

class SubroleViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar Suboles (Grupos).
    """
    queryset = Group.objects.all()
    serializer_class = SubroleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name']
    ordering_fields = ['name', 'id']
    ordering = ['name']

    # Listas de exclusión definidas una sola vez como atributos de clase
    _excluded_apps = [
        'admin', 
        'auth', 
        'contenttypes', 
        'sessions', 
        'messages',
        'staticfiles',
        'sites',
        'flatpages',
        'cities_light',
        'druo',
        'weetrust',
        'authtoken',
    ]
    
    _excluded_models = [
        'logentry',
        'permission',
        'contenttype',
        'session',
        'appcontract',
        'compilecontract',
        'promotecontract',
        'wallet',
        'passwordreset',
        'walletsmartcontract',
    ]

    def get_queryset(self):
        """
        Permite filtrar subroles por rol si se especifica role_id en los parámetros
        """
        queryset = Group.objects.all()
        
        # Filtrar por rol si se proporciona role_id
        role_id = self.request.query_params.get('role_id')
        if role_id:
            try:
                role = Role.objects.get(pk=role_id)
                queryset = role.groups.all()
            except Role.DoesNotExist:
                queryset = Group.objects.none()
                
        return queryset

    def _get_filtered_permissions_queryset(self, request):
        """
        Método privado para obtener un queryset de permisos filtrado según los parámetros
        y excluyendo apps y modelos específicos.
        """
        # Iniciar con todos los permisos
        queryset = Permission.objects.all()
        
        # Aplicar exclusiones
        queryset = queryset.exclude(content_type__app_label__in=self._excluded_apps)
        queryset = queryset.exclude(content_type__model__in=self._excluded_models)
        
        # Filtrar por app_label si se proporciona
        app_label = request.query_params.get('app_label')
        if app_label:
            queryset = queryset.filter(content_type__app_label=app_label)
        
        # Filtrar por modelo si se proporciona
        model = request.query_params.get('model')
        if model:
            queryset = queryset.filter(content_type__model=model)
        
        # Filtrar por codename si se proporciona
        codename_contains = request.query_params.get('codename__contains')
        if codename_contains:
            queryset = queryset.filter(codename__contains=codename_contains)
        
        # Ordenar el resultado
        return queryset.order_by('content_type__app_label', 'content_type__model', 'codename')

    def _check_excluded_permissions(self, permission_ids):
        """
        Método privado para verificar si alguno de los permisos está en las listas de exclusión.
        Retorna una lista de IDs excluidos si existen, o una lista vacía si todos son válidos.
        """
        excluded_permissions = Permission.objects.filter(
            models.Q(content_type__app_label__in=self._excluded_apps) | 
            models.Q(content_type__model__in=self._excluded_models),
            id__in=permission_ids
        )
        
        return list(excluded_permissions.values_list('id', flat=True))

    @action(detail=False, methods=['get'])
    def available_permissions(self, request):
        """
        Obtiene los permisos disponibles en el sistema, excluyendo permisos por defecto de Django
        """
        queryset = self._get_filtered_permissions_queryset(request)
        
        # Formatear la respuesta para que sea más útil
        formatted_permissions = []
        for permission in queryset:
            formatted_permissions.append({
                'id': permission.id,
                'name': permission.name,
                'codename': permission.codename,
                'content_type': {
                    'id': permission.content_type.id,
                    'app_label': permission.content_type.app_label,
                    'model': permission.content_type.model
                }
            })
        
        return Response(formatted_permissions)

    @action(detail=True, methods=['post'])
    def assign_permissions(self, request, pk=None):
        """
        Asigna permisos a un subrol específico
        """
        subrole = self.get_object()
        permission_ids = request.data.get('permission_ids')
        
        # Validar que permission_ids existe y no está vacío
        if not permission_ids:
            return Response({
                'status': 'error',
                'message': 'El campo permission_ids es obligatorio y no puede estar vacío'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que permission_ids es una lista
        if not isinstance(permission_ids, list):
            return Response({
                'status': 'error',
                'message': 'El campo permission_ids debe ser una lista de IDs'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verificar si algún ID pertenece a permisos excluidos
            excluded_ids = self._check_excluded_permissions(permission_ids)
            
            if excluded_ids:
                return Response({
                    'status': 'error',
                    'message': f'No se pueden asignar los siguientes permisos porque están en listas de exclusión: {excluded_ids}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Consultar los permisos válidos
            permissions = Permission.objects.filter(id__in=permission_ids)
            
            # Validar que se encontraron todos los permisos
            if len(permissions) != len(permission_ids):
                found_ids = [p.id for p in permissions]
                missing_ids = [pid for pid in permission_ids if pid not in found_ids]
                
                return Response({
                    'status': 'error',
                    'message': f'No se encontraron los siguientes permisos: {missing_ids}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Asignar los permisos al subrol
            subrole.permissions.set(permissions)
            
            return Response({
                'status': 'success',
                'message': f'Permisos asignados correctamente al subrol {subrole.name}',
                'permissions_count': len(permissions)
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
@permission_classes([])
class SubRoleApiListView(ListAPIView):
    serializer_class = SubroleSerializerBackoffice
    queryset = Group.objects.all()
    pagination_class = None

    def get_queryset(self):
        groups = Role.objects.get(pk=self.kwargs.get('role_id')).groups.all()
        return groups


@permission_classes([IsAuthenticated])
class SubRolePermissionsApiListView(RetrieveAPIView):
    queryset = Group.objects.all()
    serializer_class = SubroleSerializer

# =============================================================================
#                               TEMPLATE VIEWS
# =============================================================================


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class SubroleListView(ListView):
    template_name = 'user/subrole/subrole_list.html'
    url_name = 'subrole-list'
    model = Group
    paginate_by = 25

    def get_queryset(self):
        filter_list = self.request.GET.getlist('filter')
        filters = Q()
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'name__icontains',
                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})

        queryset = Group.objects.filter(filters).order_by('name')

        filter_verified = self.request.GET.get('verified')
        if not (filter_verified == '' or filter_verified == None):
            if (filter_verified == '0'):
                queryset = queryset.filter(status=False)

            elif (filter_verified == '1'):
                queryset = queryset.filter(status=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_obj = {
            'value': [],
            'url': ''
        }

        filter_list = self.request.GET.getlist('filter')
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                filter_obj['value'].append(
                    filter
                )
                filter_obj['url'] += '&filter={}'.format(filter)

        filter_verified = self.request.GET.get('verified')
        if not (filter_verified == '' or filter_verified == None):
            filter_obj['filter_verified'] = filter_verified
            filter_obj['url'] += '&verified={}'.format(filter_verified)
        context['filter_verified'] = filter_verified
        context['filter_obj'] = filter_obj
        context['nav_subroles'] = True

        paginator = context.get('paginator')
        num_pages = paginator.num_pages
        current_page = context.get('page_obj')
        page_no = current_page.number

        if num_pages <= 11 or page_no <= 6:  # case 1 and 2
            pages = [x for x in range(1, min(num_pages + 1, 12))]
        elif page_no > num_pages - 6:  # case 4
            pages = [x for x in range(num_pages - 10, num_pages + 1)]
        else:  # case 3
            pages = [x for x in range(page_no - 5, page_no + 6)]

        context.update({'pages': pages})
        return context

# =============================================================================


""" @method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.add_user', raise_exception=True), name='dispatch')
class SubroleCreateView(SuccessMessageMixin, CreateView):
    template_name = 'user/subrole/subrole_create.html'
    url_name = 'subrole-create'
    model = Group
    fields = ['name', 'permissions']
    success_message = _('Successful Creation!')

    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("subrole-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permissions = Permission.objects.none()
        models = [
                MenuPermissions, SponsorCompany, ActivoInversion, User, Fiducia, Notaria
                ]
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            permissions |= Permission.objects.filter(content_type=content_type)
        context['permissions'] = permissions
        context['nav_subroles'] = True
        return context """

# =============================================================================


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class SubroleDetailView(DetailView):
    template_name = 'user/subrole/subrole_detail.html'
    url_name = 'subrole-detail'
    model = Group

# =============================================================================


""" @method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class SubroleUpdateView(SuccessMessageMixin, UpdateView):
    template_name = 'user/subrole/subrole_update.html'
    url_name = 'subrole-update'
    model = Group
    fields = ['name', 'permissions']
    success_message = _('Successful Update!')

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("subrole-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = Group.objects.get(pk=self.kwargs["pk"])
        permissions = Permission.objects.none()
        models = [
                MenuPermissions, SponsorCompany, ActivoInversion, User, Fiducia, Notaria
                ]
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            permissions |= Permission.objects.filter(content_type=content_type)
        context['permissions'] = permissions
        context['asigned_permissions'] = group.permissions.all()
        context['nav_subroles'] = True
        return context """
