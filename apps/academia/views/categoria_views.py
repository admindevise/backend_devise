from django.shortcuts import get_object_or_404
from apps.academia.forms.categoria_form import CategoriaForm
from apps.academia.models import Categoria
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import View, ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _

from rest_framework import generics
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.academia.serializers.serializer_categoria import CategoriaSerializer

# =============================================================================
#                           APIREST ActorType RESOURCE
# =============================================================================
@permission_classes([IsAuthenticated])
class CategoriaApiListView(generics.ListAPIView):
    serializer_class = CategoriaSerializer
    pagination_class = None  # Desactiva la paginación

    def get_queryset(self):
        queryset = Categoria.objects.all().order_by('nombre')
        return queryset
    

# =============================================================================
#                           BACKOFFICE RESOURCE
# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('academia.view_categoria', raise_exception=True), name='dispatch')
class CategoriaListView(ListView):
    template_name = 'categoria_list.html'
    url_name = 'academia-categoria-list'
    model = Categoria
    paginate_by = 25

    def get_queryset(self):
        filter_list = self.request.GET.getlist('filter')
        filters = Q()
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'nombre__icontains',
                    'descripcion__icontains',

                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})

        queryset = Categoria.objects.filter(filters).order_by('nombre')

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

        context['nav_academia'] = True
        context['nav_academia_categoria'] = True

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
@method_decorator(permission_required('academia.create_categoria', raise_exception=True), name='dispatch')
class CategoriaCreateView(CreateView):
    form_class = CategoriaForm
    template_name = 'categoria_create.html'
    url_name = 'academia-categoria-add'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_academia'] = True
        context['nav_academia_categoria'] = True
        return context
    
    def form_valid(self, form):
        return super().form_valid(form)

    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("academia-categoria-detail", kwargs={"pk": pk})

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('academia.change_categoria', raise_exception=True), name='dispatch')
class CategoriaDetailView(SuccessMessageMixin, DetailView):
    template_name = 'categoria_detail.html'
    url_name = 'academia-categoria-detail'
    model = Categoria
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_academia'] = True
        context['nav_academia_categoria'] = True
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('academia.change_categoria', raise_exception=True), name='dispatch')
class CategoriaUpdateView(SuccessMessageMixin, UpdateView):
    template_name = 'categoria_update.html'
    url_name = 'academia-categoria-update'
    form_class = CategoriaForm
    model = Categoria
    success_message = 'Categoria actualizada!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_academia'] = True
        context['nav_academia_categoria'] = True
        return context
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("academia-categoria-detail", kwargs={"pk": pk})

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('academia.delete_categoria', raise_exception=True), name='dispatch')
class CategoriaDeleteView(View):
    url_name = 'academia-categoria-delete'

    def post(self, request,):
        categoria = get_object_or_404(Categoria, pk=self.request.POST['pk'])
        try:
            categoria.delete()
            response = {
                'status': 'success',
                'title': _('Eliminacion exitosa!'),
                'message': _('La categoria a sido borrado')
            }
        except:
            response = {
                'status': 'error',
                'title': _('Fallo al intentar eliminar el elemento!'),
                'message': _('La categoria tiene historicos en base de datos no puede ser eliminado')
            }
        return JsonResponse(response)

# =============================================================================

@method_decorator(login_required, name='dispatch')
class CategoriaDeactivateView(View):

    def post(self, request,):
        categoria = get_object_or_404(Categoria, pk=self.request.POST['pk'])
        if (categoria.status):
            categoria.status = False
            title = 'Desactivación exitosa'
            message = 'La categoria ha sido deshabilitada'
            categoria.save()
        else:
            categoria.status = True
            title = 'Activación Exitosa'
            message = 'La categoria ha sido habilitada exitosamente'
            categoria.save()

        response = {
            'changed': 'success',
            'title': title,
            'message': message
        }

        return JsonResponse(response)