from django.urls import path
from .views import (
    teacher_loads_dashboard,
    data_overview,
    data_table_detail,
    export_table_csv,
    job_status,
    teacher_class_matrix,
)

urlpatterns = [
    path("", data_overview, name="home"),
    path("data/", data_overview, name="data_overview"),
    path("data/<str:table>/export", export_table_csv, name="data_export_csv"),
    path("data/<str:table>/", data_table_detail, name="data_table_detail"),
    path("loads/", teacher_loads_dashboard, name="teacher_loads_dashboard"),
    path("loads/matrix/", teacher_class_matrix, name="teacher_class_matrix"),
    path("jobs/<str:job_id>/", job_status, name="job_status"),
]
