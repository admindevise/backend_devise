from django.contrib import admin
from apps.kaleido.models import Wallet, WalletSmartContract, InstanceOfTokenContract721, AppContract, CompileContract, PromoteContract

class AppContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'app_contract_id', 'user', 'name')
    search_fields = ('name', 'app_contract_id')
    list_display_links = ('id', 'app_contract_id')

class CompileContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'compiled_contract_id', 'app_contract', 'user')
    search_fields = ('description', 'compiled_contract_id')
    list_display_links = ('id', 'compiled_contract_id')

class PromoteContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'endpoint', 'app_contract', 'user')
    search_fields = ('endpoint', 'endpoint')
    list_display_links = ('id', 'endpoint')

class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'id_wallet', 'secret')
    search_fields = ('id_wallet',)

class InstanceOfTokenContract721Admin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'symbol', 'promote_contract')
    search_fields = ('name', 'symbol')

admin.site.register(AppContract, AppContractAdmin)
admin.site.register(CompileContract, CompileContractAdmin)
admin.site.register(PromoteContract, PromoteContractAdmin)
admin.site.register(InstanceOfTokenContract721, InstanceOfTokenContract721Admin)
admin.site.register(Wallet, WalletAdmin)