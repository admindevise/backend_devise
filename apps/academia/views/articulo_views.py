from django.shortcuts import get_object_or_404
from apps.academia.forms.articulo_form import ArticuloForm
from apps.academia.models import Articulo
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
from apps.academia.serializers.serializer_articulo import ArticuloSerializer
from django.core.paginator import Paginator
from rest_framework.pagination import PageNumberPagination
# =============================================================================
#                           APIREST ActorType RESOURCE
# =============================================================================


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 5  # Establece el tamaño de la página
    page_size_query_param = 'page_size'  # Parámetro para ajustar el tamaño de la página desde la solicitud
    max_page_size = 100  # Establece el tamaño máximo de la página

    def get_page_range(self, start, end):
        # Personaliza el rango de páginas disponibles, por ejemplo, limitándolo de 1 a 10
        return range(max(start, 1), min(end, 11))

@permission_classes([IsAuthenticated])
class ArticuloApiListView(generics.ListAPIView):
    serializer_class = ArticuloSerializer
    pagination_class = CustomPageNumberPagination
    def get_queryset(self):
        

        queryset = Articulo.objects.all().order_by('titulo')
        categoria = self.request.GET.get('categoria')
        buscar = self.request.GET.get('buscar')
        pagina = self.request.GET.get('page', 1) 

       
        if categoria:
            queryset = queryset.filter(categoria__id = categoria)
        if buscar:
            queryset = queryset.filter(Q(titulo__icontains=buscar) | Q(contenido__icontains=buscar))
        
       
        return queryset
    

    


# =============================================================================
#                           BACKOFFICE RESOURCE
# =============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('academia.view_articulo', raise_exception=True), name='dispatch')
class ArticuloListView(ListView):
    template_name = 'articulo_list.html'
    url_name = 'academia-articulo-list'
    model = Articulo
    paginate_by = 25

    def get_queryset(self):
        filter_list = self.request.GET.getlist('filter')
        filters = Q()
        if (filter_list and filter_list != ''):
            for filter in filter_list:
                fields = [
                    'titulo__icontains',
                    'contenido__icontains',

                ]

                for str_field in fields:
                    filters |= Q(**{str_field: filter})

        queryset = Articulo.objects.filter(filters).order_by('fecha')

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
        context['nav_academia_articulo'] = True

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
@method_decorator(permission_required('academia.create_articulo', raise_exception=True), name='dispatch')
class ArticuloCreateView(CreateView):
    form_class = ArticuloForm
    template_name = 'articulo_create.html'
    url_name = 'academia-articulo-add'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_academia'] = True
        context['nav_academia_articulo'] = True
        return context
    
    def form_valid(self, form):
        return super().form_valid(form)

    def get_success_url(self):
        pk = self.object.pk
        return reverse_lazy("academia-articulo-detail", kwargs={"pk": pk})

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('academia.change_articulo', raise_exception=True), name='dispatch')
class ArticuloDetailView(SuccessMessageMixin, DetailView):
    template_name = 'articulo_detail.html'
    url_name = 'academia-articulo-detail'
    model = Articulo
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_academia'] = True
        context['nav_academia_articulo'] = True
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('academia.change_articulo', raise_exception=True), name='dispatch')
class ArticuloUpdateView(SuccessMessageMixin, UpdateView):
    template_name = 'articulo_update.html'
    url_name = 'academia-articulo-update'
    form_class = ArticuloForm
    model = Articulo
    success_message = 'Articulo actualizada!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nav_academia'] = True
        context['nav_academia_articulo'] = True
        return context
    def get_success_url(self):
        pk = self.kwargs["pk"]
        return reverse_lazy("academia-articulo-detail", kwargs={"pk": pk})

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('academia.delete_articulo', raise_exception=True), name='dispatch')
class ArticuloDeleteView(View):
    url_name = 'academia-articulo-delete'

    def post(self, request,):
        articulo = get_object_or_404(Articulo, pk=self.request.POST['pk'])
        try:
            articulo.delete()
            response = {
                'status': 'success',
                'title': _('Eliminacion exitosa!'),
                'message': _('La articulo a sido borrado')
            }
        except:
            response = {
                'status': 'error',
                'title': _('Fallo al intentar eliminar el elemento!'),
                'message': _('La articulo tiene historicos en base de datos no puede ser eliminado')
            }
        return JsonResponse(response)

# =============================================================================

@method_decorator(login_required, name='dispatch')
class ArticuloDeactivateView(View):

    def post(self, request,):
        articulo = get_object_or_404(Articulo, pk=self.request.POST['pk'])
        if (articulo.status):
            articulo.status = False
            title = 'Desactivación exitosa'
            message = 'La articulo ha sido deshabilitada'
            articulo.save()
        else:
            articulo.status = True
            title = 'Activación Exitosa'
            message = 'La articulo ha sido habilitada exitosamente'
            articulo.save()

        response = {
            'changed': 'success',
            'title': title,
            'message': message
        }

        return JsonResponse(response)