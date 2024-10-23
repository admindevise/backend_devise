from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, JsonResponse
from django.contrib.messages.views import SuccessMessageMixin

from django.db.models import Q
from django.views.generic import View, ListView, UpdateView
from apps.security.models import SecurityConfiguration
from apps.user.models import User
from django.utils.translation import ugettext as _


# Create your views here.
method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.is_staff', raise_exception=True), name='dispatch')
class UserLockedListView(ListView):
    template_name = 'user_security/userlist.html'
    url_name = 'user-locked-list'
    model = User
    paginate_by = 25

    def get_queryset(self):
        filter_list = self.request.GET.getlist('filter')
        filters = Q()
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'email__icontains',
                    'phone__icontains',
                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})
        queryset = User.objects.filter(failed_attempts__gte= 3)
        queryset = queryset.filter(filters).order_by('email')
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
        context['nav_list_fail_users'] = True

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
    
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.is_staff', raise_exception=True), name='dispatch')
class UnlockAttemptsView(View):
    url_name = 'user-unlock-access'

    def post(self, request,):
        user = get_object_or_404(User, pk=self.request.POST['pk'])
        user.failed_attempts=0
        user.save()
        title = _('Reinicio exitoso')
        message = _('Han sido restaurados los intentos')
        response = {
            'is_active': 'success',
            'title': title,
            'message': message
        }

        return JsonResponse(response)
    
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.is_staff', raise_exception=True), name='dispatch')
class ConfigRulesSecurityView(SuccessMessageMixin, UpdateView):
    template_name = 'params/params.html'
    url_name = 'params-detail'
    model = SecurityConfiguration
    fields = ['max_failed_login_attempts',
            'login_lockout_duration',
            'password_expiry_days',
            'password_max_delta_change',
            ]
    success_message = 'Configuración de seguridad actualizada!'
    
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("params-detail", kwargs={"pk": pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_config_security'] = True
        return context