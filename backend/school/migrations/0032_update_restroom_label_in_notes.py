from django.db import migrations


def forwards(apps, schema_editor):
    AttendanceRecord = apps.get_model("school", "AttendanceRecord")
    # Update notes for excused records where the Arabic word حمام appears, replace with دورة المياه
    # Use queryset update in chunks to be DB-agnostic
    qs = AttendanceRecord.objects.filter(status="excused").filter(note__icontains="حمام")
    # Iterate to avoid REPLACE portability issues across DB backends
    for rec in qs.iterator(chunk_size=1000):
        try:
            new_note = (rec.note or "").replace("حمام", "دورة المياه")
            if new_note != rec.note:
                rec.note = new_note
                rec.save(update_fields=["note"])
        except Exception:
            # Best-effort; skip problematic rows
            pass


def backwards(apps, schema_editor):
    AttendanceRecord = apps.get_model("school", "AttendanceRecord")
    qs = AttendanceRecord.objects.filter(status="excused").filter(note__icontains="دورة المياه")
    for rec in qs.iterator(chunk_size=1000):
        try:
            old_note = (rec.note or "").replace("دورة المياه", "حمام")
            if old_note != rec.note:
                rec.note = old_note
                rec.save(update_fields=["note"])
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0031_attendance_add_note"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
