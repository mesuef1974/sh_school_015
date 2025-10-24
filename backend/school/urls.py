from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import (
    portal_home,
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
    teacher_week_matrix,
    api_timetable_add,
    api_timetable_move,
    teacher_week_compact,
    timetable_import_from_image,
    timetable_source_image,
    timetable_source_pdf,
    teacher_attendance_page,
    api_attendance_records,
    api_attendance_students,
    api_attendance_bulk_save,
    logout_to_login,
    root_router,
    wings_overview,
    wing_detail,
    wing_dashboard,
    assignments_vs_timetable,
    data_relations,
    data_db_audit,
)
from .api_relations import api_data_relations

urlpatterns = [
    # Auth routes (unified login/logout)
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="auth/login.html",
            redirect_authenticated_user=True,
            success_url=reverse_lazy("portal_home"),
        ),
        name="login",
    ),
    path("accounts/logout/", logout_to_login, name="logout"),
    # Root router: redirect based on auth state (prevents redirect loop)
    path("", root_router, name="home"),
    # Role-based portal
    path("portal/", portal_home, name="portal_home"),
    path("data/", data_overview, name="data_overview"),
    path("data/relations/", data_relations, name="data_relations"),
    path("data/audit/", data_db_audit, name="data_db_audit"),
    path("data/<str:table>/export", export_table_csv, name="data_export_csv"),
    path("data/<str:table>/", data_table_detail, name="data_table_detail"),
    path("loads/", teacher_loads_dashboard, name="teacher_loads_dashboard"),
    path("loads/matrix/", teacher_class_matrix, name="teacher_class_matrix"),
    path("loads/compare/", assignments_vs_timetable, name="assignments_vs_timetable"),
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
    # Teacher weekly timetable (interactive)
    path("timetable/teachers/", teacher_week_matrix, name="teacher_week_matrix"),
    path("timetable/teachers/compact/", teacher_week_compact, name="teacher_week_compact"),
    # Import timetable from image/pdf helper
    path(
        "timetable/import/from_image/",
        timetable_import_from_image,
        name="timetable_import_from_image",
    ),
    path(
        "timetable/import/source.jpg",
        timetable_source_image,
        name="timetable_source_image",
    ),
    path("timetable/import/source.pdf", timetable_source_pdf, name="timetable_source_pdf"),
    path("api/timetable/add/", api_timetable_add, name="api_timetable_add"),
    path("api/timetable/move/", api_timetable_move, name="api_timetable_move"),
    # Data relations API (live)
    path("api/data/relations", api_data_relations, name="api_data_relations"),
    # Attendance entry
    path("attendance/teacher/", teacher_attendance_page, name="teacher_attendance_page"),
    path("api/attendance/records", api_attendance_records, name="api_attendance_records"),
    path(
        "api/attendance/students",
        api_attendance_students,
        name="api_attendance_students",
    ),
    path(
        "api/attendance/bulk_save",
        api_attendance_bulk_save,
        name="api_attendance_bulk_save",
    ),
    # Wings pages
    path("wings/", wings_overview, name="wings_overview"),
    path("wings/<int:wing_id>/", wing_detail, name="wing_detail"),
    path("wing/dashboard/", wing_dashboard, name="wing_dashboard"),
]