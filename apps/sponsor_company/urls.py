from django.urls import  path
from rest_framework import routers

from .views.backoffice_company import ( CompanyListView, CompanyDetailView, CompanyUpdateView,
                                       CompanyListExportView,
                                       ApprovedSponsorView )

from .views.company_views import ( CreateCompany, UpdateCompany, ReadCompany,
                                ListSelectSponsorView, )

router = routers.SimpleRouter()

urlpatterns = [
   
    #============================= Backoffice Views Company =================================
    path('list/', CompanyListView.as_view(), name=CompanyListView.url_name),
    path('<int:pk>/detail/', CompanyDetailView.as_view(), name=CompanyDetailView.url_name),
    path('<int:pk>/update/', CompanyUpdateView.as_view(), name=CompanyUpdateView.url_name),
    # path('deactivate/', CompanyDeactivateView.as_view(), name=CompanyDeactivateView.url_name),

    path('approved/', ApprovedSponsorView.as_view(), name=ApprovedSponsorView.url_name),

    path('export/list/', CompanyListExportView.as_view(), name=CompanyListExportView.url_name),
     # # ========================  Company Info data  APIREST ===============================
    path('create/', CreateCompany.as_view()),
    path ('update/', UpdateCompany.as_view()),
    path ('read/', ReadCompany.as_view()),
    path ('select/list/', ListSelectSponsorView.as_view()),

    

]
