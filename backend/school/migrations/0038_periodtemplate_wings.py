from django.db import migrations, models


def populate_wings_from_scope(apps, schema_editor):
    PeriodTemplate = apps.get_model("school", "PeriodTemplate")
    Wing = apps.get_model("school", "Wing")
    # Map scope like 'wing-1'..'wing-5' to the wing with matching id or name
    for tpl in PeriodTemplate.objects.all():
        scope = (getattr(tpl, "scope", "") or "").strip().lower()
        if scope.startswith("wing-"):
            try:
                no = int(scope.split("-", 1)[1])
            except Exception:
                continue
            # Try by id first
            wing = Wing.objects.filter(id=no).first()
            if not wing:
                # Try by name equals the number as string or contains number
                wing = Wing.objects.filter(name__icontains=str(no)).first()
            if wing:
                try:
                    tpl.wings.add(wing)
                except Exception:
                    pass


def noop_reverse(apps, schema_editor):
    # No-op on reverse
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0037_exit_event_review_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="periodtemplate",
            name="wings",
            field=models.ManyToManyField(
                blank=True,
                help_text="الأجنحة التي ينطبق عليها هذا القالب. يحدد ذلك الفصول التابعة لهذه الأجنحة.",
                related_name="period_templates",
                to="school.wing",
            ),
        ),
        migrations.RunPython(populate_wings_from_scope, noop_reverse),
    ]
