from django.contrib import admin
from django.utils.html import format_html
from apps.audit.models import AuditCategory, AuditAction, AuditLog

class AuditCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'description']
    search_fields = ['name', 'code', 'description']
    list_filter = ['name', 'code']

class AuditActionAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'name', 'code', 'description', 'severity']
    search_fields = ['name', 'code', 'description']
    list_filter = ['category', 'name', 'code', 'severity']

class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'action', 'content_type', 'object_id', 'transaction_id', 'ip_address', 'display_status', 'created_at']
    search_fields = ['user__username', 'action__name', 'content_type__model', 'object_id', 'transaction_id', 'ip_address', 'status']
    list_filter = ['user', 'action', 'content_type', 'status']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    def display_status(self, obj):
        """Personaliza la visualización del estado con iconos"""
        if obj.status == 'SUCCESS':
            return format_html('<span style="color: green;"> {}</span>', obj.status)
        elif obj.status == 'ERROR':
            return format_html('<span style="color: red;"> {}</span>', obj.status)
        elif obj.status == 'PENDING':
            return format_html('<span style="color: orange;"> {}</span>', obj.status)
        else:
            return obj.status
    
    display_status.short_description = 'Status'
    display_status.admin_order_field = 'status'  # Permite ordenar por este campo

admin.site.register(AuditCategory, AuditCategoryAdmin)
admin.site.register(AuditAction, AuditActionAdmin)
admin.site.register(AuditLog, AuditLogAdmin)