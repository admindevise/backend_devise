from django.urls import path
from .views import Dashboard1View


urlpatterns = [
    # ============================= Templates Views ============================
    path('', Dashboard1View.as_view(), name=Dashboard1View.url_name),
]