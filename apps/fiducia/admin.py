from django.contrib import admin
from .models import Fiducia

@admin.register(Fiducia)
class FiduciaAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name', 'nit']