from apps.asset.views.kaleido_views import CreateSmartContractToken, ReadTokenSmartContract
from apps.asset.views.minuta_escrituracion_views import CreateMinutaEscrituracionView, FeedbackMinutaCreateMessage, ListMessagesMinutaEscrituracionView, MinutaEscrituracionApprovedFiducia, MinutaEscrituracionApprovedPropietario, MinutaEscrituracionMessage
from apps.asset.views.tradicion_libertad_views import CreateTradicionLibertadView
from apps.asset.views.kpi_views import ApprovedKpiAssetAdmin, FeedbackKPICreate, ListMessagesKPIView, ReadKPIAssetView, SendKPIMsjSponsor, UpdateKPIAssetView

from .views.asset_views import (ApprovedAssetFiducia, CreateAssetView, FiduciaApprovedEncargoFiduciario, ListMessagesSponsorDeviseAssetView, ListSponsorToApprvedAssetView, 
                            UpdateAssetView, ListAssetView,
                            ListTipoProyectoView, ListCategoriaView,
                            ListOwnAssetView,
                            ListAssetApproveView,
                            ListAssetTipoProyecto,
                            #1.2 Documental asset info views
                            CreateDocumentalAssetView, UpdateDocumentalAssetView, ValidateAssetSponsorView,
                            #2. Aproved Asset Sponsor Admin Views
                            ListSponsorAssetView, RetrieveAssetView,
                            FeedbackActivoCreate, ApprovedSponsorAssetView, 
                            ApprovedAdminDeviseAssetView,
                            ListMessagesAssetView, SendAdminMsjSponsor,
                            ApprovedAssetAdmin,
                            
                            )
from .views.backoffice_views import (
                            #3 Admin check assets
                            DetailAdminAssetView, ListAdminAssetView, ListAdminAssetExportView, RetrySignDocument, SendToSignFiduciaDocument, UploadFiduciaDocument
                            )
from django.urls.conf import path


urlpatterns = [
    #URLS de Utiles
    path('list/categorias/', ListCategoriaView.as_view()),
    path('list/tipoproyecto/', ListTipoProyectoView.as_view()),
    path('list/tipoproyectoasset/', ListAssetTipoProyecto.as_view()),


    #Paso 1 Creacion y seleccion de Sponsor para Activos

        #Urls de Creacion Activo
    path('create/', CreateAssetView.as_view()),
    path('update/<int:pk>/', UpdateAssetView.as_view()),
    path('list/myassets/', ListOwnAssetView.as_view()),
    path('list/assets/', ListAssetApproveView.as_view()),
    path('list/all/', ListAssetView.as_view()),

        #URLs de Informacion Documental
    path('documental/create/<int:pk>/', CreateDocumentalAssetView.as_view()),
    path('documental/update/<int:pk>/', UpdateDocumentalAssetView.as_view()),

    #Paso 2.1 Visto bueno del Sponsor 
    path('admin/list/toaprovedsponsor/', ListSponsorToApprvedAssetView.as_view()), #Para ver los que Estan pendientes de aprobar del propietario
    path('admin/list/sponsor/', ListSponsorAssetView.as_view()),

    path('retrieve/<int:pk>/', RetrieveAssetView.as_view()),
    path('send/validation/sponsor/<int:pk>/', ValidateAssetSponsorView.as_view()), #Se envia aca para que cambie de estado el asset
    path('send/feedback/', FeedbackActivoCreate.as_view()),
    path('send/approved/sponsor/<int:pk>/', ApprovedSponsorAssetView.as_view()),

    #Paso 2.1 Respuesta del Propietario
    # path('send/feedback/', FeedbackActivoCreate.as_view()), <<< misma ruta
    # path('send/approved/sponsor/<int:pk>/', ApprovedSponsorAssetView.as_view()),
    path('list/feedback/messages/<int:pk>/', ListMessagesAssetView.as_view()), #Se envian solo mensajes Propietario-Sponsor

    #Paso 2.1 Visto bueno del AdminDevise
    # path('send/feedback/admindevise/', FeedbackActivoAdmindeviseCreate.as_view()),  # path('send/feedback/', FeedbackActivoCreate.as_view()), <<< misma ruta
    path('send/approved/admindevise/<int:pk>/', ApprovedAdminDeviseAssetView.as_view()),
    #Paso 2.2 Visto Bueno Admin DEVISE
    path('list/admin/assets/', ListAdminAssetView.as_view(), name=ListAdminAssetView.url_name),
    path('list/admin/assets/export/', ListAdminAssetExportView.as_view(), name=ListAdminAssetExportView.url_name),
    path('list/admin/detail/<int:pk>/', DetailAdminAssetView.as_view(), name=DetailAdminAssetView.url_name),
    path('list/admin/detail/message/', SendAdminMsjSponsor, name='send-admin-asset-message'),
    path('list/admin/approved/', ApprovedAssetAdmin, name='admin-asset-approved'),
    path('list/feedback/messages/admin/<int:pk>/', ListMessagesSponsorDeviseAssetView.as_view()), #Se envian solo mensajes Devise-Sponsor


    #Paso 3 Visto bueno de la Fiducia
    path('fiducia/approved/', ApprovedAssetFiducia, name='fiducia-asset-approved'),
    path('fiducia/load/fideicomiso/', UploadFiduciaDocument, name='fiducia-asset-load-fideicomiso' ),
    path('fiducia/requestsign/fideicomiso/', SendToSignFiduciaDocument, name='fiducia-send-to-sign-fideicomiso' ), #ACA subo el doc a Weetrust
    path('fideicomiso/retrybiometric/', RetrySignDocument, name='retry-sign-fideicomiso' ),

    #Paso 4 Sponsor nos envia la minuta de escrituración (aprobada) y se aprueba por los demas 

    path('sponsor/create/minutaescrituracion/', CreateMinutaEscrituracionView.as_view() ),
    path('minutaescrituracion/approved/fiducia/', MinutaEscrituracionApprovedFiducia, name='minuta-approved-fiducia'),
    path('minutaescrituracion/message/', MinutaEscrituracionMessage, name='minuta-new-message'),
    path('minutaescrituracion/list/messages/asset/<int:pk>/', ListMessagesMinutaEscrituracionView.as_view()),
    path('minutaescrituracion/api/message/', FeedbackMinutaCreateMessage.as_view(), name='minuta-api-new-message'),
    path('minutaescrituracion/<int:pk>/approved/propietario/', MinutaEscrituracionApprovedPropietario.as_view(), ),

    #Paso 9 Sponsor nos envia certificado tradicion y Libertad
    path('<int:pk>/sponsor/create/certtradicionlibertad/', CreateTradicionLibertadView.as_view() ),

    #Paso 10  La fiducia valida que el encargo fiduciario se encuentra activo.

    path('fiducia/encargofiduciario/approved/', FiduciaApprovedEncargoFiduciario, name='fiducia-encargofiduciario-approved'),

    #Paso 11 Sponsor diligencia los KPI de los Activos DEVISE LO APRUEBA

    path('update/kpi/<int:pk>/', UpdateKPIAssetView.as_view()),
    path('read/kpi/<int:pk>/', ReadKPIAssetView.as_view()),
    path('admin/approved/kpi/', ApprovedKpiAssetAdmin, name='admin-approved-kpi'),
    path('admin/sendfeedback/kpi/', SendKPIMsjSponsor, name='send-admin-kpi-message'),
    path('sponsor/sendfeedback/kpi/api/', FeedbackKPICreate.as_view()),
    path('kpi/list/messages/asset/<int:pk>/', ListMessagesKPIView.as_view()),

    
    #Paso 12 ADMIN DEVISE ENVIA EL ID DEL CONTRATO
    path('kaleido/create/smartcontract/', CreateSmartContractToken, name='create-smart-contract'),
    path('kaleido/read/smartcontract/', ReadTokenSmartContract, name='read-token-smartcontract'),



    
]