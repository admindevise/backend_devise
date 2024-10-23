from django.contrib import admin
from .models import ( EstadoAprobacion, FeedbackMinutaEscrituracion, MinutaEscrituracion, TipoProyecto, Categoria, ActivoInversion,
                FeedbackActivoInversion, Fideicomiso)

@admin.register(TipoProyecto)
class TipoProyectoAdmin(admin.ModelAdmin):
    list_display = ['pk', 'nombre']

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['pk', 'nombre']

@admin.register(ActivoInversion)
class ActivoInversionAdmin(admin.ModelAdmin):
    list_display = ['pk', 'codigo', 'nombre', 'estado_aprobacion', 'sponsor']
    list_filter =   ['tipo_proyecto', 'categoria', 'sponsor']

@admin.register(Fideicomiso)
class FideicomisoAdmin(admin.ModelAdmin):
    list_display = ['pk', 'activo', 'id_weetrust_document', 'firmado_todos']
    list_filter =   ['activo', 'email_fiducia', 'email_sponsor']

@admin.register(FeedbackActivoInversion)
class FeedbackActivoInversionAdmin(admin.ModelAdmin):
    list_display = ['pk', 'remitente', 'destinatario', 'estado_actual', 'archivo_adjunto']
    list_filter =   ['remitente', 'destinatario', 'activo']

@admin.register(EstadoAprobacion)
class EstadoAprobacionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'codigo', 'paso')

@admin.register(MinutaEscrituracion)
class MinutaEscrituracionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'activo')

@admin.register(FeedbackMinutaEscrituracion)
class FeedbackMinutaEscrituracionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'minuta', 'remitente')
