"""
Management command to cleanup and normalize data
Usage: python manage.py cleanup_data
"""

import re

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from school.models import Class, Staff, Student


class Command(BaseCommand):
    help = "Cleanup and normalize database data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be cleaned without actually doing it",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        self.stdout.write(self.style.SUCCESS("Starting data cleanup..."))

        # Cleanup phone numbers
        self.cleanup_phone_numbers(dry_run)

        # Fix duplicate names
        self.fix_duplicate_names(dry_run)

        # Update students count in classes
        self.update_class_counts(dry_run)

        # Remove orphaned records
        self.remove_orphaned_records(dry_run)

        # Normalize national IDs
        self.normalize_national_ids(dry_run)

        self.stdout.write(self.style.SUCCESS("Data cleanup complete!"))

    def cleanup_phone_numbers(self, dry_run):
        """Normalize phone number formats"""
        self.stdout.write("\nCleaning phone numbers...")

        students = Student.objects.exclude(Q(phone_no="") & Q(parent_phone=""))
        count = 0

        for student in students:
            updated = False

            # Clean student phone
            if student.phone_no:
                clean_phone = self._normalize_phone(student.phone_no)
                if clean_phone != student.phone_no:
                    if not dry_run:
                        student.phone_no = clean_phone
                    updated = True

            # Clean parent phone
            if student.parent_phone:
                clean_parent = self._normalize_phone(student.parent_phone)
                if clean_parent != student.parent_phone:
                    if not dry_run:
                        student.parent_phone = clean_parent
                    updated = True

            if updated:
                if not dry_run:
                    student.save(update_fields=["phone_no", "parent_phone"])
                count += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ Cleaned {count} phone numbers"))

    def _normalize_phone(self, phone):
        """Normalize a single phone number"""
        # Remove all non-digit characters
        clean = re.sub(r"\D", "", phone)

        # Remove country code if present
        if clean.startswith("966"):
            clean = "0" + clean[3:]
        elif clean.startswith("00966"):
            clean = "0" + clean[5:]

        # Ensure starts with 0
        if clean and not clean.startswith("0"):
            clean = "0" + clean

        return clean

    def fix_duplicate_names(self, dry_run):
        """Find and report duplicate student names"""
        self.stdout.write("\nChecking for duplicate names...")

        duplicates = Student.objects.values("full_name").annotate(count=Count("id")).filter(count__gt=1)

        if duplicates.count() == 0:
            self.stdout.write(self.style.SUCCESS("  ✓ No duplicate names found"))
            return

        for dup in duplicates:
            students = Student.objects.filter(full_name=dup["full_name"])
            self.stdout.write(self.style.WARNING(f'  ⚠ Found {dup["count"]} students with name: {dup["full_name"]}'))
            for s in students:
                self.stdout.write(f"    - ID: {s.sid}, Class: {s.class_fk}")

    def update_class_counts(self, dry_run):
        """Update students_count field in Class model"""
        self.stdout.write("\nUpdating class student counts...")

        classes = Class.objects.all()
        updated_count = 0

        for cls in classes:
            actual_count = cls.students.filter(active=True).count()
            if cls.students_count != actual_count:
                if not dry_run:
                    cls.students_count = actual_count
                    cls.save(update_fields=["students_count"])
                updated_count += 1
                self.stdout.write(f"  - {cls.name}: {cls.students_count} → {actual_count}")

        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated {updated_count} class counts"))

    def remove_orphaned_records(self, dry_run):
        """Remove or report orphaned records"""
        self.stdout.write("\nChecking for orphaned records...")

        # Students without a class
        orphaned_students = Student.objects.filter(class_fk__isnull=True, active=True).count()

        if orphaned_students > 0:
            self.stdout.write(self.style.WARNING(f"  ⚠ Found {orphaned_students} active students without a class"))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ No orphaned student records"))

    def normalize_national_ids(self, dry_run):
        """Normalize national ID format"""
        self.stdout.write("\nNormalizing national IDs...")

        # Students
        students = Student.objects.exclude(national_no="")
        count = 0

        for student in students:
            if student.national_no:
                clean_id = re.sub(r"\D", "", student.national_no)
                if len(clean_id) == 10 and clean_id != student.national_no:
                    if not dry_run:
                        student.national_no = clean_id
                        student.save(update_fields=["national_no"])
                    count += 1

        # Staff
        staff = Staff.objects.exclude(national_no="")
        for s in staff:
            if s.national_no:
                clean_id = re.sub(r"\D", "", s.national_no)
                if len(clean_id) == 10 and clean_id != s.national_no:
                    if not dry_run:
                        s.national_no = clean_id
                        s.save(update_fields=["national_no"])
                    count += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ Normalized {count} national IDs"))
