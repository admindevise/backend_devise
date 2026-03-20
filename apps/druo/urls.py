from .views import BanksListView, AccountTypeListView, AccountSubtypeListView

from django.urls.conf import path


urlpatterns = [
    path('fi/<int:fi_id>/banks/', BanksListView.as_view()),
    path('fi/<int:fi_id>/account/types/', AccountTypeListView.as_view()),
    path('fi/<int:fi_id>/account/subtypes/', AccountSubtypeListView.as_view()),

]