"""
Management command to archive old attendance records
Usage: python manage.py archive_old_attendance --days=365
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from school.models import AttendanceRecord
from school.models_enhanced import AttendanceRecordArchive


class Command(BaseCommand):
    help = "Archive attendance records older than specified days to archive table"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Archive records older than this many days (default: 365)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be archived without actually doing it",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records to process in each batch (default: 1000)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        cutoff_date = date.today() - timedelta(days=days)

        self.stdout.write(self.style.WARNING(f"Archiving attendance records older than {cutoff_date}"))

        # Count records to be archived
        old_records = AttendanceRecord.objects.filter(date__lt=cutoff_date)
        total_count = old_records.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No records to archive"))
            return

        self.stdout.write(f"Found {total_count} records to archive")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
            # Show sample records
            sample = old_records[:10]
            for record in sample:
                self.stdout.write(f"  - {record.student} on {record.date} ({record.status})")
            return

        # Archive in batches
        archived_count = 0
        failed_count = 0

        self.stdout.write("Starting archive process...")

        while True:
            batch = list(old_records[:batch_size])
            if not batch:
                break

            with transaction.atomic():
                try:
                    # Create archive records
                    archive_records = []
                    for record in batch:
                        archive_records.append(
                            AttendanceRecordArchive(
                                student_id=record.student_id,
                                student_name=record.student.full_name,
                                classroom_id=record.classroom_id,
                                classroom_name=record.classroom.name,
                                subject_id=record.subject_id,
                                subject_name=record.subject.name_ar,
                                teacher_id=record.teacher_id,
                                teacher_name=record.teacher.full_name,
                                term_id=record.term_id,
                                date=record.date,
                                day_of_week=record.day_of_week,
                                period_number=record.period_number,
                                start_time=record.start_time,
                                end_time=record.end_time,
                                status=record.status,
                                late_minutes=record.late_minutes,
                                early_minutes=record.early_minutes,
                                note=record.note,
                                original_id=record.id,
                            )
                        )

                    # Bulk create archive records
                    AttendanceRecordArchive.objects.bulk_create(archive_records)

                    # Delete original records
                    AttendanceRecord.objects.filter(id__in=[r.id for r in batch]).delete()

                    archived_count += len(batch)

                    self.stdout.write(
                        self.style.SUCCESS(f"Archived {archived_count}/{total_count} records"),
                        ending="\r",
                    )

                except Exception as e:
                    failed_count += len(batch)
                    self.stdout.write(self.style.ERROR(f"Error archiving batch: {e}"))

        self.stdout.write("\n")
        self.stdout.write(self.style.SUCCESS(f"Archive complete! Archived: {archived_count}, Failed: {failed_count}"))
