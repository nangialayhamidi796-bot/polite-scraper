import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from llm.schemas import EnrichRequest
from jobs import create_job, get_job, start_worker

from jobs import create_job, get_job, start_worker


load_dotenv()

app = FastAPI(
    title="Polite Scraper API",
    version="1.0.0",
)
@app.on_event("startup")
def startup_event():
    start_worker()


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