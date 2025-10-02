from django.db import models
from django.contrib.auth.models import User


class Class(models.Model):
    name = models.CharField(max_length=100, unique=True)
    grade = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=10, blank=True)

    def __str__(self) -> str:
        return f"{self.name}"


class Student(models.Model):
    sid = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=200)
    class_fk = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, related_name="students"
    )
    dob = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.sid} - {self.full_name}"


class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    role = models.CharField(
        max_length=50,
        choices=[
            ("teacher", "Teacher"),
            ("admin", "Admin"),
            ("staff", "Staff"),
        ],
    )
    national_no = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    job_no = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    phone_no = models.CharField(max_length=30, blank=True)

    def __str__(self) -> str:
        return self.full_name
