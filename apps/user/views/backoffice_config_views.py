
from ..models import IdType
from apps.druo.models import AccountType, AccountSubtype, Bank
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic import View, ListView, CreateView, DetailView, UpdateView, DeleteView


# =============================================================================
#                           BACKOFFICE VIEWS RESOURCE
# =============================================================================

@method_decorator(login_required, name='dispatch')
class IdTypeCreateView(CreateView):
    template_name = 'backoffice_config/idtype/create.html'
    model = IdType
    fields = ('value', 'name', 'description')
    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("idtype-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_idtype_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class IdTypeListView(ListView):
    model = IdType
    template_name ='backoffice_config/idtype/list.html'
    paginate_by = 20
    def get_queryset(self):
        filters = Q()
        filter_list = self.request.GET.getlist('filter')
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'value__icontains',
                    'name__icontains',
                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})
        queryset = IdType.objects.filter(filters)

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            if (filter_status == '0'):
                queryset = queryset.filter(status=False)

            elif (filter_status == '1'):
                queryset = queryset.filter(status=True)

        return queryset.order_by('name')

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

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            filter_obj['filter_status'] = filter_status
            filter_obj['url'] += '&verified={}'.format(filter_status)
        context['filter_status'] = filter_status
        context['filter_obj'] = filter_obj
        context['nav_idtype_list'] = True

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
class IdTypeDetailView(DetailView):
    template_name = 'backoffice_config/idtype/detail.html'
    model = IdType
    fields = ('value', 'name', 'description')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_idtype_list'] = True
        return context


@method_decorator(login_required, name='dispatch')
class IdTypeUpdateView(UpdateView):
    template_name = 'backoffice_config/idtype/update.html'
    url_name = 'idtype-update'
    model = IdType
    fields = ('value', 'name', 'description')
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("idtype-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_idtype_list'] = True
        return context


@method_decorator(login_required, name='dispatch')
class IdTypeDeleteView(DeleteView):
    def post(self, request,):
        user = get_object_or_404(IdType, pk=self.request.POST['pk'])
        try:
            user.delete()
            response = {
                'status': 'success',
                'title': _('Eliminacion exitosa!'),
                'message': _('El Tipo Id a sido borrado')
            }
        except:
            response = {
                'status': 'error',
                'title': _('Fallo al intentar eliminar el elemento!'),
                'message': _('El elemento posee historicos en base de datos no puede ser eliminado')
            }
        return JsonResponse(response)

@method_decorator(login_required, name='dispatch')
class IdtypeDeactivateView(View):

    def post(self, request,):
        idtype = get_object_or_404(IdType, pk=self.request.POST['pk'])
        if (idtype.status):
            idtype.status = False
            title = 'Desactivación exitosa'
            message = 'El tipo de documento ha sido deshabilitado'
            idtype.save()
        else:
            idtype.status = True
            title = 'Activación Exitosa'
            message = 'El tipo de documento a sido habilitado exitosamente'
            idtype.save()

        response = {
            'changed': 'success',
            'title': title,
            'message': message
        }

        return JsonResponse(response)

# ================      bank  AccountType       =============================================

@method_decorator(login_required, name='dispatch')
class AccountTypeCreateView(CreateView):
    template_name = 'backoffice_config/accounttype/create.html'
    model = AccountType
    fields = ('value', 'name', 'description')
    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("accounttype-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_accounttype_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class AccountTypeListView(ListView):
    model = AccountType
    template_name ='backoffice_config/accounttype/list.html'
    paginate_by = 20
    def get_queryset(self):
        filters = Q()
        filter_list = self.request.GET.getlist('filter')
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'value__icontains',
                    'name__icontains',
                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})
        queryset = AccountType.objects.filter(filters)

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            if (filter_status == '0'):
                queryset = queryset.filter(status=False)

            elif (filter_status == '1'):
                queryset = queryset.filter(status=True)

        return queryset.order_by('name')

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

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            filter_obj['filter_status'] = filter_status
            filter_obj['url'] += '&verified={}'.format(filter_status)
        context['filter_status'] = filter_status
        context['filter_obj'] = filter_obj
        context['nav_accounttype_list'] = True

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
class AccountTypeDetailView(DetailView):
    template_name = 'backoffice_config/accounttype/detail.html'
    model = AccountType
    fields = ('value', 'name', 'description')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_accounttype_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class AccountTypeUpdateView(UpdateView):
    template_name = 'backoffice_config/accounttype/update.html'
    url_name = 'accounttype-update'
    model = AccountType
    fields = ('value', 'name', 'description')
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("accounttype-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_accounttype_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class AccountTypeDeleteView(DeleteView):
    def post(self, request,):
        user = get_object_or_404(AccountType, pk=self.request.POST['pk'])
        try:
            user.delete()
            response = {
                'status': 'success',
                'title': _('Eliminacion exitosa!'),
                'message': _('El tipo Cta Bancaria a sido borrado')
            }
        except:
            response = {
                'status': 'error',
                'title': _('Fallo al intentar eliminar el elemento!'),
                'message': _('El elemento posee historicos en base de datos no puede ser eliminado')
            }
        return JsonResponse(response)

@method_decorator(login_required, name='dispatch')
class AccountTypeDeactivateView(View):

    def post(self, request,):
        accounttype = get_object_or_404(AccountType, pk=self.request.POST['pk'])
        if (accounttype.status):
            accounttype.status = False
            title = 'Desactivación exitosa'
            message = 'El tipo de Cta Bancaria ha sido deshabilitado'
            accounttype.save()
        else:
            accounttype.status = True
            title = 'Activación Exitosa'
            message = 'El tipo de Cta Bancaria a sido habilitado exitosamente'
            accounttype.save()

        response = {
            'changed': 'success',
            'title': title,
            'message': message
        }

        return JsonResponse(response)

# ================      bank  SubAccountType       =============================================

@method_decorator(login_required, name='dispatch')
class AccountSubtypeCreateView(CreateView):
    template_name = 'backoffice_config/accountsubtype/create.html'
    model = AccountSubtype
    fields = ('value', 'name', 'description')
    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("accountsubtype-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_accountsubtype_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class AccountSubtypeListView(ListView):
    model = AccountSubtype
    template_name ='backoffice_config/accountsubtype/list.html'
    paginate_by = 20
    def get_queryset(self):
        filters = Q()
        filter_list = self.request.GET.getlist('filter')
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'value__icontains',
                    'name__icontains',
                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})
        queryset = AccountSubtype.objects.filter(filters)

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            if (filter_status == '0'):
                queryset = queryset.filter(status=False)

            elif (filter_status == '1'):
                queryset = queryset.filter(status=True)

        return queryset.order_by('name')

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

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            filter_obj['filter_status'] = filter_status
            filter_obj['url'] += '&verified={}'.format(filter_status)
        context['filter_status'] = filter_status
        context['filter_obj'] = filter_obj
        context['nav_accountsubtype_list'] = True

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
class AccountSubtypeDetailView(DetailView):
    template_name = 'backoffice_config/accountsubtype/detail.html'
    model = AccountSubtype
    fields = ('value', 'name', 'description')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_accountsubtype_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class AccountSubtypeUpdateView(UpdateView):
    template_name = 'backoffice_config/accountsubtype/update.html'
    url_name = 'accountsubtype-update'
    model = AccountSubtype
    fields = ('value', 'name', 'description')
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("accountsubtype-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_accountsubtype_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class AccountSubtypeDeleteView(DeleteView):
    def post(self, request,):
        user = get_object_or_404(AccountSubtype, pk=self.request.POST['pk'])
        try:
            user.delete()
            response = {
                'status': 'success',
                'title': _('Eliminacion exitosa!'),
                'message': _('El tipo Subcuenta Bancaria a sido borrado')
            }
        except:
            response = {
                'status': 'error',
                'title': _('Fallo al intentar eliminar el elemento!'),
                'message': _('El elemento posee historicos en base de datos no puede ser eliminado')
            }
        return JsonResponse(response)

@method_decorator(login_required, name='dispatch')
class AccountSubtypeDeactivateView(View):

    def post(self, request,):
        accountsubtype = get_object_or_404(AccountSubtype, pk=self.request.POST['pk'])
        if (accountsubtype.status):
            accountsubtype.status = False
            title = 'Desactivación exitosa'
            message = 'El tipo de Subcuenta Bancaria ha sido deshabilitado'
            accountsubtype.save()
        else:
            accountsubtype.status = True
            title = 'Activación Exitosa'
            message = 'El tipo de Subcuenta Bancaria a sido habilitado exitosamente'
            accountsubtype.save()

        response = {
            'changed': 'success',
            'title': title,
            'message': message
        }

        return JsonResponse(response)

# ================      Bank Configuration       =============================================

@method_decorator(login_required, name='dispatch')
class BankCreateView(CreateView):
    template_name = 'backoffice_config/bank/create.html'
    model = Bank
    fields = ( 'institution_name',  'uuid',  'country',  'network', )
    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("bank-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_bank_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class BankListView(ListView):
    model = Bank
    template_name ='backoffice_config/bank/list.html'
    paginate_by = 20
    def get_queryset(self):
        filters = Q()
        filter_list = self.request.GET.getlist('filter')
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'uuid__icontains',
                    'institution_name__icontains',
                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})
        queryset = Bank.objects.filter(filters)

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            if (filter_status == '0'):
                queryset = queryset.filter(status=False)

            elif (filter_status == '1'):
                queryset = queryset.filter(status=True)

        return queryset.order_by('institution_name')

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

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            filter_obj['filter_status'] = filter_status
            filter_obj['url'] += '&verified={}'.format(filter_status)
        context['filter_status'] = filter_status
        context['filter_obj'] = filter_obj
        context['nav_bank_list'] = True

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
class BankDetailView(DetailView):
    template_name = 'backoffice_config/bank/detail.html'
    model = Bank
    fields = ('value', 'name', 'description')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_bank_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class BankUpdateView(UpdateView):
    template_name = 'backoffice_config/bank/update.html'
    url_name = 'bank-update'
    model = Bank
    fields = ('value', 'name', 'description')
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("bank-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_bank_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
class BankDeleteView(DeleteView):
    def post(self, request,):
        user = get_object_or_404(Bank, pk=self.request.POST['pk'])
        try:
            user.delete()
            response = {
                'status': 'success',
                'title': _('Eliminacion exitosa!'),
                'message': _('El Banco a sido borrado')
            }
        except:
            response = {
                'status': 'error',
                'title': _('Fallo al intentar eliminar el elemento!'),
                'message': _('El elemento posee historicos en base de datos no puede ser eliminado')
            }
        return JsonResponse(response)

@method_decorator(login_required, name='dispatch')
class BankDeactivateView(View):

    def post(self, request,):
        bank = get_object_or_404(Bank, pk=self.request.POST['pk'])
        if (bank.status):
            bank.status = False
            title = 'Desactivación exitosa'
            message = 'El Banco ha sido deshabilitado'
            bank.save()
        else:
            bank.status = True
            title = 'Activación Exitosa'
            message = 'El Banco a sido habilitado exitosamente'
            bank.save()

        response = {
            'changed': 'success',
            'title': title,
            'message': message
        }

        return JsonResponse(response)

