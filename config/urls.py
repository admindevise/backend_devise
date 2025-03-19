from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path

from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from .import settings
from apps.dashboard import urls as dashboard_urls
from apps.user import urls as user_urls
#APIREST URLS
from apps.info_residential import urls as user_info_residential_urls
from apps.info_workplace import urls as user_workplace_urls
from apps.info_financial import urls as user_info_financial_urls
from apps.druo import urls as druo_urls
from apps.fiducia import urls as fiducia_urls
from apps.info_socioeconomic import urls as user_socioeconomic_urls
from apps.sponsor_company import urls as company_urls
from apps.asset import urls as asset_urls
from apps.notaria import urls as notaria_urls
from apps.security import urls as security_urls
from apps.academia import urls as academia_urls

from apps.kaleido import urls as kaleido_urls
from apps.fund import urls as fund_urls
from apps.audit import urls as audit_urls

from rest_framework_simplejwt.views import ( TokenObtainPairView, TokenRefreshView )

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Devise API",
        default_version='v1',
        description="API para la plataforma Devise de gestión de activos y tokens",
        terms_of_service="",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    validators=['ssv']
)

urlpatterns = [
    path('admin/', admin.site.urls),

    #Include Auth urls
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    #Include Cities app Urls
    path('cities/', include('apps.cities.urls')),

    #Include dashboard app
    path('', include(dashboard_urls)),

    #Include User custom Urls
    path('user/', include(user_urls)),
    path('user/', include(user_info_residential_urls)), #Resident and Workplace info
    path('user/', include(user_workplace_urls)), #Resident and Workplace info
    path('user/', include(user_info_financial_urls)), #Resident and Workplace info
    path('user/', include(user_socioeconomic_urls)), #Socioeconimic info

    #Backoffice urls
    path('company/', include(company_urls)), #Company backoffice

    #Fiducia Urls
    path('fiducia/', include(fiducia_urls)), #Fiducia backoffice
    #Notaria Urls
    path('notaria/', include(notaria_urls)), #Notaria backoffice
    # Druo
    path('druo/', include(druo_urls)),

    #APIREST urls:
    path('asset/', include(asset_urls)),    # URLS de Assets
    path('sponsor/', include(company_urls)), #Company backoffice

    #Security Urls:
    path('security/', include(security_urls)),

    #Academia Urls:
    path('academia/', include(academia_urls)),


    #Kaleido Urls:
    path('kaleido/', include(kaleido_urls)),
    
    #Fund Urls
    path('fund/', include(fund_urls)),
    
    #Audit Urls
    path('audit/', include(audit_urls)),

    # #wee trust
    # path('weetrust/', include(weetrust_urls)),

    #Generic auth Views
    path('auth/login/',  auth_views.LoginView.as_view( template_name='adminlte/base/login.html' ), name='login'),
    path('auth/logout/', auth_views.logout_then_login, name='logout'),
    
    #Swagger Docs
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)