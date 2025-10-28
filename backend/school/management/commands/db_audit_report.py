from django.core.management.base import BaseCommand
from django.db import connection

from ...models import AttendanceRecord, Student, TeachingAssignment, Term, TimetableEntry


class Command(BaseCommand):
    help = "Print DB best-practices audit results (passes and suggestions) for the 'school' app. Read-only."

    def handle(self, *args, **options):
        # DB info
        try:
            vendor = connection.vendor
            settings_dict = getattr(connection, "settings_dict", {}) or {}
            db_name = settings_dict.get("NAME")
            db_ver = None
            if vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    row = cursor.fetchone()
                    db_ver = row[0] if row else None
            elif vendor == "mysql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT VERSION();")
                    row = cursor.fetchone()
                    db_ver = row[0] if row else None
            else:
                db_ver = getattr(connection, "server_version", None)
        except Exception:
            vendor = None
            db_name = None
            db_ver = None

        # Resolve table names
        term_tbl = Term._meta.db_table
        tten_tbl = TimetableEntry._meta.db_table
        atre_tbl = AttendanceRecord._meta.db_table
        tasg_tbl = TeachingAssignment._meta.db_table
        stud_tbl = Student._meta.db_table

        passes = []
        suggestions = []

        def add_pass(title, detail):
            passes.append({"title": title, "detail": detail})

        def add_sug(title, detail, hint=None):
            suggestions.append({"title": title, "detail": detail, "hint": hint})

        # Introspection
        introspection = connection.introspection
        constraints = {}
        with connection.cursor() as cursor:
            for tbl in [term_tbl, tten_tbl, atre_tbl, tasg_tbl, stud_tbl]:
                try:
                    constraints[tbl] = introspection.get_constraints(cursor, tbl)
                except Exception:
                    constraints[tbl] = {}

        def has_named(tbl, name_substr: str) -> bool:
            for cname in constraints.get(tbl, {}).keys():
                if name_substr.lower() in cname.lower():
                    return True
            return False

        def has_index_with_columns(tbl, cols_exact_order):
            cols_exact_order = [c.lower() for c in cols_exact_order]
            for _, cinfo in constraints.get(tbl, {}).items():
                try:
                    if cinfo.get("index"):
                        cols = [c.lower() for c in (cinfo.get("columns") or [])]
                        if cols == cols_exact_order:
                            return True
                except Exception:
                    continue
            return False

        # Checks (match the web audit view)
        if has_named(term_tbl, "one_current_term_per_year"):
            add_pass(
                "Term current per year",
                "Conditional unique present (one_current_term_per_year)",
            )
        else:
            add_sug(
                "Term current per year",
                "Add conditional UniqueConstraint to enforce one current term per academic year.",
            )

        if has_named(tten_tbl, "tt_day_between_1_5"):
            add_pass("TimetableEntry day check", "day_of_week between 1 and 5")
        else:
            add_sug(
                "TimetableEntry day check",
                "Add CHECK constraint for day_of_week between 1 and 5.",
            )

        if has_named(tten_tbl, "tt_period_between_1_7"):
            add_pass("TimetableEntry period check", "period_number between 1 and 7")
        else:
            add_sug(
                "TimetableEntry period check",
                "Add CHECK constraint for period_number between 1 and 7.",
            )

        if has_index_with_columns(tten_tbl, ["term_id", "teacher_id", "day_of_week", "period_number"]):
            add_pass("TimetableEntry index (term,teacher,day,period)", "Present")
        else:
            add_sug(
                "TimetableEntry index (term,teacher,day,period)",
                "Add composite index to speed lookups.",
            )

        if has_index_with_columns(tten_tbl, ["term_id", "classroom_id", "day_of_week", "period_number"]):
            add_pass("TimetableEntry index (term,class,day,period)", "Present")
        else:
            add_sug(
                "TimetableEntry index (term,class,day,period)",
                "Add composite index to speed lookups.",
            )

        if has_named(atre_tbl, "att_day_between_1_7"):
            add_pass("AttendanceRecord day check", "day_of_week between 1 and 7")
        else:
            add_sug(
                "AttendanceRecord day check",
                "Add CHECK for day_of_week between 1 and 7.",
            )

        if has_named(atre_tbl, "att_period_between_1_7"):
            add_pass("AttendanceRecord period check", "period_number between 1 and 7")
        else:
            add_sug(
                "AttendanceRecord period check",
                "Add CHECK for period_number between 1 and 7.",
            )

        if has_index_with_columns(atre_tbl, ["classroom_id", "date", "period_number", "term_id"]):
            add_pass("Attendance index (class,date,period,term)", "Present")
        else:
            add_sug("Attendance index (class,date,period,term)", "Add composite index.")

        if has_index_with_columns(atre_tbl, ["student_id", "date", "term_id"]):
            add_pass("Attendance index (student,date,term)", "Present")
        else:
            add_sug("Attendance index (student,date,term)", "Add composite index.")

        if not has_index_with_columns(tasg_tbl, ["teacher_id", "classroom_id"]):
            add_sug(
                "TeachingAssignment index (teacher,classroom)",
                "Optional composite index based on workload.",
            )
        else:
            add_pass("TeachingAssignment index (teacher,classroom)", "Present")

        # Optional trigram suggestion always listed as suggestion (safe, optional)
        add_sug(
            "Trigram index for Student.full_name (optional)",
            "Enable pg_trgm and add GIN trigram index for faster Arabic name search.",
        )

        total = len(passes) + len(suggestions)
        ok = len(passes)
        warn = len(suggestions)

        self.stdout.write(self.style.NOTICE(f"DB: {db_name} | Engine: {vendor} | Version: {db_ver or '-'}"))
        self.stdout.write(self.style.HTTP_INFO(f"Checks: {total} | Pass: {ok} | Suggestions: {warn}"))
        self.stdout.write("")
        if passes:
            self.stdout.write(self.style.SUCCESS("Pass:"))
            for it in passes:
                self.stdout.write(f"  - {it['title']}: {it['detail']}")
            self.stdout.write("")
        if suggestions:
            self.stdout.write(self.style.WARNING("Suggestions:"))
            for it in suggestions:
                self.stdout.write(f"  - {it['title']}: {it['detail']}")
        else:
            self.stdout.write(self.style.SUCCESS("No suggestions — all proposals applied."))
