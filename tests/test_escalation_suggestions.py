import pytest
from django.utils import timezone


@pytest.mark.django_db
@pytest.mark.parametrize(
    "degree,n,expected",
    [
        # Degree 1: n=1..4 and >4
        (1, 1, ["VERBAL_NOTICE"]),
        (1, 2, ["WRITTEN_NOTICE"]),
        (1, 3, ["WRITTEN_WARNING", "COUNSELING_SESSION"]),
        (1, 4, ["BEHAVIOR_CONTRACT"]),
        (1, 5, ["BEHAVIOR_CONTRACT"]),
        # Degree 2: n=1..3 and >3
        (2, 1, ["WRITTEN_WARNING", "BEHAVIOR_CONTRACT"]),
        (2, 2, ["WRITTEN_WARNING", "GUARDIAN_MEETING"]),
        (2, 3, ["COMMITTEE_REFERRAL", "SUSPENSION"]),
        (2, 4, ["COMMITTEE_REFERRAL", "SUSPENSION"]),
        # Degree 3: n=1..2 and >2
        (3, 1, ["COMMITTEE_REFERRAL"]),
        (3, 2, ["SUSPENSION", "RESTITUTION"]),
        (3, 4, ["SUSPENSION", "RESTITUTION"]),
        # Degree 4: any n -> fixed set
        (4, 1, ["COMMITTEE_REFERRAL", "EXTERNAL_NOTIFICATION"]),
        (4, 2, ["COMMITTEE_REFERRAL", "EXTERNAL_NOTIFICATION"]),
        (4, 4, ["COMMITTEE_REFERRAL", "EXTERNAL_NOTIFICATION"]),
        (4, 10, ["COMMITTEE_REFERRAL", "EXTERNAL_NOTIFICATION"]),
    ],
)
def test_suggest_actions_mapping_matches_policy(degree, n, expected):
    from django.apps import apps
    from discipline.models import BehaviorLevel, Violation, Incident
    from discipline.serializers import suggest_actions_for

    # Prepare student
    Student = apps.get_model("school", "Student")
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب اختبار"
    student = Student.objects.create(**s_kwargs)

    # Prepare violation & level
    lvl, _ = BehaviorLevel.objects.get_or_create(code=degree, defaults={"name": f"درجة {degree}", "description": ""})
    viol, _ = Violation.objects.get_or_create(
        code=f"MAP-TST-{degree}",
        defaults={
            "level": lvl,
            "category": "اختبار خريطة",
            "description": "",
            "default_actions": [],
            "default_sanctions": [],
            "severity": degree,
            "requires_committee": degree >= 3,
            "policy": {"window_days": 365},
        },
    )

    # Prepare a minimal reporter user (required FK)
    from django.contrib.auth import get_user_model

    reporter = get_user_model().objects.create_user(username=f"rep_map_{degree}_{n}", password="x")

    # Create prior incidents inside window so that repeat_index becomes n
    base = timezone.now()
    for i in range(max(0, n - 1)):
        Incident.objects.create(
            violation=viol,
            student=student,
            reporter=reporter,
            occurred_at=base - timezone.timedelta(minutes=(i + 1)),
            location="L",
            narrative="prev",
            status="open",
            severity=viol.severity,
            committee_required=viol.requires_committee,
        )

    # Create current incident
    # لضمان عدم تساوي occurred_at استخدم الآن
    inc = Incident(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=timezone.now(),
        location="L",
        narrative="now",
        status="open",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )
    # لا حاجة لحفظ السجل الحالي لحساب التكرار (يُحسب كعدد السابق + 1)

    got = suggest_actions_for(inc)
    assert got == expected


@pytest.mark.django_db
def test_compute_repeat_index_respects_policy_window_over_env(settings):
    from django.apps import apps
    from discipline.models import BehaviorLevel, Violation, Incident
    from discipline.serializers import compute_repeat_index

    # Force global repeat window to a large number but set violation.policy.window_days to 10
    settings.DISCIPLINE_REPEAT_WINDOW_D = 365

    Student = apps.get_model("school", "Student")
    s_kwargs = {}
    if "full_name" in {f.name for f in Student._meta.get_fields()}:
        s_kwargs["full_name"] = "طالب اختبار"
    student = Student.objects.create(**s_kwargs)

    lvl, _ = BehaviorLevel.objects.get_or_create(code=2, defaults={"name": "الدرجة الثانية", "description": ""})
    viol, _ = Violation.objects.get_or_create(
        code="WIN-TST-2",
        defaults={
            "level": lvl,
            "category": "اختبار نافذة",
            "description": "",
            "default_actions": [],
            "default_sanctions": [],
            "severity": 2,
            "requires_committee": False,
            "policy": {"window_days": 10},
        },
    )

    now = timezone.now()
    # Prepare reporter
    from django.contrib.auth import get_user_model

    reporter = get_user_model().objects.create_user(username="rep_win", password="x")

    # Prior -5 days (inside policy window)
    Incident.objects.create(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=now - timezone.timedelta(days=5),
        location="L",
        narrative="inside",
        status="open",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )
    # Prior -15 days (outside 10-day policy window)
    Incident.objects.create(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=now - timezone.timedelta(days=15),
        location="L",
        narrative="outside",
        status="open",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )

    inc = Incident(
        violation=viol,
        student=student,
        reporter=reporter,
        occurred_at=now,
        location="L",
        narrative="current",
        status="open",
        severity=viol.severity,
        committee_required=viol.requires_committee,
    )

    # Only one prior within 10 days -> repeat_index should be 2
    assert compute_repeat_index(inc) == 2


def test_suggest_actions_handles_missing_occurred_at_and_unknown_degree():
    from types import SimpleNamespace
    from discipline.serializers import suggest_actions_for

    # Unknown degree -> []
    ns0 = SimpleNamespace(severity=0, occurred_at=None, violation=None, student_id=None, violation_id=None)
    assert suggest_actions_for(ns0) == []

    # Degree 1 with missing occurred_at -> treated as n=1
    ns1 = SimpleNamespace(severity=1, occurred_at=None, violation=None, student_id=None, violation_id=None)
    assert suggest_actions_for(ns1) == ["VERBAL_NOTICE"]
