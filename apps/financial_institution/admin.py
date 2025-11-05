from django.contrib import admin
from .models.core import FinancialInstitution, FinancialInstitutionApproval, FinancialInstitutionApplication
from apps.financial_institution.models.permissions import (
    FIPermission,
    FICustomGroup,
    FIUserGroupMembership
)

@admin.register(FinancialInstitution)
class FinancialInstitutionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'institution_type', 'country', 'created_at']
    search_fields = ['name', 'institution_type', 'country']
    list_filter = ['institution_type', 'country', 'created_at']
    ordering = ['name',]


@admin.register(FinancialInstitutionApplication)
class FinancialInstitutionApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'financial_institution', 'status', 'created_at']
    search_fields = ['user__username', 'financial_institution__name', 'status']
    list_filter = ['status', 'created_at']
    ordering = ['-created_at',]


@admin.register(FinancialInstitutionApproval)
class FinancialInstitutionApprovalAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status']
    search_fields = ['user__username', 'status']
    list_filter = ['approval_date',]
    ordering = ['-approval_date',]


@admin.register(FIPermission)
class FIPermissionAdmin(admin.ModelAdmin):
    list_display = ['codename', 'name', 'category', 'created_at']
    list_filter = ['category']
    search_fields = ['name', 'codename']
    ordering = ['category', 'name']


@admin.register(FICustomGroup)
class FICustomGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'financial_institution', 'is_active', 'created_at']
    list_filter = ['financial_institution', 'is_active']
    search_fields = ['name', 'financial_institution__name']
    filter_horizontal = ['permissions']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('financial_institution')


@admin.register(FIUserGroupMembership)
class FIUserGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'is_active', 'assigned_at', 'assigned_by']
    list_filter = ['is_active', 'group__financial_institution']
    search_fields = ['user__email', 'group__name']
    raw_id_fields = ['user', 'assigned_by']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'group', 'assigned_by')