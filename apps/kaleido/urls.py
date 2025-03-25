from django.urls import  path
from .views.kaleido_views import KaleidoApiListView, create_wallet_service, get_list_of_wallets_hosted,test

from apps.kaleido.views.kaleido_core import AppContractView, CompileContractView, PromoteContractView

from apps.kaleido.views.kaleido_views_model import ListUserWalletsView

from apps.kaleido.views.kaleido_fund import Mint721View, SafeTransfer721View, SafeTransfer721IndexToIndexView, ReceipStoreView, get_wallet_address, get_token_balance, burn_721_token, TokenOwnershipView, Test

urlpatterns = [
    #============================= APIREST Views Kaleido =================================
    path('api/list/', get_list_of_wallets_hosted, name='get-list-wallet-hosted'),
    path('api/create-wallet/',create_wallet_service, name='create-wallet-service'),
    path('api/get-wallets/',KaleidoApiListView.as_view(),name=KaleidoApiListView.url_name),
    path('api/test/',test, name='test'),
    
    #============================= APIREST views Kaleido Core =================================
    
    path('api/app_contract/', AppContractView.as_view(), name='app-contract'),
    path('api/compile_contract/', CompileContractView.as_view(), name='compile-contract'),
    path('api/promote_contract/', PromoteContractView.as_view(), name='promote-contract'),
    
    #============================= APIREST Views Model =================================
    path('api/my_wallets/', ListUserWalletsView.as_view(), name='wallet-list'),
    
    path('api/address/', get_wallet_address, name='address'),
    path('api/balance/', get_token_balance, name='balance'),
    path('api/ownership/', TokenOwnershipView.as_view(), name='ownership'),
    path('api/burn/', burn_721_token, name='burn'),
    path('api/mint_721/', Mint721View.as_view(), name='mint-721-token'),
    
    path('api/safe_transfer/', SafeTransfer721View.as_view(), name='safe-transfer-from'),
    path('api/safe_transfer_index_to_index/', SafeTransfer721IndexToIndexView.as_view(), name='safe-transfer-index-to-index'),
    path('api/receipt_store/', ReceipStoreView.as_view(), name='receipt-store'),
    
    path('api/test_fund/', Test.as_view(), name='test'),
]