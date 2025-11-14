from django.db import models
from django.conf import settings


class Grade(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "صف"
        verbose_name_plural = "صفوف"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "مادة"
        verbose_name_plural = "مواد"


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
        verbose_name = "شعبة"
        verbose_name_plural = "شُعب"

    def __str__(self):
        return f"{self.grade.name} - {self.name}"
