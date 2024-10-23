from django.urls import  path
from .views.kaleido_views import KaleidoApiListView, create_wallet_service, get_list_of_wallets_hosted,test

urlpatterns = [
    #============================= APIREST Views Kaleido =================================
    path('api/list/', get_list_of_wallets_hosted, name='get-list-wallet-hosted'),
    path('api/create-wallet/',create_wallet_service, name='create-wallet-service'),
    path('api/get-wallets/',KaleidoApiListView.as_view(),name=KaleidoApiListView.url_name),
    path('api/test/',test, name='test'),
]