from django.urls import  path

from apps.notaria.views.notaria_assets import DetailAssetNotariaView, ListAssetNotariaView, MinutaEscrituracionApprovedNotaria, MinutaEscrituracionNotarioMessage, TramitarNuevaEscritura, UploadNotariaEscritura
from .views.notaria_views import ( NotariaListView, NotariaDetailView,
                                NotariaUpdateView,
                                NotariaListExportView, NotariaCreateView,
                                )

from .views.user_notaria import (UserNotariaListView, UserNotariaCreateView,
                                UserNotariaDetailView, UserBasicInfoUpdateView,
                                UserDocumentUpdateView, UserResidentialUpdateView,
                                UserResidentialCreateView, UserWorkplaceUpdateView, 
                                UserWorkplaceCreateView, 
                                )


urlpatterns = [
   
    #============================= Backoffice Views Notaria =================================
    path('create/', NotariaCreateView.as_view(), name=NotariaCreateView.url_name),
    path('list/', NotariaListView.as_view(), name=NotariaListView.url_name),
    path('<int:pk>/detail/', NotariaDetailView.as_view(), name=NotariaDetailView.url_name),
    path('<int:pk>/update/', NotariaUpdateView.as_view(), name=NotariaUpdateView.url_name),
    path('export/list/', NotariaListExportView.as_view(), name=NotariaListExportView.url_name),

    #============================= Templates Usuarios NOTARIA =================================
    path('user/viewlist/', UserNotariaListView.as_view(), name=UserNotariaListView.url_name),
    path('user/create/', UserNotariaCreateView.as_view(), name=UserNotariaCreateView.url_name),
    path('user/<int:pk>/detail/', UserNotariaDetailView.as_view(), name=UserNotariaDetailView.url_name),

    path('user/basic/<int:pk>/update/', UserBasicInfoUpdateView.as_view(), name=UserBasicInfoUpdateView.url_name),
    path('user/documental/<int:pk>/update/', UserDocumentUpdateView.as_view(), name=UserDocumentUpdateView.url_name),

    path('user/residencial/<int:pk>/update/', UserResidentialUpdateView.as_view(), name=UserResidentialUpdateView.url_name),
    path('user/residencial/<int:pk>/create/', UserResidentialCreateView.as_view(), name=UserResidentialCreateView.url_name),

    path('user/workplace/<int:pk>/update/', UserWorkplaceUpdateView.as_view(), name=UserWorkplaceUpdateView.url_name),
    path('user/workplace/<int:pk>/create/', UserWorkplaceCreateView.as_view(), name=UserWorkplaceCreateView.url_name),

    #============================= Templates Assets para la  NOTARIA =================================
    path('list/assets/', ListAssetNotariaView.as_view(), name=ListAssetNotariaView.url_name),
    path('detail/asset/<int:pk>/', DetailAssetNotariaView.as_view(), name=DetailAssetNotariaView.url_name),
    path('minutaescrituracion/approved/notaria/', MinutaEscrituracionApprovedNotaria, name='minuta-approved-notaria'),
    path('minutaescrituracion/message/notaria/', MinutaEscrituracionNotarioMessage, name='minuta-notario-message'),
    path('tramitar/nueva/escritura/', TramitarNuevaEscritura, name='tramitar-nueva-escritura'),
    path('upload/escritura/', UploadNotariaEscritura, name='notaria-upload-escritura' ),





    
]