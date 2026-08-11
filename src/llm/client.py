import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from llm.schemas import EnrichRequest


load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parents[2]
PROMPT_FILE = PROJECT_DIR / "prompts" / "enrich-book-v1.md"


def generate_enrichment(book: EnrichRequest) -> str:
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")

    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": book.model_dump_json(),
            },
        ],
    )

    return response.choices[0].message.content or ""