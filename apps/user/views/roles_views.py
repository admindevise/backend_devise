from apps.user.models import Role
from django.db.models import Q
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from apps.utils.permissions import CustomDjangoModelPermission
from django.views.generic import View, ListView, CreateView, DetailView, UpdateView

from rest_framework.decorators import permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated 

from ..serializers.role_serializer import RoleSerializer


# =============================================================================
#                           APIREST USER RESOURCE
# =============================================================================
@permission_classes([IsAuthenticated])
class RoleApiListView(ListAPIView):
    serializer_class = RoleSerializer
    queryset = Role.objects.all()
    pagination_class = None

    # def get_queryset(self):
    #     if self.request.user.groups.filter(name='SUPERADMINISTRADOR').exists():
    #         queryset = Role.objects.all()
    #     else:
    #         queryset = Role.objects.all().exclude(name='COLABORADOR')
    #     return queryset

# =============================================================================
#                           BACKOFFICE RESOURCE
# =============================================================================@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class RoleListView(ListView):
    template_name = 'user/role/role_list.html'
    url_name = 'role-list'
    model = Role
    paginate_by = 25

    def get_queryset(self):
        filter_list = self.request.GET.getlist('filter')
        filters = Q()
        if ( filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'name__icontains',
                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})

        queryset = Role.objects.filter(filters).order_by('name')

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
        if ( filter_list and filter_list != ''):
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
        context['nav_roles'] = True

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
class RoleAddView(SuccessMessageMixin, CreateView):
    template_name = 'user/role/role_create.html'
    url_name = 'role-add'
    model = Role
    fields = [ 'name', 'groups' ]
    success_message =  _('Successful Creation!')

    def form_valid(self, form):
        object = form.save()
        
        id_group = self.request.POST.get('group')

        if not (id_group == '' or id_group == None):
            group_selected = Group.objects.get(pk=id_group)
            object.groups.add(group_selected)

        object.save()
        return super().form_valid(form)

    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("role-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id_group = self.request.POST.get('group')
        if not (id_group == '' or id_group == None):
            group_selected = Group.objects.get(pk=id_group)
            context['group_selected'] = group_selected
        context['groups'] = Group.objects.all()
        context['nav_roles'] = True
        
        return context

# =============================================================================
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class RoleDetailView(DetailView):
    template_name = 'user/role/role_detail.html'
    url_name = 'role-detail'
    model = Role

# =============================================================================
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class RoleUpdateView(SuccessMessageMixin, UpdateView):
    template_name = 'user/role/role_update.html'
    url_name = 'role-update'
    model = Role
    fields = [ 'name', 'groups' ]
    success_message =  _('Successful Update!')

    def form_valid(self, form):
        object = form.save()
        id_group = self.request.POST.get('group')

        if not (id_group == '' or id_group == None):
            object.groups.clear()
            group_selected = Group.objects.get(pk=id_group)
            object.groups.add(group_selected)

        object.save()
        return super().form_valid(form)

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("role-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['group_selected'] = self.object.groups.all()[0]
        except:
            context['group_selected'] = ''
        context['groups'] = Group.objects.all()
        context['nav_roles'] = True
        return context

# =============================================================================
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.delete_role', raise_exception=True), name='dispatch')
class RoleDeleteView(View):
    url_name = 'role-delete'

    def post(self, request,):
        role = get_object_or_404(Role, pk=self.request.POST['pk'])
        try:
            role.delete()
            response = {
                    'status': 'success',
                    'title': _('Successful removal!'),
                    'message': _('Role has been deleted!')
                }
        except:
            response = {
                    'status': 'error',
                    'title': _('Failed Delete!'),
                    'message': _('This item is in use, cannot be deleted!')
                }
        return JsonResponse(response)

