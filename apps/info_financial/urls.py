from django.urls import  path
from rest_framework import routers

from .views.financial_views import ( CreateFinancialUserInfo, UpdateReadFinancialUserInfo )


router = routers.SimpleRouter()


urlpatterns = [
   
    # # ========================  Api Financial Info data  ===============================
    path('financialinfo/create/', CreateFinancialUserInfo.as_view()),
    path ('financialinfo/update_read/', UpdateReadFinancialUserInfo.as_view()), 

]

urlpatterns += router.urls