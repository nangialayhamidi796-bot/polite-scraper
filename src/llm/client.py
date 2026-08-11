import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from llm.schemas import EnrichRequest


load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parents[2]
PROMPT_FILE = PROJECT_DIR / "prompts" / "enrich-book-v1.md"


def generate_enrichment(
    book: EnrichRequest,
    broken_output: str | None = None,
    validation_error: str | None = None,
) -> str:
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")

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

    if broken_output is not None:
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
    )

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.1,
        messages=messages,
    )

    return response.choices[0].message.content or ""