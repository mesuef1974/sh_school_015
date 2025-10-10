from __future__ import annotations

from io import BytesIO
from typing import Any, Dict

from backend.school.services.imports import import_teacher_loads

try:
    # Available when running inside RQ worker
    from rq import get_current_job  # type: ignore
except Exception:  # pragma: no cover - safe fallback when not in worker

    def get_current_job():  # type: ignore
        return None


def process_import_teacher_loads(file_bytes: bytes, *, dry_run: bool = False) -> Dict[str, Any]:
    """Worker job: run the Excel import from in-memory bytes and return summary.

    Also stores the summary into job.meta for easy retrieval from status pages.
    """
    summary = import_teacher_loads(BytesIO(file_bytes), dry_run=dry_run)
    job = get_current_job()
    if job is not None:
        job.meta = job.meta or {}
        job.meta["summary"] = summary
        job.save_meta()
    return summary


def enqueue_import_teacher_loads(queue, file_bytes: bytes, *, dry_run: bool = False):
    """Enqueue the import job on the provided RQ queue and return the job object."""
    return queue.enqueue(process_import_teacher_loads, file_bytes, dry_run=dry_run, job_timeout=600)
