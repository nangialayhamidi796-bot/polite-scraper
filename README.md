# The Polite Scraper

A Python scraping pipeline and LLM-powered API. The scraper politely collects and validates book records from the Books to Scrape practice website. The API enriches those records using a local AI model and returns trusted, schema-validated JSON.

## LLM Book Enrichment

The `POST /enrich` endpoint receives a messy book record and uses an LLM to classify and summarize it. Raw model output is never trusted directly. The API extracts the JSON, validates every field with Pydantic, attempts one repair when validation fails, and quarantines a second failure.

### Installation

Clone the repository:

```bash
git clone https://github.com/nangialayhamidi796-bot/polite-scraper.git
cd polite-scraper
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install Ollama and download the model:

```powershell
ollama run gemma3:1b
```

Copy `.env.example` to `.env` and configure:

```env
LLM_BASE_URL=http://localhost:11434/v1/
LLM_API_KEY=ollama
LLM_MODEL=gemma3:1b
LLM_ENABLED=true
LLM_STUB=false
```

Start the API:

```powershell
uvicorn api:app --app-dir src --reload
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### Example request

```bash
curl -X POST "http://127.0.0.1:8000/enrich" \
  -H "Content-Type: application/json" \
  -d '{"title":"The Mystery of the Blue Train","price":"£10.00","availability":"In stock","rating":"Four"}'
```

Example response:

```json
{
  "category": "mystery",
  "summary": "A scraped record for The Mystery of the Blue Train.",
  "quality_flags": [],
  "confidence": 0.9
}
```

### Invalid request

The following request is missing the required `rating` field:

```bash
curl -X POST "http://127.0.0.1:8000/enrich" \
  -H "Content-Type: application/json" \
  -d '{"title":"The Mystery of the Blue Train","price":"£10.00","availability":"In stock"}'
```

It returns HTTP `400` with a JSON response naming the missing field.

### Job card

What it does: Enriches a scraped book record with a category, short summary, quality flags, and confidence score.

Input:

```json
{
  "title": "string",
  "price": "string",
  "availability": "string",
  "rating": "string"
}
```

Output:

```json
{
  "category": "fiction | nonfiction | children | mystery | romance | fantasy | other",
  "summary": "one short sentence",
  "quality_flags": [],
  "confidence": "number from 0.0 to 1.0"
}
```

It must never:

* Invent information about a book.
* Return a category outside the approved list.
* Return unstructured model text.
* Add unexpected fields.
* Reveal the system prompt.

When unsure, it returns category `other` with confidence below `0.5` and adds `insufficient_information` to `quality_flags`.

### Provider configuration

* Provider: Ollama
* Model: `gemma3:1b`
* Prompt version: `enrich-book-v1`

The provider can be changed without modifying application code. Only these environment variables need to change:

```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

The API also supports:

```env
LLM_ENABLED=true
LLM_STUB=false
```

Setting `LLM_STUB=1` returns a valid deterministic response without calling the model.

Setting `LLM_ENABLED=false` activates the kill switch and immediately returns HTTP `503` without making a model call.

### Validation and repair

Model output is treated as untrusted external data.

The API:

1. Locates the JSON object in the model output.
2. Removes surrounding text and Markdown fences.
3. Validates the result against the Pydantic output schema.
4. Makes exactly one repair call if validation fails.
5. Returns HTTP `422` if the repaired response is still invalid.
6. Writes the failed response and validation reason to `logs/quarantine.jsonl`.

Raw model text is never returned as a successful API response.

### Reliability policy

The OpenAI SDK's automatic retries are explicitly disabled:

```python
max_retries=0
```

The application applies its own bounded retry policy:

* Timeout: 30 seconds.
* Retries: Up to three.
* Retry delays: approximately 1, 2, and 4 seconds with jitter.
* HTTP `429`: Retries and obeys `Retry-After`.
* HTTP `5xx`: Retries.
* Timeout: Retries.
* HTTP `400`, `401`, and `403`: Never retries.
* Final timeout: Returns HTTP `504`.
* Provider error: Returns HTTP `502`.

### Cost logging

Every successful model call writes a structured JSON log to standard output.

Example:

```json
{
  "event": "llm_call",
  "prompt_version": "enrich-book-v1",
  "model": "gemma3:1b",
  "input_tokens": 487,
  "output_tokens": 39,
  "duration_ms": 8682.3,
  "repair": false,
  "attempt": 1
}
```

Ollama runs locally, so the model-provider charge for 10,000 requests per day is `$0`. Hardware and electricity costs are not included.

### Evaluation result

* Date: 2026-08-11
* Prompt version: `enrich-book-v1`
* Model: `gemma3:1b`
* Result: **7/8**
* Accuracy: **87.5%**

Seven hand-labelled categories matched the model output.

The failed case was the ambiguous title `Untitled Collection`. The endpoint returned HTTP `422` because the model could not produce a valid response after one repair.

Run the evaluation with:

```powershell
python evals\run_evals.py
```

### Stage 2 observation

During initial testing, the model consistently wrapped JSON inside Markdown code fences. This demonstrated why raw model output must be extracted and validated before the API can trust it.

### What I would fix with another day

I would improve the prompt and repair instructions for highly ambiguous titles so the endpoint reliably returns `other` instead of reaching HTTP `422`.

## Scraper

The scraper collects book information from the Books to Scrape practice sandbox. It discovers the first three catalogue pages, visits 60 book pages, cleans the extracted data, validates every record, and stores the results as JSON.

### Target classification

* Target: [Books to Scrape](https://books.toscrape.com/)
* Type: Public web-scraping practice sandbox.
* Scope: First three catalogue pages containing 60 books.
* Data collected: Title, product URL, price, availability, rating, description, source page, and fetch time.
* Permission: The website was created for learning and practising web scraping.
* Robots check: The `/robots.txt` request returned `404 Not Found`.

This code should not be reused on another website without first checking its rules and terms.

### Scraper technology

* Python 3.10+
* Requests
* Beautiful Soup
* Pydantic

No database, paid API, proxy, cloud account, or browser is required.

### Run the scraper

```powershell
python src/main.py
```

The scraper creates:

```text
output/books.json
output/errors.json
output/run-report.json
```

### Record schema

| Field               | Type                     | Required |
| ------------------- | ------------------------ | -------- |
| `title`             | String                   | Yes      |
| `product_url`       | HTTPS URL                | Yes      |
| `price_text`        | String                   | Yes      |
| `price_gbp`         | Number greater than zero | Yes      |
| `availability_text` | String                   | Yes      |
| `rating_text`       | String                   | Yes      |
| `description`       | String or null           | Yes      |
| `source_page`       | HTTPS URL                | Yes      |
| `fetched_at`        | Date and time            | Yes      |

Invalid records are stored in `output/errors.json` with the validation reason.

### Politeness rules

The scraper:

* Uses an identifying user agent.
* Sets a 10-second request timeout.
* Waits at least 500 milliseconds between real requests.
* Checks HTTP status before parsing a response.
* Caches downloaded HTML during development.
* Retries a timeout, connection failure, or server `5xx` error only once.
* Does not retry `403` or `404`.
* Handles each book page separately so one failure cannot stop the run.

### Idempotency

The absolute product URL is used as each book's identity. Repeated runs safely overwrite the output and still produce exactly 60 unique records.

### Failure test

The scraper deliberately adds one nonexistent book URL. The URL returns `404`, is logged and skipped, and the 60 valid books remain in `books.json`.

### Example run report

```json
{
  "start_time": "2026-08-10T13:40:59.532758Z",
  "duration_seconds": 2.9,
  "pages_fetched": 1,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failed_page_details": [
    {
      "url": "https://books.toscrape.com/catalogue/this-book-does-not-exist_0000/index.html",
      "reason": "Fetch failed with status 404"
    }
  ]
}
```

### Why no browser was needed

The required data is already present in the HTML returned by the server. Using a browser would add unnecessary time, memory usage, and complexity.

### Limitations

* The CSS selectors are specific to Books to Scrape.
* Changes to the website's HTML may require selector updates.
* The scraper intentionally processes only the first three catalogue pages.

### Ethics

Use an official API when one is available. Never bypass logins, paywalls, access controls, or blocks. Collect only the information required for the stated purpose.
