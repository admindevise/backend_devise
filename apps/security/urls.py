from django.urls import  path
from .views.useradmin import ConfigRulesSecurityView, UnlockAttemptsView, UserLockedListView


urlpatterns = [
    #============================= Templates Views Usuarios =================================

    path('view/lock/list/', UserLockedListView.as_view(), name=UserLockedListView.url_name),
    path('unlock/attempts/', UnlockAttemptsView.as_view(), name=UnlockAttemptsView.url_name),
    path('configure/rules/<int:pk>/', ConfigRulesSecurityView.as_view(), name=ConfigRulesSecurityView.url_name),

]