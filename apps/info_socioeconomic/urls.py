from django.urls import  path
from rest_framework import routers

from .views.socioeconomic_views import ( SocioeconomicUserInfo, UpdateReadSocioeconomicUserInfo, ListOriginsFunds )


router = routers.SimpleRouter()


urlpatterns = [
   
    # # ========================  Api Financial Info data  ===============================
    path('socioeconomic/listoriginsfunds/', ListOriginsFunds.as_view()),
    path('socioeconomic/create/', SocioeconomicUserInfo.as_view()),
    path('socioeconomic/update_read/', UpdateReadSocioeconomicUserInfo.as_view()), 

]

urlpatterns += router.urls