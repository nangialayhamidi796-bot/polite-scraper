
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from llm.client import LLMProviderError, LLMTimeoutError
from llm.processor import EnrichmentValidationError, process_enrichment
from llm.schemas import EnrichRequest






@dataclass
class Job:
    id: str
    status: str
    request_data: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    attempts: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


jobs: dict[str, Job] = {}
idempotency_keys: dict[str, str] = {}
job_queue: queue.Queue[str] = queue.Queue()
logger = logging.getLogger(__name__)
store_lock = threading.Lock()
MAX_ATTEMPTS = 3


def create_job(
    request_data: dict[str, Any],
    idempotency_key: str,
) -> tuple[Job, bool]:
    with store_lock:
        existing_job_id = idempotency_keys.get(idempotency_key)

        if existing_job_id:
            existing_job = jobs[existing_job_id]
            return existing_job, False

        job = Job(
            id=str(uuid4()),
            status="pending",
            request_data=request_data,
        )

        jobs[job.id] = job
        idempotency_keys[idempotency_key] = job.id
        job_queue.put(job.id)

        return job, True


def get_job(job_id: str) -> Job | None:
    return jobs.get(job_id)

def run_worker() -> None:
    while True:
        job_id = job_queue.get()
        job = get_job(job_id)

        if job is None:
            job_queue.task_done()
            continue

        # Do not run an already completed job twice.
        if job.status == "completed":
            job_queue.task_done()
            continue

        job.status = "running"
        job.attempts += 1

        try:
            request = EnrichRequest(**job.request_data)
            response = process_enrichment(request)

            job.result = response.model_dump()
            job.status = "completed"
            job.error = None

        except (
            LLMTimeoutError,
            LLMProviderError,
            EnrichmentValidationError,
        ) as error:
            job.error = str(error)

            if job.attempts < MAX_ATTEMPTS:
                job.status = "pending"
                time.sleep(2 ** job.attempts)
                job_queue.put(job.id)
            else:
                job.status = "failed"
                logger.error(
                    "ALERT: Job %s permanently failed after %s attempts: %s",
                    job.id,
                    job.attempts,
                    error,
                )

        except Exception as error:
            job.error = str(error)
            job.status = "failed"
            logger.exception("ALERT: Unexpected job failure: %s", job.id)

        finally:
            job_queue.task_done()


def start_worker() -> None:
    worker = threading.Thread(
        target=run_worker,
        name="enrichment-worker",
        daemon=True,
    )
    worker.start()