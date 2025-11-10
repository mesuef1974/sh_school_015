from django.db import models
from django.conf import settings


class Grade(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Class(models.Model):
    name = models.CharField(max_length=50)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(Subject)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={"role": "teacher"},
    )

    class Meta:
        verbose_name_plural = "Classes"

    def __str__(self):
        return f"{self.grade.name} - {self.name}"
