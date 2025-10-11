from django.urls import path
from .views import (
    teacher_loads_dashboard,
    data_overview,
    data_table_detail,
    export_table_csv,
    job_status,
    teacher_class_matrix,
    export_assignments_xlsx,
    export_matrix_xlsx,
    export_assignments_pdf,
    export_matrix_pdf,
)

urlpatterns = [
    path("", data_overview, name="home"),
    path("data/", data_overview, name="data_overview"),
    path("data/<str:table>/export", export_table_csv, name="data_export_csv"),
    path("data/<str:table>/", data_table_detail, name="data_table_detail"),
    path("loads/", teacher_loads_dashboard, name="teacher_loads_dashboard"),
    path("loads/matrix/", teacher_class_matrix, name="teacher_class_matrix"),
    # New exports
    path(
        "loads/export/assignments.xlsx",
        export_assignments_xlsx,
        name="export_assignments_xlsx",
    ),
    path("loads/matrix/export.xlsx", export_matrix_xlsx, name="export_matrix_xlsx"),
    path(
        "loads/export/assignments.pdf",
        export_assignments_pdf,
        name="export_assignments_pdf",
    ),
    path("loads/matrix/export.pdf", export_matrix_pdf, name="export_matrix_pdf"),
    path("jobs/<str:job_id>/", job_status, name="job_status"),
]
