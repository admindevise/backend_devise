from django.contrib import admin
from .models import Notaria

@admin.register(Notaria)
class NotariaAdmin(admin.ModelAdmin):
    list_display = ['pk']