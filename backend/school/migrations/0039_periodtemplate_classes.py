from django.db import migrations, models


def populate_classes_from_wings(apps, schema_editor):
    PeriodTemplate = apps.get_model("school", "PeriodTemplate")
    Class = apps.get_model("school", "Class")
    # For each template linked to wings, link all classes that belong to those wings
    for tpl in PeriodTemplate.objects.all():
        try:
            wing_ids = list(tpl.wings.values_list("id", flat=True))
        except Exception:
            wing_ids = []
        if not wing_ids:
            continue
        class_ids = list(Class.objects.filter(wing_id__in=wing_ids).values_list("id", flat=True))
        if not class_ids:
            continue
        try:
            # Using through model via add(*ids) may be heavy but acceptable for migration scale
            tpl.classes.add(*class_ids)
        except Exception:
            # In case of bulk add issues (database limits), fallback to chunking
            for cid in class_ids:
                try:
                    tpl.classes.add(cid)
                except Exception:
                    pass


def noop_reverse(apps, schema_editor):
    # No reverse population (safe to ignore)
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("school", "0038_periodtemplate_wings"),
    ]

    operations = [
        migrations.AddField(
            model_name="periodtemplate",
            name="classes",
            field=models.ManyToManyField(
                blank=True,
                help_text="الفصول التي ينطبق عليها هذا القالب مباشرةً.",
                related_name="period_templates",
                to="school.class",
            ),
        ),
        migrations.RunPython(populate_classes_from_wings, noop_reverse),
    ]
