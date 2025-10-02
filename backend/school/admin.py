from django.contrib import admin
from .models import Class, Student, Staff


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "grade", "section")
    search_fields = ("name",)
    list_filter = ("grade", "section")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("id", "sid", "full_name", "class_fk", "active")
    search_fields = ("sid", "full_name")
    list_filter = ("active", "class_fk")


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "role", "user")
    search_fields = ("full_name",)
    list_filter = ("role",)
