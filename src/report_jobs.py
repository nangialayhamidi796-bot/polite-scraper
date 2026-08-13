import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from report_service import generate_pdf_report


@dataclass
class ReportJob:
    id: str
    status: str = "pending"
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


report_jobs: dict[str, ReportJob] = {}
report_queue: queue.Queue[str] = queue.Queue()
report_lock = threading.Lock()


def create_report_job() -> ReportJob:
    job = ReportJob(id=str(uuid4()))

    with report_lock:
        report_jobs[job.id] = job
        report_queue.put(job.id)

    return job


def get_report_job(job_id: str) -> ReportJob | None:
    return report_jobs.get(job_id)


def run_report_worker() -> None:
    while True:
        job_id = report_queue.get()
        job = get_report_job(job_id)

        if job is None:
            report_queue.task_done()
            continue

        job.status = "running"

        try:
            job.result = generate_pdf_report()
            job.status = "completed"
            job.error = None
        except Exception as error:
            job.status = "failed"
            job.error = str(error)
        finally:
            report_queue.task_done()


def start_report_worker() -> None:
    worker = threading.Thread(
        target=run_report_worker,
        name="pdf-report-worker",
        daemon=True,
    )
    worker.start()