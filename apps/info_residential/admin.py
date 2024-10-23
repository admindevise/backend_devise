from django.contrib import admin
from .models import Residentialplace

@admin.register(Residentialplace)
class ResidentialplaceAdmin(admin.ModelAdmin):
    list_display = ['pk', 'user']