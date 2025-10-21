from django.core.management.base import BaseCommand, CommandError

from ...services.timetable_import import import_timetable_csv


class Command(BaseCommand):
    help = "Import timetable entries from a CSV file. Headers: teacher,class,subject,day,period"

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to CSV file (UTF-8)")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Validate only without writing",
        )

    def handle(self, *args, **options):
        path = options["path"]
        dry = options["dry_run"]
        try:
            summary = import_timetable_csv(path, dry_run=dry)
        except Exception as e:
            raise CommandError(str(e))
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: created={summary['created']} replaced={summary['replaced']} skipped={summary['skipped']}"
            )
        )
        if summary.get("errors"):
            for err in summary["errors"]:
                self.stdout.write(self.style.WARNING(err))
