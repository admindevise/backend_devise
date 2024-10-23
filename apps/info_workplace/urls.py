from django.urls import  path
from rest_framework import routers

from .views.workplace_views import ( CreateWorkplace, UpdateReadWorkplace )


router = routers.SimpleRouter()

urlpatterns = [
   
    # # ========================  Workplace Info data  ===============================
    path('workplace/create/', CreateWorkplace.as_view()),
    path ('workplace/update_read/', UpdateReadWorkplace.as_view()), 

]
