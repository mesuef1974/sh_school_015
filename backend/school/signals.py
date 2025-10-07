from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Student, Class


@receiver(pre_save, sender=Student)
def _capture_old_class(sender, instance: Student, **kwargs):
    if instance.pk:
        try:
            old = Student.objects.only("class_fk_id").get(pk=instance.pk)
            instance._old_class_fk_id = old.class_fk_id
        except Student.DoesNotExist:
            instance._old_class_fk_id = None
    else:
        instance._old_class_fk_id = None


def _adjust_class_count(class_id: int, delta: int):
    if class_id is None:
        return
    # Use F expression to avoid race conditions
    from django.db.models import F

    Class.objects.filter(id=class_id).update(students_count=F("students_count") + delta)


@receiver(post_save, sender=Student)
def _student_saved(sender, instance: Student, created: bool, **kwargs):
    new_class_id = instance.class_fk_id
    old_class_id = getattr(instance, "_old_class_fk_id", None)

    if created:
        if new_class_id:
            _adjust_class_count(new_class_id, +1)
        return

    # Updated existing
    if old_class_id != new_class_id:
        if old_class_id:
            _adjust_class_count(old_class_id, -1)
        if new_class_id:
            _adjust_class_count(new_class_id, +1)


@receiver(post_delete, sender=Student)
def _student_deleted(sender, instance: Student, **kwargs):
    class_id = instance.class_fk_id
    if class_id:
        _adjust_class_count(class_id, -1)
