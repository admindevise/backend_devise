from django.contrib import admin
from .models import FinancialInstitution, FinancialInstitutionApproval, FinancialInstitutionApplication

class FinancialInstitutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'institution_type', 'country', 'created_at')
    search_fields = ('name', 'institution_type', 'country')
    list_filter = ('institution_type', 'country', 'created_at')
    ordering = ('name',)

class FinancialInstitutionApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'financial_institution', 'status', 'created_at')
    search_fields = ('user__username', 'financial_institution__name', 'status')
    list_filter = ('status', 'created_at')
    ordering = ('-created_at',)

class FinancialInstitutionApprovalAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status')
    search_fields = ('user__username', 'status')
    list_filter = ('approval_date',)
    ordering = ('-approval_date',)
    
admin.site.register(FinancialInstitution, FinancialInstitutionAdmin)
admin.site.register(FinancialInstitutionApproval, FinancialInstitutionApprovalAdmin)
admin.site.register(FinancialInstitutionApplication, FinancialInstitutionApplicationAdmin)