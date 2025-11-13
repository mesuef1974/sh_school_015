from django.urls import path

from .views import (
    change_password,
    logout,
    me,
    create_approval_request,
    approve_approval_request,
    reject_approval_request,
    tasks_log,
    tasks_list,
    tasks_mine,
    task_update,
)

app_name = "school_api"

urlpatterns = [
    path("me/", me, name="me"),
    path("change_password/", change_password, name="change_password"),
    path("logout/", logout, name="logout"),
    path("approvals/", create_approval_request, name="approvals_create"),
    path("approvals/<int:id>/approve/", approve_approval_request, name="approvals_approve"),
    path("approvals/<int:id>/reject/", reject_approval_request, name="approvals_reject"),
    # Tasks logging APIs
    path("tasks/log/", tasks_log, name="tasks_log"),
    path("tasks/", tasks_list, name="tasks_list"),
    path("tasks/mine/", tasks_mine, name="tasks_mine"),
    path("tasks/<int:id>/", task_update, name="task_update"),
]
