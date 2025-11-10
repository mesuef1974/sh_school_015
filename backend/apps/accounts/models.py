from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = (
        ("admin", "Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("parent", "Parent"),
    )

    role = models.CharField(max_length=10, choices=ROLES)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
