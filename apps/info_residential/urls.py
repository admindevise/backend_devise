from django.urls import  path
from rest_framework import routers

from .views.residentialplace_views import ( CreateResidentialplaceInfo, UpdateReadResidentialplaceInfo )


router = routers.SimpleRouter()


urlpatterns = [
   
    # # ========================  Api Residential Work Info data  ===============================
    path('residential/create/', CreateResidentialplaceInfo.as_view()),
    path ('residential/update_read/', UpdateReadResidentialplaceInfo.as_view()), 

]

urlpatterns += router.urls