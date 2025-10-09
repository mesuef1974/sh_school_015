from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from django.core.checks import run_checks
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.apps import apps


class Command(BaseCommand):
    help = (
        "Run a comprehensive, read-only health check for the platform and database. "
        "Reports system check results, DB connectivity, unapplied migrations, basic data quality, and index presence."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)",
        )
        parser.add_argument(
            "--fail-on-warn",
            action="store_true",
            help="Exit with non-zero code if warnings are present.",
        )

    def handle(self, *args, **opts):
        fmt: str = opts["format"]
        fail_on_warn: bool = opts["fail_on_warn"]

        report: Dict[str, Any] = {
            "system_check": {},
            "database": {},
            "migrations": {},
            "data_quality": {},
            "indexes": {},
        }

        # 1) Django system checks
        errors = run_checks()
        report["system_check"] = {
            "count": len(errors),
            "items": [
                {
                    "id": getattr(e, "id", None),
                    "msg": str(e),
                    "level": getattr(e, "level_tag", "ERROR"),
                }
                for e in errors
            ],
        }

        # 2) DB connectivity and basic info
        db_ok = True
        db_error = None
        tables: List[str] = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                # List user tables (PostgreSQL assumed; fallback generic information_schema)
                # Vendor-agnostic table listing via Django introspection
                introspection = connection.introspection
                tables = introspection.table_names()
        except Exception as e:  # pragma: no cover
            db_ok = False
            db_error = str(e)
        report["database"] = {"ok": db_ok, "error": db_error, "tables": tables}

        # 3) Unapplied migrations
        unapplied: List[Tuple[str, str]] = []
        try:
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            # Each plan item is (Migration, backwards?)
            for mig, _ in plan:
                unapplied.append((mig.app_label, mig.name))
        except Exception as e:  # pragma: no cover
            report["migrations"] = {
                "ok": False,
                "error": str(e),
                "unapplied": [],
            }
        else:
            report["migrations"] = {
                "ok": True,
                "unapplied": [f"{a}.{n}" for a, n in unapplied],
            }

        # 4) Data quality checks (read-only)
        dq: Dict[str, Any] = {}
        # Target core models
        ModelClass = apps.get_model("school", "Class")
        ModelStudent = apps.get_model("school", "Student")
        ModelStaff = apps.get_model("school", "Staff")
        ModelSubject = apps.get_model("school", "Subject")
        ModelClassSubject = apps.get_model("school", "ClassSubject")
        ModelTA = apps.get_model("school", "TeachingAssignment")

        # Helper to count duplicates on a field (ignoring NULL/empty)
        def dup_counts(model, field: str, ignore_blank: bool = True) -> int:
            from django.db.models import Count

            qs = model.objects.values(field).annotate(c=Count("id")).filter(c__gt=1)
            if ignore_blank:
                qs = qs.exclude(**{f"{field}__isnull": True}).exclude(**{f"{field}": ""})
            return qs.count()

        def null_fk_count(model, fk_field: str) -> int:
            return model.objects.filter(**{f"{fk_field}__isnull": True}).count()

        dq["Class"] = {"rows": ModelClass.objects.count()}
        dq["Student"] = {
            "rows": ModelStudent.objects.count(),
            "dup_sid": dup_counts(ModelStudent, "sid", ignore_blank=False),
            "dup_national_no": dup_counts(ModelStudent, "national_no", ignore_blank=True),
            "null_class_fk": null_fk_count(ModelStudent, "class_fk"),
        }
        dq["Staff"] = {
            "rows": ModelStaff.objects.count(),
            "dup_email": dup_counts(ModelStaff, "email", ignore_blank=True),
            "user_links_null": null_fk_count(ModelStaff, "user"),
        }
        dq["Subject"] = {"rows": ModelSubject.objects.count()}
        dq["ClassSubject"] = {
            "rows": ModelClassSubject.objects.count(),
            "null_classroom": null_fk_count(ModelClassSubject, "classroom"),
            "null_subject": null_fk_count(ModelClassSubject, "subject"),
        }
        dq["TeachingAssignment"] = {
            "rows": ModelTA.objects.count(),
            "null_teacher": null_fk_count(ModelTA, "teacher"),
            "null_classroom": null_fk_count(ModelTA, "classroom"),
            "null_subject": null_fk_count(ModelTA, "subject"),
        }
        report["data_quality"] = dq

        # 5) Index presence (best-effort; not fatal if DB vendor lacks pg catalogs)
        idx_info: Dict[str, Any] = {"ok": True, "missing": [], "error": None}
        try:
            wanted_indexes: Dict[str, List[str]] = {
                ModelStudent._meta.db_table: [
                    "student_natno_idx",
                    "student_class_idx",
                    "student_active_idx",
                    "student_needs_idx",
                    "student_nationality_idx",
                    "student_grade_label_idx",
                    "student_section_label_idx",
                ],
                ModelStaff._meta.db_table: [
                    "staff_role_idx",
                    "staff_user_idx",
                    "staff_email_idx",
                    "staff_phone_idx",
                    "staff_natno_idx",
                    "staff_jobno_idx",
                ],
            }
            existing: Dict[str, List[str]] = {}
            with connection.cursor() as cursor:
                # Vendor-agnostic index listing using Django introspection
                introspection = connection.introspection
                for t in wanted_indexes.keys():
                    try:
                        constraints = introspection.get_constraints(cursor, t)
                    except Exception:
                        constraints = {}
                    idx_names = [name for name, c in constraints.items() if c.get("index")]
                    existing[t] = idx_names
            for table, names in wanted_indexes.items():
                missing = [n for n in names if n not in set(existing.get(table, []))]
                if missing:
                    idx_info["missing"].append({"table": table, "indexes": missing})
        except Exception as e:  # pragma: no cover
            idx_info["ok"] = False
            idx_info["error"] = str(e)
        report["indexes"] = idx_info

        # Aggregate status
        warn_count = 0
        # count system check results (any non-empty is already problematic)
        warn_count += len(report["system_check"].get("items", []))
        # any unapplied migrations is a warning
        warn_count += len(report["migrations"].get("unapplied", []))
        # duplicates and nulls
        for k, v in dq.items():
            for key, val in v.items():
                if key.startswith("dup_") or key.startswith("null_"):
                    if isinstance(val, int) and val > 0:
                        warn_count += 1
        # missing indexes
        if report["indexes"].get("missing"):
            warn_count += len(report["indexes"]["missing"])  # type: ignore[index]

        # Output
        if fmt == "json":
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            self._print_text(report)

        if fail_on_warn and warn_count > 0:
            # Use CommandError for non-zero exit code with message
            raise CommandError(f"Healthcheck completed with {warn_count} warnings.")

    # --- helpers ---
    def _print_text(self, report: Dict[str, Any]) -> None:
        out = self.stdout
        out.write("== System check ==\n")
        items = report["system_check"].get("items", [])
        if not items:
            out.write("OK: No issues found by Django system check.\n")
        else:
            for e in items:
                out.write(f"{e.get('level', '')}: {e.get('id', '?')} - {e.get('msg', '')}\n")

        out.write("\n== Database ==\n")
        db = report["database"]
        out.write(f"Connection: {'OK' if db.get('ok') else 'ERROR'}\n")
        if db.get("error"):
            out.write(f"Error: {db['error']}\n")
        out.write(f"User tables: {len(db.get('tables', []))}\n")

        out.write("\n== Migrations ==\n")
        mig = report["migrations"]
        unapplied = mig.get("unapplied", [])
        if unapplied:
            out.write("Unapplied:\n")
            for m in unapplied:
                out.write(f"  - {m}\n")
        else:
            out.write("All migrations applied.\n")

        out.write("\n== Data quality ==\n")
        dq = report["data_quality"]
        for model_name, stats in dq.items():
            out.write(f"{model_name}: rows={stats.get('rows', 0)}\n")
            for k, v in stats.items():
                if k == "rows":
                    continue
                if isinstance(v, int) and v > 0:
                    out.write(f"  WARN {k}: {v}\n")
                elif isinstance(v, int):
                    out.write(f"  {k}: {v}\n")

        out.write("\n== Indexes (best-effort) ==\n")
        idx = report["indexes"]
        if not idx.get("ok"):
            out.write(f"Index check skipped/failed: {idx.get('error')}\n")
        else:
            missing = idx.get("missing", [])
            if missing:
                out.write("Missing suggested indexes:\n")
                for item in missing:
                    out.write(f"  - {item['table']}: {', '.join(item['indexes'])}\n")
            else:
                out.write("OK: All suggested indexes exist.\n")
