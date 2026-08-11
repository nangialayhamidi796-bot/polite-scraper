import json
from datetime import datetime, timezone
from pathlib import Path

from llm.client import generate_enrichment
from llm.schemas import EnrichRequest, EnrichResponse


PROJECT_DIR = Path(__file__).resolve().parents[2]
QUARANTINE_FILE = PROJECT_DIR / "logs" / "quarantine.jsonl"
PROMPT_VERSION = "enrich-book-v1"


class EnrichmentValidationError(Exception):
    pass


def parse_and_validate(raw_output: str) -> EnrichResponse:
    start = raw_output.find("{")
    end = raw_output.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("Model output does not contain a JSON object")

    json_text = raw_output[start : end + 1]

    return EnrichResponse.model_validate_json(json_text)


def quarantine(
    book: EnrichRequest,
    raw_output: str,
    error: Exception,
) -> None:
    QUARANTINE_FILE.parent.mkdir(exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": book.model_dump(),
        "raw_output": raw_output,
        "error": str(error),
    }

    with QUARANTINE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_enrichment(book: EnrichRequest) -> EnrichResponse:
    first_output = generate_enrichment(book)

    try:
        return parse_and_validate(first_output)
    except Exception as first_error:
        repaired_output = generate_enrichment(
            book,
            broken_output=first_output,
            validation_error=str(first_error),
        )

        try:
            return parse_and_validate(repaired_output)
        except Exception as second_error:
            quarantine(book, repaired_output, second_error)

            raise EnrichmentValidationError(
                "The model could not produce a valid response after one repair"
            ) from second_error