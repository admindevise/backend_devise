from django.urls import  path
from .views.kaleido_views import KaleidoApiListView, create_wallet_service, get_list_of_wallets_hosted,test

from apps.kaleido.views.kaleido_views_model import ListUserWalletsView

from apps.kaleido.views.kaleido_fund import Mint721View, SafeTransfer721View, SafeTransfer721IndexToIndexView

urlpatterns = [
    #============================= APIREST Views Kaleido =================================
    path('api/list/', get_list_of_wallets_hosted, name='get-list-wallet-hosted'),
    path('api/create-wallet/',create_wallet_service, name='create-wallet-service'),
    path('api/get-wallets/',KaleidoApiListView.as_view(),name=KaleidoApiListView.url_name),
    path('api/test/',test, name='test'),
    
    #============================= APIREST Views Model =================================
    path('api/my_wallets/', ListUserWalletsView.as_view(), name='wallet-list'),
    
    path('api/mint_721/', Mint721View.as_view(), name='mint-721-token'),
    path('api/safe_transfer/', SafeTransfer721View.as_view(), name='safe-transfer-from'),
    path('api/safe_transfer_index_to_index/', SafeTransfer721IndexToIndexView.as_view(), name='safe-transfer-index-to-index'),
]