from .views import BanksListView, AccountTypeListView, AccountSubtypeListView

from django.urls.conf import path


urlpatterns = [
    path('banks/', BanksListView.as_view()),
    path('account/types/', AccountTypeListView.as_view()),
    path('account/subtypes/', AccountSubtypeListView.as_view()),

]