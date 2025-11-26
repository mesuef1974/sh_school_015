import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from school.models import AttendanceRecord, AttendanceRecordArchive

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Archives attendance records older than a specified number of days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="The minimum age in days for attendance records to be archived.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="The number of records to process in each batch.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="If set, the command will only report the records to be archived without actually performing the operation.",
        )

    def handle(self, *args, **options):
        days_old = options["days"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        cutoff_date = date.today() - timedelta(days=days_old)
        self.stdout.write(f"Archiving attendance records older than {cutoff_date} ({days_old} days old).")

        records_to_archive = AttendanceRecord.objects.filter(date__lt=cutoff_date)
        total_count = records_to_archive.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No records to archive."))
            return

        self.stdout.write(f"Found {total_count} records to archive.")

        if dry_run:
            self.stdout.write(self.style.WARNING("This is a dry run. No data will be modified."))
            return

        archived_count = 0
        with transaction.atomic():
            for record in records_to_archive.iterator(chunk_size=batch_size):
                AttendanceRecordArchive.objects.create(
                    original_id=record.id,
                    student_id=record.student_id,
                    classroom_id=record.classroom_id,
                    subject_id=record.subject_id,
                    teacher_id=record.teacher_id,
                    term_id=record.term_id,
                    date=record.date,
                    day_of_week=record.day_of_week,
                    period_number=record.period_number,
                    start_time=record.start_time,
                    end_time=record.end_time,
                    status=record.status,
                    late_minutes=record.late_minutes,
                    early_minutes=record.early_minutes,
                    runaway_reason=record.runaway_reason,
                    excuse_type=record.excuse_type,
                    excuse_note=record.excuse_note,
                    note=record.note,
                    exit_reasons=record.exit_reasons,
                    exit_left_at=record.exit_left_at,
                    exit_returned_at=record.exit_returned_at,
                    source=record.source,
                    locked=record.locked,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
                archived_count += 1

            # After archiving, delete the original records
            records_to_archive.delete()

        self.stdout.write(self.style.SUCCESS(f"Successfully archived and deleted {archived_count} records."))
