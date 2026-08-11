import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from llm.schemas import EnrichRequest, EnrichResponse


load_dotenv()

app = FastAPI(
    title="Polite Scraper API",
    version="1.0.0",
)


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


@app.post("/enrich", response_model=EnrichResponse)
def enrich_book(book: EnrichRequest):
    if os.getenv("LLM_STUB", "").lower() in {"1", "true"}:
        return EnrichResponse(
            category="other",
            summary=f"Book record for {book.title}.",
            quality_flags=["stub_response"],
            confidence=0.5,
        )

    raise HTTPException(
        status_code=503,
        detail="LLM integration is not enabled yet",
    )
