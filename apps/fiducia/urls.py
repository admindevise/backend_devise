from django.urls import  path
from .views.fiducia_views import ( FiduciaListView, FiduciaDetailView,
                                FiduciaUpdateView, ApprovedSponsorView,
                                FiduciaListExportView, FiduciaCreateView,
                                FiduciaFinancialUpdateView, FiduciaFinancialCreateView, ListSelectFiduciaView,
                                )

from .views.user_fiducia import (UserFiduciaListView, UserFiduciaCreateView,
                                UserFiduciaDetailView, UserBasicInfoUpdateView,
                                UserDocumentUpdateView, UserResidentialUpdateView,
                                UserResidentialCreateView, UserWorkplaceUpdateView, 
                                UserWorkplaceCreateView, 
                                )


urlpatterns = [
    # # ========================  Company Info data  APIREST ===============================
    path ('select/list/', ListSelectFiduciaView.as_view()),

    #============================= Backoffice Views Fiducia =================================
    path('create/', FiduciaCreateView.as_view(), name=FiduciaCreateView.url_name),
    path('list/', FiduciaListView.as_view(), name=FiduciaListView.url_name),
    path('<int:pk>/detail/', FiduciaDetailView.as_view(), name=FiduciaDetailView.url_name),
    path('<int:pk>/update/', FiduciaUpdateView.as_view(), name=FiduciaUpdateView.url_name),
    # path('deactivate/', FiduciaDeactivateView.as_view(), name=FiduciaDeactivateView.url_name),
    path('export/list/', FiduciaListExportView.as_view(), name=FiduciaListExportView.url_name),

    path('financial/<int:pk>/update/', FiduciaFinancialUpdateView.as_view(), name=FiduciaFinancialUpdateView.url_name),
    path('financial/<int:pk>/create/', FiduciaFinancialCreateView.as_view(), name=FiduciaFinancialCreateView.url_name),


    #============================= Templates Usuarios FIDUCIA =================================
    path('user/viewlist/', UserFiduciaListView.as_view(), name=UserFiduciaListView.url_name),
    path('user/create/', UserFiduciaCreateView.as_view(), name=UserFiduciaCreateView.url_name),
    path('user/<int:pk>/detail/', UserFiduciaDetailView.as_view(), name=UserFiduciaDetailView.url_name),

    path('user/basic/<int:pk>/update/', UserBasicInfoUpdateView.as_view(), name=UserBasicInfoUpdateView.url_name),
    path('user/documental/<int:pk>/update/', UserDocumentUpdateView.as_view(), name=UserDocumentUpdateView.url_name),

    path('user/residencial/<int:pk>/update/', UserResidentialUpdateView.as_view(), name=UserResidentialUpdateView.url_name),
    path('user/residencial/<int:pk>/create/', UserResidentialCreateView.as_view(), name=UserResidentialCreateView.url_name),

    path('user/workplace/<int:pk>/update/', UserWorkplaceUpdateView.as_view(), name=UserWorkplaceUpdateView.url_name),
    path('user/workplace/<int:pk>/create/', UserWorkplaceCreateView.as_view(), name=UserWorkplaceCreateView.url_name),

    
    
]