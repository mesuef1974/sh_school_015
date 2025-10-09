from django.urls import path
from .views import (
    teacher_loads_dashboard,
    data_overview,
    data_table_detail,
    export_table_csv,
)

urlpatterns = [
    path("", data_overview, name="home"),
    path("data/", data_overview, name="data_overview"),
    path("data/<str:table>/export", export_table_csv, name="data_export_csv"),
    path("data/<str:table>/", data_table_detail, name="data_table_detail"),
    path("loads/", teacher_loads_dashboard, name="teacher_loads_dashboard"),
]
