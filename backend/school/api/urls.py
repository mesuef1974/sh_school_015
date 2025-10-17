from django.urls import path
from .views import me, change_password, logout

app_name = "school_api"

urlpatterns = [
    path("me/", me, name="me"),
    path("change_password/", change_password, name="change_password"),
    path("logout/", logout, name="logout"),
]
