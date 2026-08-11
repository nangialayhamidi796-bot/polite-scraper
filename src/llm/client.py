import json
import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import APITimeoutError, APIStatusError, OpenAI

from llm.schemas import EnrichRequest


load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parents[2]
PROMPT_FILE = PROJECT_DIR / "prompts" / "enrich-book-v1.md"
PROMPT_VERSION = "enrich-book-v1"
MAX_ATTEMPTS = 4


class LLMTimeoutError(Exception):
    pass


class LLMProviderError(Exception):
    pass


def retry_after_seconds(error: APIStatusError) -> float | None:
    value = error.response.headers.get("retry-after")

    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_time = parsedate_to_datetime(value)
            now = datetime.now(timezone.utc)
            return max(0.0, (retry_time - now).total_seconds())
        except (TypeError, ValueError):
            return None


def retry_delay(attempt: int, error: APIStatusError | None = None) -> float:
    if error is not None and error.status_code == 429:
        provider_delay = retry_after_seconds(error)

        if provider_delay is not None:
            return provider_delay

    return (2 ** (attempt - 1)) + random.uniform(0.0, 0.25)


def generate_enrichment(
    book: EnrichRequest,
    broken_output: str | None = None,
    validation_error: str | None = None,
) -> str:
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    is_repair = broken_output is not None

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": book.model_dump_json(),
        },
    ]

    if is_repair:
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": broken_output,
                },
                {
                    "role": "user",
                    "content": (
                        "Your previous answer was rejected for this reason: "
                        f"{validation_error}. Return only corrected JSON "
                        "matching the schema. Do not use Markdown fences."
                    ),
                },
            ]
        )

    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=30.0,
        max_retries=0,
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.perf_counter()

        try:
            response = client.chat.completions.create(
                model=os.environ["LLM_MODEL"],
                temperature=0.1,
                messages=messages,
            )

            duration_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )
            usage = response.usage

            cost_log = {
                "event": "llm_call",
                "prompt_version": PROMPT_VERSION,
                "model": os.environ["LLM_MODEL"],
                "input_tokens": usage.prompt_tokens if usage else 0,
                "output_tokens": usage.completion_tokens if usage else 0,
                "duration_ms": duration_ms,
                "repair": is_repair,
                "attempt": attempt,
            }
            print(json.dumps(cost_log))

            return response.choices[0].message.content or ""

        except APITimeoutError as error:
            if attempt == MAX_ATTEMPTS:
                raise LLMTimeoutError(
                    "The model did not respond within 30 seconds"
                ) from error

            delay = retry_delay(attempt)
            print(
                json.dumps(
                    {
                        "event": "llm_retry",
                        "reason": "timeout",
                        "attempt": attempt,
                        "delay_seconds": round(delay, 2),
                    }
                )
            )
            time.sleep(delay)

        except APIStatusError as error:
            retryable = error.status_code == 429 or error.status_code >= 500

            if not retryable or attempt == MAX_ATTEMPTS:
                raise LLMProviderError(
                    f"Model provider returned status {error.status_code}"
                ) from error

            delay = retry_delay(attempt, error)
            print(
                json.dumps(
                    {
                        "event": "llm_retry",
                        "reason": f"http_{error.status_code}",
                        "attempt": attempt,
                        "delay_seconds": round(delay, 2),
                    }
                )
            )
            time.sleep(delay)

    raise LLMProviderError("Model request failed")