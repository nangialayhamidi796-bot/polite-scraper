# The Polite Scraper

A small Python scraping pipeline that politely collects book information from the Books to Scrape practice sandbox. It discovers the first three catalogue pages, visits 60 book pages, cleans the extracted data, validates every record, and stores the results as JSON.

## Target Classification

* **Target:** https://books.toscrape.com/
* **Type:** Public web-scraping practice sandbox.
* **Scope:** Only the first three catalogue pages containing 60 books.
* **Data collected:** Title, product URL, price, availability, rating, description, source page, and fetch time.
* **Permission:** ToScrape describes Books to Scrape as a safe place for beginners to practise web scraping.
* **Robots check:** No robots file found. The `/robots.txt` request returned `404 Not Found`.
* **Why appropriate:** The website was specifically created for scraping practice.

I will not reuse this code on another site without checking its rules and terms first.

## Technology

* Python 3.10+
* Requests
* Beautiful Soup
* Pydantic

No database, paid API, proxy, cloud account, or browser is required.

## Installation

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

Install the packages:

```powershell
python -m pip install -r requirements.txt
```

## Run Command

```powershell
python src/main.py
```

The scraper creates:

```text
output/books.json
output/errors.json
output/run-report.json
```

## Record Schema

Each valid record contains:

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

## Politeness Rules

The scraper:

* Uses an identifying user-agent.
* Sets a 10-second request timeout.
* Waits at least 500 milliseconds between real requests.
* Checks the HTTP status before parsing a response.
* Caches downloaded HTML and uses the cache during development.
* Retries a timeout, connection failure, or server `5xx` error only once.
* Does not retry `403` or `404` responses.
* Handles each book page separately so one failure cannot stop the run.

## Idempotency

The absolute product URL is used as each book's identity. Running the scraper repeatedly overwrites the output safely and still produces exactly 60 unique records, not duplicates.

## Failure Test

The program deliberately adds one made-up book URL. The URL returns `404`, is logged and skipped, and the 60 valid books remain in `books.json`.

## Example Run Report

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

## Why No Browser Was Needed

The required data is already present in the HTML sent by the server. Using a browser would only add extra time, memory use, and complexity.

## Limitation

The CSS selectors are designed specifically for Books to Scrape. A change to the website's HTML structure could require selector updates. The scraper intentionally processes only the first three catalogue pages.

## Ethics

Use an official API when one is available. Never bypass logins, paywalls, access controls, or blocks. Collect only the information needed for the stated purpose.

## LLM Enrichment API

The LLM provider is configured through environment variables, so the API can switch between local Ollama and a hosted provider without changing code.

Start the API in stub mode:

```bash
LLM_STUB=1 uvicorn api:app --app-dir src --reload
```

### Valid request

```bash
curl -X POST "http://127.0.0.1:8000/enrich" \
  -H "Content-Type: application/json" \
  -d '{"title":"The Secret Garden","price":"£12.99","availability":"In stock","rating":"Four"}'
```

### Invalid request

```bash
curl -X POST "http://127.0.0.1:8000/enrich" \
  -H "Content-Type: application/json" \
  -d '{"title":"The Secret Garden","price":"£12.99","availability":"In stock"}'
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```