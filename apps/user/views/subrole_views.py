from apps.asset.models import ActivoInversion
from apps.fiducia.models import Fiducia
from apps.notaria.models import Notaria
from apps.sponsor_company.models import SponsorCompany
from apps.user.models import Role
from apps.menu.models import  MenuPermissions

from django.contrib.auth.models import Group, Permission
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages.views import SuccessMessageMixin

from django.contrib.contenttypes.models import ContentType

from django.db.models import Q
from django.urls import reverse_lazy

from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import View, ListView, CreateView, DetailView, UpdateView

from apps.user.models import User

from rest_framework.decorators import permission_classes
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from ..serializers.subrole_serializer import SubroleSerializer, SubroleSerializerBackoffice


# =============================================================================
#                               API VIEWS
# =============================================================================
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


@method_decorator(login_required, name='dispatch')
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
        return context

# =============================================================================


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class SubroleDetailView(DetailView):
    template_name = 'user/subrole/subrole_detail.html'
    url_name = 'subrole-detail'
    model = Group

# =============================================================================


@method_decorator(login_required, name='dispatch')
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
        return context
