from django.urls import  path

from . import views


urlpatterns = [
    # ========================  Api User Correspondence data  ===============================
    path('tokenweetrust/landing', views.landing_view, name = 'oauth2-landing'),
    
]
