
from django.forms.models import BaseModelForm
from apps.user.models import User
from ..models import Notaria

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
from django.template.loader import get_template

from ...user.forms.financial_form import FinancialForm, UpdateFinancialForm

from io import BytesIO
from xhtml2pdf import pisa
from import_export import fields, resources, widgets

import datetime as dt

# =============================================================================
#                           IMPORT - EXPORT RESOURCE
# =============================================================================
class NotariaResource(resources.ModelResource):
    country = fields.Field(attribute='get_country_display')
    region = fields.Field(attribute='get_region_display')
    city = fields.Field(attribute='get_city_display')

    class Meta:
        model = Notaria
        fields = (
            'name',
            'country',
            'region',
            'city',
            'phone',
            'address',
            'zip_code',
        )
        export_order = (
            'name',
            'country',
            'region',
            'city',
            'phone',
            'address',
            'zip_code',
        )
# =============================================================================
#                           BACKOFFICE RESOURCE
# =============================================================================
# =============================================================================

    
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('notaria.view_notaria', raise_exception=True), name='dispatch')
class NotariaListView(ListView):
    template_name = 'notaria_list.html'
    url_name = 'notaria-list'
    model = Notaria
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

        queryset = Notaria.objects.filter(filters).order_by('name')

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            if (filter_status == '0'):
                queryset = queryset.filter(status=False)

            elif (filter_status == '1'):
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

        filter_status = self.request.GET.get('status')
        if not (filter_status == '' or filter_status == None):
            filter_obj['filter_status'] = filter_status
            filter_obj['url'] += '&status={}'.format(filter_status)
        context['filter_status'] = filter_status
        context['filter_obj'] = filter_obj
        context['nav_notaria_list'] = True

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
@method_decorator(permission_required('notaria.view_notaria', raise_exception=True), name='dispatch')
class NotariaListExportView(View):
    url_name = 'notaria-list-export'

    def _get_pdf_export(self, queryset, file_name):
        template = get_template('report/notaria_list_export.html')
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
        dataset = NotariaResource().export(queryset)
        file_name = "notarias_{}".format(dt.datetime.now().strftime("%d-%m-%Y"))

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
            queryset = Notaria.objects.all().order_by('id')
            filter_status = request.POST.get('filter_status')
            if not (filter_status == '' or filter_status == None):
                if (filter_status == '0'):
                    queryset = queryset.filter(status=False, rejected=False)

                elif (filter_status == '1'):
                    queryset = queryset.filter(status=True, rejected=False)

                

            filter_list = request.POST.getlist('filter')
            filters = Q()
            if ( filter_list and filter_list != ''):
                for filter in filter_list:
                    fields = [
                        'name__icontains',
                    ]

                    for str_field in fields:
                        filters |= Q(**{str_field: filter})

                queryset = queryset.filter(filters)

        else:
            if not (id_seleccion == '' or id_seleccion == None):
                queryset = Notaria.objects.filter(id__in=id_seleccion).order_by('id')
            else:
                queryset = Notaria.objects.none()

        response = self._get_export_response(queryset, format=format_file)

        return response

# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('notaria.create_notaria', raise_exception=True), name='dispatch')
class NotariaCreateView(CreateView):
    template_name = 'notaria_create.html'
    url_name = 'notaria-add'
    model = Notaria
    fields = [ 
            'name', 'country', 'region',
            'city', 'phone', 'mobile', 'address',
            'zip_code', 'codigo', 'numero',
            'email',
            ]
    def form_valid(self, form):
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_notaria_list'] = True
        return context

    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("notaria-detail", kwargs={"pk": pk})
    
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('notaria.view_notaria', raise_exception=True), name='dispatch')
class NotariaDetailView(DetailView):
    template_name = 'notaria_detail.html'
    url_name = 'notaria-detail'
    model = Notaria

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_notaria_list'] = True
        return context

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('notaria.change_notaria', raise_exception=True), name='dispatch')
class NotariaUpdateView(SuccessMessageMixin, UpdateView):
    template_name = 'notaria_update.html'
    url_name = 'notaria-update'
    model = Notaria
    fields = [ 
            'name', 'country', 'region',
            'city', 'phone', 'mobile', 'address',
            'zip_code', 'codigo', 'numero',
            'email',
            ]
    success_message = 'Notaria actualizada!'

    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("notaria-detail", kwargs={"pk": pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_notaria_list'] = True
        context['countries'] = Country.objects.all()
        context['regions'] = Region.objects.filter(country=self.object.country)
        context['cities'] = SubRegion.objects.filter(
            country=self.object.country, region=self.object.region)
        return context

    

