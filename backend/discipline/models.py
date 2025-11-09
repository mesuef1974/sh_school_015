from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models


class BehaviorLevel(models.Model):
    code = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Behavior Level"
        verbose_name_plural = "Behavior Levels"
        ordering = ("code",)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code} - {self.name}"


class Violation(models.Model):
    level = models.ForeignKey(BehaviorLevel, on_delete=models.PROTECT, related_name="violations")
    code = models.CharField(max_length=16, unique=True)
    category = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    default_actions = models.JSONField(default=list)
    default_sanctions = models.JSONField(default=list)
    severity = models.PositiveSmallIntegerField()
    requires_committee = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Violation"
        verbose_name_plural = "Violations"
        ordering = ("severity", "code")
        permissions = (("access", "Can access discipline module"),)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.category}"


class Incident(models.Model):
    STATUS_CHOICES = (
        ("open", "Open"),
        ("under_review", "Under Review"),
        ("closed", "Closed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    violation = models.ForeignKey(Violation, on_delete=models.PROTECT, related_name="incidents")
    student = models.ForeignKey("school.Student", on_delete=models.PROTECT, related_name="incidents")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_incidents")
    occurred_at = models.DateTimeField()
    location = models.CharField(max_length=128, blank=True)
    narrative = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open")
    severity = models.PositiveSmallIntegerField()
    committee_required = models.BooleanField(default=False)
    # Workflow tracking fields
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_incidents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_incidents",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    actions_applied = models.JSONField(default=list, blank=True)
    sanctions_applied = models.JSONField(default=list, blank=True)
    escalated_due_to_repeat = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        ordering = ("-occurred_at",)
        permissions = (
            ("incident_create", "Can create incident"),
            ("incident_submit", "Can submit incident for review"),
            ("incident_review", "Can review incident (approve/return)"),
            ("incident_escalate", "Can escalate incident"),
            ("incident_notify_guardian", "Can notify guardian for incident"),
            ("incident_close", "Can close incident"),
        )

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.violation.code} @ {self.occurred_at:%Y-%m-%d}"
