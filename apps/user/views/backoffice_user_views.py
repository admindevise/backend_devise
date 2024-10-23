from django.contrib.auth.models import Permission
from apps.user.models import User, Role, PasswordReset
from apps.info_residential.models import Residentialplace
from apps.info_workplace.models import Workplace
from apps.sponsor_company.models import SponsorCompany
from apps.info_socioeconomic.models import Socioeconomic
from apps.kaleido.models import Wallet

from apps.info_financial.models import Financial
# from apps.utils.permissions import CustomDjangoModelPermission
from cities_light.models import Country, Region, SubRegion

from django.conf import settings
from django.db.models import Q
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import View, ListView, CreateView, DetailView, UpdateView

from ..forms.financial_form import FinancialForm, UpdateFinancialForm
from ..forms.residential_form import ResidentialForm, UpdateResidentialForm
from ..forms.user_form import UserBasicInfoForm, UserDocumentInfoForm
from ..forms.workplace_form import WorkplaceForm, UpdateWorkplaceForm
from ..forms.socioeconomic_form import UpdateSocioeconomicForm, SocioeconomicForm

from django.template.loader import get_template

from io import BytesIO
from xhtml2pdf import pisa
from import_export import fields, resources, widgets
import datetime as dt

from django.contrib.auth.password_validation import validate_password

# =============================================================================
#                           IMPORT - EXPORT RESOURCE
# =============================================================================
class UserResource(resources.ModelResource):
    
    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name',
            'username',
            'local_id_type',
            'document_number',
            'role',
            'kyc_validated',
        )
        export_order = (
            'email',
            'first_name',
            'last_name',
            'username',
            'first_name',
            'last_name',
            'role',
        )

# =============================================================================
#                           BACKOFFICE RESOURCE
# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class UserListView(ListView):
    template_name = 'user/user_list.html'
    url_name = 'user-list'
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

        queryset = User.objects.filter(filters).order_by('email')

        filter_verified = self.request.GET.get('verified')
        if not (filter_verified == '' or filter_verified == None):
            if (filter_verified == '0'):
                queryset = queryset.filter(is_active=False)

            elif (filter_verified == '1'):
                queryset = queryset.filter(is_active=True)

        filter_subrol = self.request.GET.get('subrol')
        if not (filter_subrol == '' or filter_subrol == None):
            grupo = Group.objects.get(id=filter_subrol)
            queryset = queryset.filter(groups=grupo)

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
        context['nav_users_login'] = True

        filter_subrol = self.request.GET.get('subrol')
        if not (filter_subrol == '' or filter_subrol == None):
            filter_obj['filter_subrol'] = int(filter_subrol)
            filter_obj['url'] += '&subrol={}'.format(filter_subrol)
        context['subroles'] = Group.objects.all()

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
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class UserListExportView(View):
    url_name = 'user-list-export'

    def _get_pdf_export(self, queryset, file_name):
        template = get_template('report/user_list_export.html')
        context = {
            'user_report': self.request.user,
            'object_list': queryset,
            'current_scheme_host': self.request._current_scheme_host,
        }
        html  = template.render(context)
        result = BytesIO()

        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, debug=1)

        return result

    def _get_export_response(self, queryset, format='csv'):
        dataset = UserResource().export(queryset)
        file_name = "users_{}".format(dt.datetime.now().strftime("%d-%m-%Y"))

        if (format == 'csv'):
            dataset_format = dataset.csv
            CONTENT_DISPOSITION = 'attachment; filename="{}.csv"'.format(file_name)
            CONTENT_TYPE = 'text/csv'

        elif (format == 'xls'):
            dataset_format = dataset.xls
            CONTENT_DISPOSITION = 'attachment; filename="{}.xls"'.format(file_name)
            CONTENT_TYPE = 'application/vnd.ms-excel'

        elif (format == 'xlsx'):
            dataset_format = dataset.xlsx
            CONTENT_DISPOSITION = 'attachment; filename="{}.xlsx"'.format(file_name)
            CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        elif (format == 'tsv'):
            dataset_format = dataset.tsv
            CONTENT_DISPOSITION = 'attachment; filename="{}.tsv"'.format(file_name)
            CONTENT_TYPE = 'text/tab-separated-values'

        elif (format == 'ods'):
            dataset_format = dataset.ods
            CONTENT_DISPOSITION = 'attachment; filename="{}.ods"'.format(file_name)
            CONTENT_TYPE = 'application/vnd.oasis.opendocument.spreadsheet'

        elif (format == 'json'):
            dataset_format = dataset.json
            CONTENT_DISPOSITION = 'attachment; filename="{}.json"'.format(file_name)
            CONTENT_TYPE = 'application/json'

        elif (format == 'yaml'):
            dataset_format = dataset.yaml
            CONTENT_DISPOSITION = 'attachment; filename="{}.yaml"'.format(file_name)
            CONTENT_TYPE = 'text/yaml'

        elif (format == 'html'):
            dataset_format = dataset.html
            CONTENT_DISPOSITION = 'attachment; filename="{}.html"'.format(file_name)
            CONTENT_TYPE = 'text/html'

        elif (format == 'pdf'):
            result = self._get_pdf_export(queryset, file_name)
            CONTENT_DISPOSITION = 'attachment; filename="{}.pdf"'.format(file_name)
            CONTENT_TYPE = 'application/pdf'

            response = HttpResponse(content_type=CONTENT_TYPE)
            response['Content-Disposition'] = CONTENT_DISPOSITION
            response.content = result.getvalue()
            return response

        else:
            dataset_format = dataset.csv
            CONTENT_DISPOSITION = 'attachment; filename="_{}.csv"'.format(file_name)
            CONTENT_TYPE = 'text/csv'

        response = HttpResponse(dataset_format, content_type=CONTENT_TYPE)
        response['Content-Disposition'] = CONTENT_DISPOSITION
        return response


    def post(self, request, *args, **kwargs):
        format_file_available = {
            '0': 'csv',
            '1': 'xls',
            '2': 'xlsx',
            '3': 'pdf',
            # '4': 'ods',
            # '5': 'json',
            # '6': 'yaml',
            # '7': 'html',
        }

        id_seleccion = request.POST.getlist('_action_selection')
        action = request.POST.get('_action')
        selected_all_elements = request.POST.get('selected-all-elements')
        format_file_id = request.POST.get('_format_file')
        try:
            format_file = format_file_available[format_file_id]
        except:
            format_file = format_file_available['0']

        if (selected_all_elements == '1' or selected_all_elements == 1):
            queryset = User.objects.all().order_by('username')
            filter_verified = request.POST.get('filter_verified')

            if not (filter_verified == '' or filter_verified == None):
                if (filter_verified == '0'):
                    queryset = queryset.filter(verified=False, rejected=False)

                elif (filter_verified == '1'):
                    queryset = queryset.filter(verified=True, rejected=False)

            filter_subrol = request.POST.get('subrol')
            if not (filter_subrol == '' or filter_subrol == None):
                grupo = Group.objects.get(id=filter_subrol)
                queryset = queryset.filter(groups=grupo)

            filter_list = request.POST.getlist('filter')
            filters = Q()
            if ( filter_list and filter_list != ''):
                for filter in filter_list:
                    fields = [
                        'email__icontains',
                        'phone__icontains',
                    ]

                    for str_field in fields:
                        filters |= Q(**{str_field: filter})

                queryset = queryset.filter(filters)

        else:
            if not (id_seleccion == '' or id_seleccion == None):
                queryset = User.objects.filter(id__in=id_seleccion).order_by('email')
            else:
                queryset = User.objects.none()

        response = self._get_export_response(queryset, format=format_file)

        return response


# =============================================================================
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.add_user', raise_exception=True), name='dispatch')
class UserCreateView(CreateView):
    template_name = 'user/user_create.html'
    url_name = 'user-add'
    model = User
    fields = [
        'email', 'phone', 'password', 'indicative',
        'referred_by_code', 'birth_country',
        'role',
        ]

    def form_valid(self, form):
        id_group = form.cleaned_data.get('group')
        password = form.cleaned_data.get('password')

        try:
            validate_password(password, self.object)
        except Exception as e:
            print("e: ",e)
            # La contraseña no cumple con las políticas de validación
            form.add_error('password', str(e))
            return self.form_invalid(form)
        
        if not (id_group == '' or id_group == None):
            group_selected = Group.objects.get(pk=id_group)
            object.groups.add(group_selected)

        object = form.save()
        object.set_password(password)
        object.save()
        return super().form_valid(form)

    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id_group = self.request.POST.get('group')
        if not (id_group == '' or id_group == None):
            group_selected = Group.objects.get(pk=id_group)
            context['group_selected'] = group_selected
        context['roles'] = Role.objects.all()
        context['nav_users_login'] = True
        context['countries'] = Country.objects.all()
        return context
    
# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class UserDetailView(DetailView):
    template_name = 'user/user_detail.html'
    url_name = 'user-detail'
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_users_login'] = True
        usuario = User.objects.get(id=self.kwargs['pk'])
        if Wallet.objects.filter(user=usuario).exists():
            context['wallet'] = Wallet.objects.get(user=usuario)
        else:
            context['wallet'] = None

        if Residentialplace.objects.filter(user=usuario).exists():
            context['residential'] = Residentialplace.objects.get(user=usuario)
        else:
            context['residential'] = None

        if Workplace.objects.filter(user=usuario).exists():
            context['workplace'] = Workplace.objects.get(user=usuario)
        elif usuario.groups.filter(name='INVERSIONISTA').exists():
            context['workplace'] = True
        else:
            context['workplace'] = None

        if SponsorCompany.objects.filter(user=usuario).exists():
            context['sponsorcompany'] = SponsorCompany.objects.get(user=usuario)
        else:
            context['sponsorcompany'] = None

        if Financial.objects.filter(user=usuario).exists():
            context['financial'] = Financial.objects.get(user=usuario)
        else:
            context['financial'] = None
        if Socioeconomic.objects.filter(user=usuario).exists():
            context['socioeconomic'] = Socioeconomic.objects.get(user=usuario)
        else:
            context['socioeconomic'] = None
        return context

# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.delete_user', raise_exception=True), name='dispatch')
class UserDeleteView(View):
    url_name = 'user-delete'

    def post(self, request,):
        user = get_object_or_404(User, pk=self.request.POST['pk'])
        try:
            user.delete()
            response = {
                'status': 'success',
                'title': _('Eliminacion exitosa!'),
                'message': _('El usuario a sido borrado')
            }
        except:
            response = {
                'status': 'error',
                'title': _('Fallo al intentar eliminar el elemento!'),
                'message': _('El elemento posee historicos en base de datos no puede ser eliminado')
            }
        return JsonResponse(response)

# =============================================================================


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserDeactivateView(View):
    url_name = 'user-deactivate'

    def post(self, request,):
        user = get_object_or_404(User, pk=self.request.POST['pk'])
        if (user.is_active):
            user.is_active = False
            title = _('Desactivación exitosa')
            message = _('El usuario ha sido deshabilitado')
            user.save()
        else:
            user.is_active = True
            title = _('Activación Exitosa')
            message = _('El usuario a sido habilitado exitosamente')
            user.save()

        response = {
            'is_active': 'success',
            'title': title,
            'message': message
        }

        return JsonResponse(response)


# =========================== UPDATE BASIC INFO USER  ===================================
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserBasicInfoUpdateView(SuccessMessageMixin, UpdateView):
    model = User
    template_name = 'user/user_basicinfo_update.html'
    url_name = 'user-basicinfo-update'
    form_class = UserBasicInfoForm
    success_message = 'Información personal actualizada!'


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
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            context['group_selected'] = self.object.groups.all()[0]
        except:
            context['group_selected'] = ''
        context['countries'] = Country.objects.all()
        context['regions'] = Region.objects.filter(country=self.object.birth_country)
        context['cities'] = SubRegion.objects.filter(
            country=self.object.birth_country, region=self.object.birth_region)
        context['groups'] = Group.objects.all()
        context['roles'] = Role.objects.all()
        context['nav_users_login'] = True
        return context

# =========================== UPDATE DOCUMENTAL INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserDocumentUpdateView(SuccessMessageMixin, UpdateView):
    model = User
    template_name = 'user/user_document_update.html'
    url_name = 'user-documentinfo-update'
    form_class = UserDocumentInfoForm
    success_message = 'Información documental actualizada!'

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries'] = Country.objects.all()
        context['regions'] = Region.objects.filter(country=self.object.doc_country_expedition)
        context['cities'] = SubRegion.objects.filter(
            country=self.object.doc_country_expedition, region=self.object.doc_region_expedition)
        context['nav_users_login'] = True
        return context

# =========================== CREATE RESIDENCIAL INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserResidentialCreateView(SuccessMessageMixin, CreateView):
    model = Residentialplace
    template_name = 'user/user_residential_create.html'
    url_name = 'user-residentialinfo-create'
    form_class = ResidentialForm

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()
        context['nav_users_login'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])
        return context

# =========================== UPDATE RESIDENCIAL INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserResidentialUpdateView(SuccessMessageMixin, UpdateView):
    model = Residentialplace
    template_name = 'user/user_residential_update.html'
    url_name = 'user-residentialinfo-update'
    form_class = UpdateResidentialForm
    success_message = 'Información residencial actualizada!'


    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Retrieve the `pk` value from the URL
        return Residentialplace.objects.get(user__pk=pk)
    
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries'] = Country.objects.all()
        context['regions'] = Region.objects.filter(country=self.object.resident_country)
        context['cities'] = SubRegion.objects.filter(
            country=self.object.resident_country, region=self.object.resident_region)
        context['nav_users_login'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])

        return context
    
# =========================== CREATE LABORAL INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserWorkplaceCreateView(SuccessMessageMixin, CreateView):
    model = Workplace
    template_name = 'user/user_workplace_create.html'
    url_name = 'user-workplaceinfo-create'
    form_class = WorkplaceForm

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()
        context['nav_users_login'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])
        return context

# =========================== UPDATE LABORAL INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserWorkplaceUpdateView(SuccessMessageMixin, UpdateView):
    model = Workplace
    template_name = 'user/user_workplace_update.html'
    url_name = 'user-workplaceinfo-update'
    form_class = UpdateWorkplaceForm
    success_message = 'Información laboral actualizada!'


    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Retrieve the `pk` value from the URL
        return Workplace.objects.get(user__pk=pk)
    
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries'] = Country.objects.all()
        context['regions'] = Region.objects.filter(country=self.object.company_country)
        context['cities'] = SubRegion.objects.filter(
            country=self.object.company_country, region=self.object.company_region)
        context['nav_users_login'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])

        return context
    
# =========================== CREATE FINANCIAL INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserFinancialCreateView(SuccessMessageMixin, CreateView):
    model = Financial
    template_name = 'user/user_financial_create.html'
    url_name = 'user-financialinfo-create'
    form_class = FinancialForm

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()
        context['nav_users_login'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])
        return context

# =========================== UPDATE LABORAL INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserFinancialUpdateView(SuccessMessageMixin, UpdateView):
    model = Financial
    template_name = 'user/user_financial_update.html'
    url_name = 'user-financialinfo-update'
    form_class = UpdateFinancialForm
    success_message = 'Información bancaria actualizada!'


    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Retrieve the `pk` value from the URL
        return Financial.objects.get(user__pk=pk)
    
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_users_login'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])
        return context
    
# =========================== CREATE SOCIOECONOMIC INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserSocioeconomicCreateView(SuccessMessageMixin, CreateView):
    model = Socioeconomic
    template_name = 'user/user_socioeconomic_create.html'
    url_name = 'user-socioeconomicinfo-create'
    form_class = SocioeconomicForm

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()
        context['nav_users_login'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])
        return context

# =========================== UPDATE Socieconomic INFO USER  ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserSocieconomicUpdateView(SuccessMessageMixin, UpdateView):
    model = Socioeconomic
    template_name = 'user/user_socioeconomic_update.html'
    url_name = 'user-socioeconomicinfo-update'
    form_class = UpdateSocioeconomicForm
    success_message = 'Información socioeconomica actualizada!'


    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Retrieve the `pk` value from the URL
        return Socioeconomic.objects.get(user__pk=pk)
    
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()
        context['nav_users_login'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])
        return context