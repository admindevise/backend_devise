from django.contrib import admin
from .models import FinancialInstitution, FinancialInstitutionApproval, FinancialInstitutionApplication

class FinancialInstitutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'institution_type', 'country', 'created_at')
    search_fields = ('name', 'institution_type', 'country')
    list_filter = ('institution_type', 'country', 'created_at')
    ordering = ('name',)

class FinancialInstitutionApprovalAdmin(admin.ModelAdmin):
    list_display = ('id', 'financial_institution', 'user', 'investor_profile')
    search_fields = ('financial_institution__name', 'user__username', 'investor_profile')
    list_filter = ('approval_date',)
    ordering = ('-approval_date',)

class FinancialInstitutionApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'financial_institution', 'status', 'requested_at')
    search_fields = ('user__username', 'financial_institution__name', 'status')
    list_filter = ('status', 'requested_at')
    ordering = ('-requested_at',)
    
admin.site.register(FinancialInstitution, FinancialInstitutionAdmin)
admin.site.register(FinancialInstitutionApproval, FinancialInstitutionApprovalAdmin)
admin.site.register(FinancialInstitutionApplication, FinancialInstitutionApplicationAdmin)