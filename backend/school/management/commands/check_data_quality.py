"""
Management command to check and report on data quality
Usage: python manage.py check_data_quality [--fix] [--verbose]
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from school.models import Student, Staff, Class, AttendanceRecord, ExitEvent
from school.validators import (
    validate_saudi_national_id,
    validate_phone_number,
)


class Command(BaseCommand):
    help = "Check data quality and report issues"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix", action="store_true", help="Attempt to fix issues automatically"
        )
        parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    def handle(self, *args, **options):
        self.fix_mode = options["fix"]
        self.verbose = options["verbose"]

        self.stdout.write(self.style.SUCCESS("\n📊 Data Quality Report\n"))
        self.stdout.write("=" * 70)

        if self.fix_mode:
            self.stdout.write(
                self.style.WARNING("🔧 Fix mode enabled - issues will be corrected\n")
            )

        # Run all checks
        self.check_student_data()
        self.check_staff_data()
        self.check_class_data()
        self.check_attendance_data()
        self.check_exit_events()

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("✓ Data quality check complete\n"))

    def check_student_data(self):
        """Check student data quality"""
        self.stdout.write(self.style.HTTP_INFO("\n👨‍🎓 STUDENT DATA"))
        self.stdout.write("-" * 70)

        total = Student.objects.count()
        active = Student.objects.filter(active=True).count()
        self.stdout.write(f"Total students: {total} (Active: {active})")

        # Check for missing critical fields
        issues = []

        # Missing national IDs
        missing_national = Student.objects.filter(
            Q(national_no__isnull=True) | Q(national_no=""), active=True
        ).count()
        if missing_national > 0:
            issues.append(f"  ⚠ {missing_national} students missing national ID")

        # Invalid national IDs
        invalid_national = 0
        for student in Student.objects.exclude(national_no="").exclude(national_no__isnull=True):
            try:
                validate_saudi_national_id(student.national_no)
            except Exception:
                invalid_national += 1
                if self.verbose:
                    self.stdout.write(
                        f'    - {student.sid}: Invalid national ID "{student.national_no}"'
                    )
        if invalid_national > 0:
            issues.append(f"  ⚠ {invalid_national} students with invalid national ID format")

        # Missing parent contact
        missing_parent = Student.objects.filter(
            Q(parent_phone="") | Q(parent_phone__isnull=True), active=True
        ).count()
        if missing_parent > 0:
            issues.append(f"  ⚠ {missing_parent} students missing parent phone")

        # Invalid phone numbers
        invalid_phones = 0
        for student in Student.objects.exclude(phone_no="").exclude(phone_no__isnull=True):
            try:
                validate_phone_number(student.phone_no)
            except Exception:
                invalid_phones += 1
        if invalid_phones > 0:
            issues.append(f"  ⚠ {invalid_phones} students with invalid phone format")

        # Students without class
        no_class = Student.objects.filter(class_fk__isnull=True, active=True).count()
        if no_class > 0:
            issues.append(f"  ⚠ {no_class} active students not assigned to any class")

        # Duplicate names
        duplicates = (
            Student.objects.values("full_name").annotate(count=Count("id")).filter(count__gt=1)
        )
        if duplicates.count() > 0:
            issues.append(f"  ⚠ {duplicates.count()} duplicate student names found")

        # Age inconsistencies
        age_issues = (
            Student.objects.filter(active=True)
            .exclude(dob__isnull=True)
            .exclude(Q(age__gte=5) & Q(age__lte=25))
            .count()
        )
        if age_issues > 0:
            issues.append(f"  ⚠ {age_issues} students with unusual ages (< 5 or > 25)")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.WARNING(issue))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ No issues found"))

    def check_staff_data(self):
        """Check staff data quality"""
        self.stdout.write(self.style.HTTP_INFO("\n👨‍🏫 STAFF DATA"))
        self.stdout.write("-" * 70)

        total = Staff.objects.count()
        with_user = Staff.objects.exclude(user__isnull=True).count()
        self.stdout.write(f"Total staff: {total} (With user account: {with_user})")

        issues = []

        # Staff without user account (should they have one?)
        teachers = Staff.objects.filter(role="teacher", user__isnull=True).count()
        if teachers > 0:
            issues.append(f"  ⚠ {teachers} teachers without user accounts")

        # Missing contact info
        no_phone = Staff.objects.filter(Q(phone_no="") | Q(phone_no__isnull=True)).count()
        if no_phone > 0:
            issues.append(f"  ⚠ {no_phone} staff members missing phone number")

        no_email = Staff.objects.filter(Q(email="") | Q(email__isnull=True)).count()
        if no_email > 0:
            issues.append(f"  ⚠ {no_email} staff members missing email")

        # Invalid national IDs
        invalid_national = 0
        for staff in Staff.objects.exclude(national_no=""):
            try:
                validate_saudi_national_id(staff.national_no)
            except Exception:
                invalid_national += 1
        if invalid_national > 0:
            issues.append(f"  ⚠ {invalid_national} staff with invalid national ID format")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.WARNING(issue))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ No issues found"))

    def check_class_data(self):
        """Check class data quality"""
        self.stdout.write(self.style.HTTP_INFO("\n🏫 CLASS DATA"))
        self.stdout.write("-" * 70)

        total = Class.objects.count()
        self.stdout.write(f"Total classes: {total}")

        issues = []

        # Classes with incorrect student counts
        for cls in Class.objects.all():
            actual = cls.students.filter(active=True).count()
            if cls.students_count != actual:
                issues.append(
                    f"  ⚠ Class {cls.name}: count mismatch (DB: {cls.students_count}, Actual: {actual})"
                )
                if self.fix_mode:
                    cls.students_count = actual
                    cls.save(update_fields=["students_count"])
                    self.stdout.write(self.style.SUCCESS(f"    ✓ Fixed count for {cls.name}"))

        # Classes without wing assignment
        no_wing = Class.objects.filter(wing__isnull=True).count()
        if no_wing > 0:
            issues.append(f"  ⚠ {no_wing} classes not assigned to a wing")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.WARNING(issue))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ No issues found"))

    def check_attendance_data(self):
        """Check attendance data quality"""
        self.stdout.write(self.style.HTTP_INFO("\n📝 ATTENDANCE DATA"))
        self.stdout.write("-" * 70)

        total = AttendanceRecord.objects.count()
        self.stdout.write(f"Total attendance records: {total}")

        issues = []

        # Records with late_minutes but status not 'late'
        inconsistent = (
            AttendanceRecord.objects.filter(late_minutes__gt=0).exclude(status="late").count()
        )
        if inconsistent > 0:
            issues.append(f'  ⚠ {inconsistent} records with late_minutes > 0 but status ≠ "late"')

        # Records with status=late but late_minutes=0
        inconsistent2 = AttendanceRecord.objects.filter(status="late", late_minutes=0).count()
        if inconsistent2 > 0:
            issues.append(f'  ⚠ {inconsistent2} records with status="late" but late_minutes=0')

        # Exit permission without exit times
        exit_no_times = AttendanceRecord.objects.filter(
            status="excused", exit_left_at__isnull=True
        ).count()
        if exit_no_times > 0:
            issues.append(f"  ⚠ {exit_no_times} exit permissions without exit_left_at timestamp")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.WARNING(issue))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ No issues found"))

    def check_exit_events(self):
        """Check exit event data quality"""
        self.stdout.write(self.style.HTTP_INFO("\n🚪 EXIT EVENTS"))
        self.stdout.write("-" * 70)

        total = ExitEvent.objects.count()
        open_events = ExitEvent.objects.filter(returned_at__isnull=True).count()
        self.stdout.write(f"Total exit events: {total} (Currently open: {open_events})")

        issues = []

        # Long-duration exits (> 2 hours = 7200 seconds)
        long_exits = ExitEvent.objects.filter(duration_seconds__gt=7200).count()
        if long_exits > 0:
            issues.append(f"  ⚠ {long_exits} exit events with duration > 2 hours")

        # Very old unclosed exits
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=7)
        old_open = ExitEvent.objects.filter(returned_at__isnull=True, started_at__lt=cutoff).count()
        if old_open > 0:
            issues.append(
                f"  ⚠ {old_open} exit events open for more than 7 days (likely data error)"
            )

        # Exit events without student
        no_student = ExitEvent.objects.filter(student__isnull=True).count()
        if no_student > 0:
            issues.append(f"  ⚠ {no_student} exit events without student reference")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.WARNING(issue))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ No issues found"))
