from apps.user.models import User, Role, Group
from apps.info_residential.models import Residentialplace
from apps.info_workplace.models import Workplace
from apps.sponsor_company.models import SponsorCompany

from apps.info_financial.models import Financial
# from apps.utils.permissions import CustomDjangoModelPermission
from cities_light.models import Country, Region, SubRegion

from django.conf import settings
from django.db.models import Q
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import ListView, CreateView, DetailView, UpdateView

from ...user.forms.residential_form import ResidentialForm, UpdateResidentialForm
from ...user.forms.user_form import UserBasicInfoForm, UserDocumentInfoForm
from ...user.forms.workplace_form import WorkplaceForm, UpdateWorkplaceForm

from io import BytesIO
from xhtml2pdf import pisa
from import_export import fields, resources, widgets
import datetime as dt

from django.contrib.auth.password_validation import validate_password


# =============================================================================
#                           BACKOFFICE RESOURCE
# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class UserNotariaListView(ListView):
    template_name = 'user/user_notaria_list.html'
    url_name = 'user-notaria-list'
    model = User
    paginate_by = 25

    def get_queryset(self):
        notaria_role = Role.objects.get(name='NOTARIO')
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

        queryset = User.objects.filter(role = notaria_role).filter(filters).order_by('email')

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
        context['nav_users_notaria'] = True

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
class UserNotariaCreateView(SuccessMessageMixin, CreateView):
    template_name = 'user/user_notaria_create.html'
    url_name = 'user-notaria-add'
    model = User
    fields = [
        'email', 'indicative',
        'first_name', 'last_name',
        'local_id_type', 'document_number',
        'phone', 'password',
        'birth_country',
        'role', 'notaria',
        ]
    success_message = 'Usuario Notaria creado exitosamente!'


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
        return reverse_lazy("user-notaria-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups'] = Group.objects.filter(name__icontains='NOTARIO')
        context['roles'] = Role.objects.all()
        context['nav_users_notaria'] = True
        context['countries'] = Country.objects.all()
        return context
    
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.view_user', raise_exception=True), name='dispatch')
class UserNotariaDetailView(DetailView):
    template_name = 'user/user_notaria_detail.html'
    url_name = 'user-notaria-detail'
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_users_notaria'] = True
        usuario = User.objects.get(id=self.kwargs['pk'])
        context['group_name'] = usuario.groups.first().name if usuario.groups.exists() else None
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

        if usuario.notaria:
            context['notaria'] = usuario.notaria
        else:
            context['notaria'] = None

        return context
    
# =========================== UPDATE BASIC INFO USER NOTARIA ===================================
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserBasicInfoUpdateView(SuccessMessageMixin, UpdateView):
    model = User
    template_name = 'user/basicinfo_update.html'
    url_name = 'user-notaria-basicinfo-update'
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
        return reverse_lazy("user-notaria-detail", kwargs={"pk": pk})

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
        context['nav_users_notaria'] = True
        return context
    
# =========================== UPDATE DOCUMENTAL INFO USER NOTARIA ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserDocumentUpdateView(SuccessMessageMixin, UpdateView):
    model = User
    template_name = 'user/user_document_update.html'
    url_name = 'user-notaria-documentinfo-update'
    form_class = UserDocumentInfoForm
    success_message = 'Información documental actualizada!'

    def form_valid(self, form):
        usuario = form.save()
        usuario.kyc_validated = 'sucessfull_document'
        usuario.save()
        return super().form_valid(form)

    
    
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-notaria-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries'] = Country.objects.all()
        context['regions'] = Region.objects.filter(country=self.object.doc_country_expedition)
        context['cities'] = SubRegion.objects.filter(
            country=self.object.doc_country_expedition, region=self.object.doc_region_expedition)
        context['nav_users_notaria'] = True
        return context

# =========================== CREATE RESIDENCIAL INFO USER  NOTARIA ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserResidentialCreateView(SuccessMessageMixin, CreateView):
    model = Residentialplace
    template_name = 'user/user_residential_create.html'
    url_name = 'user-notaria-residentialinfo-create'
    form_class = ResidentialForm

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-notaria-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()
        context['nav_users_notaria'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])
        return context

# =========================== UPDATE RESIDENCIAL INFO USER  NOTARIA ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserResidentialUpdateView(SuccessMessageMixin, UpdateView):
    model = Residentialplace
    template_name = 'user/user_residential_update.html'
    url_name = 'user-notaria-residentialinfo-update'
    form_class = UpdateResidentialForm
    success_message = 'Información residencial actualizada!'


    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Retrieve the `pk` value from the URL
        return Residentialplace.objects.get(user__pk=pk)
    
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-notaria-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries'] = Country.objects.all()
        context['regions'] = Region.objects.filter(country=self.object.resident_country)
        context['cities'] = SubRegion.objects.filter(
            country=self.object.resident_country, region=self.object.resident_region)
        context['nav_users_notaria'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])

        return context
    
# =========================== CREATE LABORAL INFO USER NOTARIA ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserWorkplaceCreateView(SuccessMessageMixin, CreateView):
    model = Workplace
    template_name = 'user/user_workplace_create.html'
    url_name = 'user-notaria-workplaceinfo-create'
    form_class = WorkplaceForm

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-notaria-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()
        context['nav_users_notaria'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])
        return context

# =========================== UPDATE LABORAL INFO USER NOTARIA ===================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('user.change_user', raise_exception=True), name='dispatch')
class UserWorkplaceUpdateView(SuccessMessageMixin, UpdateView):
    model = Workplace
    template_name = 'user/user_workplace_update.html'
    url_name = 'user-notaria-workplaceinfo-update'
    form_class = UpdateWorkplaceForm
    success_message = 'Información laboral actualizada!'


    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Retrieve the `pk` value from the URL
        return Workplace.objects.get(user__pk=pk)
    
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("user-notaria-detail", kwargs={"pk": pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries'] = Country.objects.all()
        context['regions'] = Region.objects.filter(country=self.object.company_country)
        context['cities'] = SubRegion.objects.filter(
            country=self.object.company_country, region=self.object.company_region)
        context['nav_users_notaria'] = True
        context['user'] = User.objects.get(id=self.kwargs["pk"])

        return context
    

