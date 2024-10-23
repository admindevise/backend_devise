from django.contrib import admin
from .models import Socioeconomic, OriginFund

@admin.register(Socioeconomic)
class SocioeconomicAdmin(admin.ModelAdmin):
    list_display = ['pk', 'user']

@admin.register(OriginFund)
class OriginFundAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name']