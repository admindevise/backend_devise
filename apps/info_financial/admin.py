from django.contrib import admin
from .models import Financial

@admin.register(Financial)
class FinancialAdmin(admin.ModelAdmin):
    list_display = ['pk', 'user', 'fiducia']