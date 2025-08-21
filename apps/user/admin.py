from django.contrib import admin
from apps.user.models import User, Role, PasswordReset, IdType
from apps.user.models_permission import UserAdminPermission

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['pk','email', 'code', 'phone', 'document_number', 'last_password_change']
    list_filter = ['role', 'groups']


class RoleAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name']
admin.site.register(Role, RoleAdmin)

class IdTypeAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name']
admin.site.register(IdType, IdTypeAdmin)

class UserAdminPermissionAdmin(admin.ModelAdmin):
    list_display = ['id',]
admin.site.register(UserAdminPermission, UserAdminPermissionAdmin)

@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    pass
