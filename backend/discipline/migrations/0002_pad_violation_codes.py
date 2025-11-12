from __future__ import annotations

from django.db import migrations
import re


def normalize(code: str) -> str:
    """Convert codes like '1-1' to '1-01'. Leave codes already like '4-09' as-is.
    Only affects patterns digits-digits. Other formats remain unchanged.
    """
    if not code:
        return code
    m = re.match(r"^(\d+)-(\d+)$", code)
    if not m:
        return code
    left, right = m.group(1), m.group(2)
    try:
        return f"{left}-{int(right):02d}"
    except ValueError:
        return code


def forwards(apps, schema_editor):
    Violation = apps.get_model("discipline", "Violation")
    # Iterate over all violations and normalize code
    for v in Violation.objects.all().only("id", "code"):
        new_code = normalize(v.code)
        if new_code != v.code:
            # To avoid potential unique collisions, if a collision occurs just skip update for that row
            try:
                Violation.objects.filter(pk=v.pk).update(code=new_code)
            except Exception:
                # In rare case of conflict, leave as-is; admin can resolve manually
                pass


def backwards(apps, schema_editor):
    # Best-effort reverse: strip a single leading zero from the right side when present
    Violation = apps.get_model("discipline", "Violation")
    for v in Violation.objects.all().only("id", "code"):
        code = v.code or ""
        m = re.match(r"^(\d+)-(\d{2,})$", code)
        if not m:
            continue
        left, right = m.group(1), m.group(2)
        # If right has leading zero and length >= 2, remove one leading zero
        if right.startswith("0"):
            new_code = f"{left}-{int(right)}"  # int will drop leading zeros
            try:
                Violation.objects.filter(pk=v.pk).update(code=new_code)
            except Exception:
                pass


class Migration(migrations.Migration):
    dependencies = [
        ("discipline", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
