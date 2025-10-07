from django.urls import path
from .views import (
    teacher_loads_dashboard,
    data_overview,
    data_table_detail,
    calendar_list,
    calendar_template_detail,
    timetable_select,
    timetable_class_week,
)

urlpatterns = [
    path("", data_overview, name="home"),
    path("data/", data_overview, name="data_overview"),
    path("data/<str:table>/", data_table_detail, name="data_table_detail"),
    path("loads/", teacher_loads_dashboard, name="teacher_loads_dashboard"),
    path("calendar/", calendar_list, name="calendar_list"),
    path("calendar/<int:pk>/", calendar_template_detail, name="calendar_template_detail"),
    path("timetable/", timetable_select, name="timetable_select"),
    path(
        "timetable/<int:class_id>/<int:template_id>/",
        timetable_class_week,
        name="timetable_class_week",
    ),
]
