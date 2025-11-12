from django.urls import path

from .views import (
    change_password,
    logout,
    me,
    create_approval_request,
    approve_approval_request,
)

app_name = "school_api"

urlpatterns = [
    path("me/", me, name="me"),
    path("change_password/", change_password, name="change_password"),
    path("logout/", logout, name="logout"),
    path("approvals/", create_approval_request, name="approvals_create"),
    path("approvals/<int:id>/approve/", approve_approval_request, name="approvals_approve"),
]
