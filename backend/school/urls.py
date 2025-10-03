from django.urls import path
from .views import teacher_loads_dashboard

urlpatterns = [
    path("loads/", teacher_loads_dashboard, name="teacher_loads_dashboard"),
]
