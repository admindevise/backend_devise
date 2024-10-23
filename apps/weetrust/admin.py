from django.contrib import admin
from .models import AccessTokenWeetrust, DocumentSesionResult

@admin.register(AccessTokenWeetrust)
class AccessTokenWeetrustAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']

@admin.register(DocumentSesionResult)
class DocumentSesionResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at']