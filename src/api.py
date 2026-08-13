from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from jobs import create_job, get_job, start_worker
from llm.schemas import EnrichRequest
from report_jobs import (
    create_report_job,
    get_report_job,
    start_report_worker,
)


load_dotenv()

app = FastAPI(
    title="Polite Scraper API",
    version="1.1.0",
)


@app.on_event("startup")
def startup_event():
    start_worker()
    start_report_worker()


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    error: RequestValidationError,
):
    fields = [
        {
            "field": ".".join(str(part) for part in item["loc"][1:]),
            "message": item["msg"],
        }
        for item in error.errors()
    ]

    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_request",
            "fields": fields,
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/enrich", status_code=202)
def enrich_book(
    book: EnrichRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    job, created = create_job(
        book.model_dump(),
        idempotency_key,
    )

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job.id,
            "status": job.status,
            "created": created,
            "status_url": f"/jobs/{job.id}",
        },
        headers={
            "Location": f"/jobs/{job.id}",
        },
    )


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return {
        "job_id": job.id,
        "status": job.status,
        "attempts": job.attempts,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at,
    }


@app.post("/reports", status_code=202)
def request_pdf_report():
    job = create_report_job()

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job.id,
            "status": job.status,
            "status_url": f"/reports/{job.id}",
        },
        headers={
            "Location": f"/reports/{job.id}",
        },
    )


@app.get("/reports/{job_id}")
def report_status(job_id: str):
    job = get_report_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Report job not found",
        )

    response = {
        "job_id": job.id,
        "status": job.status,
        "error": job.error,
        "created_at": job.created_at,
        "download_url": None,
    }

    if job.status == "completed":
        response["download_url"] = f"/reports/{job.id}/download"

    return response


@app.get("/reports/{job_id}/download")
def download_report(job_id: str):
    job = get_report_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Report job not found",
        )

    if job.status != "completed" or job.result is None:
        raise HTTPException(
            status_code=409,
            detail="Report is not ready",
        )

    file_path = Path(job.result["file_path"])

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file not found",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=job.result["file_name"],
    )