from django.contrib import admin
from .models import Categoria, Articulo


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['pk', 'nombre']

@admin.register(Articulo)
class ArticuloAdmin(admin.ModelAdmin):
    list_display = ['pk', 'titulo', 'categoria']