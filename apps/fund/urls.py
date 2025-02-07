from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FundViewSet, FundPriceViewSet, ListRuntimeWalletsView, ListWalletsView, CreateWalletView, IndexWalletView, CreateContractView, CompileContractView, PromoteContractView, DeployInstanceOfTokenContract20View, DeployInstanceOfTokenContract721View, Mint721View, SafeTransfer721View, SafeTransfer721IndexToIndexView, ReceipStoreView, CreateWalletCDView, IndexWalletCDView

router = DefaultRouter()
router.register(r'main', FundViewSet, basename='fund')

fund_price_list = FundPriceViewSet.as_view({
    'get': 'list'
})

urlpatterns = [
    path('', include(router.urls)),
    path('fund_prices/<int:fund_id>/<str:interval>/', fund_price_list, name='fund-price-list'),
    
    # Wallets
    path('runtime_wallets/', ListRuntimeWalletsView.as_view(), name='list-wallets'),
    path('list_wallets/', ListWalletsView.as_view(), name='list-wallets'),
    path('create_wallet/', CreateWalletView.as_view(), name='create-wallet'),
    path('index_wallet/', IndexWalletView.as_view(), name='index-wallet'),
    
    # Contracts
    path('create_contract/', CreateContractView.as_view(), name='create-contract'),
    path('compile_contract/', CompileContractView.as_view(), name='compile-contract'),
    path('promote_contract/', PromoteContractView.as_view(), name='promote-contract'),
    
    path('deploy_instance_contract_20/', DeployInstanceOfTokenContract20View.as_view(), name='deploy-contract-20'),
    path('deploy_instance_contract_721/', DeployInstanceOfTokenContract721View.as_view(), name='deploy-contract-721'),
    
    path('mint_721/', Mint721View.as_view(), name='mint-721'),
    path('safe_transfer_721/', SafeTransfer721View.as_view(), name='safe-transfer-721'),
    path('safe_transfer_721_index_to_index/', SafeTransfer721IndexToIndexView.as_view(), name='safe-transfer-721-index-to-index'),
    
    path('receipt_store/', ReceipStoreView.as_view(), name='receipt-store'),
    
    # Wallets CD
    path('create_wallet_cd/', CreateWalletCDView.as_view(), name='create-wallet-cd'),
    path('index_wallet_cd/', IndexWalletCDView.as_view(), name='index-wallet-cd'),
    
]