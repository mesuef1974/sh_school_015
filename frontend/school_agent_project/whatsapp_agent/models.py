from django.db import models
from django.contrib.postgres.fields import JSONField


class Person(models.Model):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("parent", "Parent"),
        ("teacher", "Teacher"),
        ("admin", "Admin"),
        ("visitor", "Visitor"),
        ("moe", "MoE_Staff"),
    ]
    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    student_id = models.CharField(max_length=50, blank=True, null=True)
    national_id = models.CharField(max_length=20, blank=True, null=True)
    related_student = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    consents = JSONField(default=dict, blank=True)  # consent flags
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class ReplyTemplate(models.Model):
    intent = models.CharField(max_length=100)
    trigger_phrases = JSONField(default=list, blank=True)  # list of keywords
    text_template = models.TextField()
    media_url = models.TextField(blank=True, null=True)
    buttons = JSONField(default=list, blank=True)  # quick replies
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.intent} - {self.text_template[:30]}"


class MessageLog(models.Model):
    DIRECTION = [("incoming", "incoming"), ("outgoing", "outgoing")]
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=20)
    direction = models.CharField(max_length=10, choices=DIRECTION)
    content = models.TextField()
    intent = models.CharField(max_length=100, blank=True, null=True)
    confidence = models.FloatField(null=True, blank=True)
    provider_meta = JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StudentResult(models.Model):
    student_id = models.CharField(max_length=50)
    year = models.IntegerField()
    term = models.CharField(max_length=20)
    total = models.DecimalField(max_digits=6, decimal_places=2)
    grade = models.CharField(max_length=20)
    details = JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AttendanceRecord(models.Model):
    student_id = models.CharField(max_length=50)
    date = models.DateField()
    status = models.CharField(max_length=20)  # present/absent/late
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BehaviorReport(models.Model):
    student_id = models.CharField(max_length=50)
    date = models.DateField()
    report = models.TextField()
    severity = models.CharField(max_length=20, default="normal")
    created_at = models.DateTimeField(auto_now_add=True)


class EscalationTicket(models.Model):
    original_message = models.ForeignKey(MessageLog, on_delete=models.CASCADE)
    assigned_to = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, default="open")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
