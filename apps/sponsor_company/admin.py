from django.contrib import admin
from .models import SponsorCompany

@admin.register(SponsorCompany)
class SponsorCompanyAdmin(admin.ModelAdmin):
    list_display = ['pk', 'user', 'company_name']