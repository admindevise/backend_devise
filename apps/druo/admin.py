from django.contrib import admin
from .models import Bank, AccountSubtype, AccountType, Token, UserDruo

@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ['pk', 'institution_name']

@admin.register(AccountSubtype)
class AccountSubtypeAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name']

@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name']

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ['pk', 'created_at']

@admin.register(UserDruo)
class UserDruoAdmin(admin.ModelAdmin):
    list_display = ['pk', 'user_devise', 'uuid', 'created']