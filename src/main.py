import json
import time
from pathlib import Path
from urllib.parse import urljoin
from pydantic import BaseModel, Field, HttpUrl, ValidationError

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone


START_URL = "https://books.toscrape.com/catalogue/page-1.html"
REQUEST_DELAY = 0.5
TIMEOUT = 10

HEADERS = {
    "User-Agent": (
        "FlyRankInternship-A9/1.0 "
        "(+https://github.com/nangialayhamidi796-bot/polite-scraper)"
    )
}

PROJECT_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_DIR / "cache"
OUTPUT_DIR = PROJECT_DIR / "output"

class BookRecord(BaseModel):
    title: str = Field(min_length=1)
    product_url: HttpUrl
    price_text: str = Field(min_length=1)
    price_gbp: float = Field(gt=0)
    availability_text: str = Field(min_length=1)
    rating_text: str = Field(min_length=1)
    description: str | None
    source_page: HttpUrl
    fetched_at: datetime


def fetch_page(url, cache_name):
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / cache_name

    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        html = html.replace("Â£", "£")
        size = len(html.encode("utf-8"))

        print(f"CACHE HIT: {cache_name}, size={size} bytes")
        return html

    print(f"FETCH: {url}")
    time.sleep(REQUEST_DELAY)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed with status {response.status_code}: {url}"
        )

    
    response.encoding = "utf-8"
    html = response.text
    cache_file.write_text(html, encoding="utf-8")

    size = len(html.encode("utf-8"))
    print(f"FETCH COMPLETE: status=200, size={size} bytes")

    return html
def get_fetched_at(cache_name):
    cache_file = CACHE_DIR / cache_name
    modified_time = cache_file.stat().st_mtime

    fetched_at = datetime.fromtimestamp(
        modified_time,
        tz=timezone.utc,
    )

    return fetched_at.isoformat().replace("+00:00", "Z")

def extract_book(html, product_url, source_page, cache_name):
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("div.product_main")

    if product is None:
        raise ValueError("Product section was not found")

    title = product.select_one("h1").get_text(strip=True)
    price_text = product.select_one("p.price_color").get_text(strip=True)

    availability_text = product.select_one(
        "p.availability"
    ).get_text(" ", strip=True)

    rating_element = product.select_one("p.star-rating")
    rating_classes = rating_element.get("class", [])

    rating_text = next(
        class_name
        for class_name in rating_classes
        if class_name != "star-rating"
    )

    description_element = soup.select_one(
        "#product_description + p"
    )

    if description_element is None:
        description = None
    else:
        description = description_element.get_text(" ", strip=True)

    raw_record = {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": get_fetched_at(cache_name),
    }

    return raw_record

def discover_books():
    page_url = START_URL
    book_sources = {}
    discovered = 0

    for page_number in range(1, 4):
        cache_name = f"catalogue-page-{page_number}.html"
        html = fetch_page(page_url, cache_name)

        soup = BeautifulSoup(html, "html.parser")
        book_links = soup.select("article.product_pod h3 a")

        discovered += len(book_links)

        for link in book_links:
            book_url = urljoin(page_url, link["href"])
            book_sources.setdefault(book_url, page_url)

        if page_number < 3:
            next_link = soup.select_one("li.next a")

            if next_link is None:
                raise RuntimeError("Next catalogue page was not found")

            page_url = urljoin(page_url, next_link["href"])

    print("catalogue_pages=3")
    print(f"discovered={discovered}")
    print(f"unique_urls={len(book_sources)}")

    return book_sources

def scrape_book_details():
    book_sources = discover_books()
    raw_records = []

    for number, (product_url, source_page) in enumerate(
        book_sources.items(),
        start=1,
    ):
        book_slug = product_url.rstrip("/").split("/")[-2]
        cache_name = f"book-{book_slug}.html"

        print(f"DETAIL {number}/60")

        html = fetch_page(product_url, cache_name)

        record = extract_book(
            html=html,
            product_url=product_url,
            source_page=source_page,
            cache_name=cache_name,
        )

        raw_records.append(record)

    print(f"detail_pages={len(raw_records)}")
    print(json.dumps(raw_records[0], indent=2, ensure_ascii=False))

    return raw_records

def validate_and_store(raw_records):
    OUTPUT_DIR.mkdir(exist_ok=True)

    valid_by_url = {}
    errors = []

    for raw_record in raw_records:
        try:
            price_gbp = float(
                raw_record["price_text"].replace("£", "").strip()
            )

            clean_record = {
                **raw_record,
                "price_gbp": price_gbp,
            }

            validated = BookRecord.model_validate(clean_record)
            validated_data = validated.model_dump(mode="json")

            product_url = str(validated_data["product_url"])
            valid_by_url[product_url] = validated_data

        except (ValueError, ValidationError) as error:
            errors.append(
                {
                    "product_url": raw_record.get("product_url"),
                    "reason": str(error),
                    "record": raw_record,
                }
            )

    valid_records = list(valid_by_url.values())

    books_file = OUTPUT_DIR / "books.json"
    errors_file = OUTPUT_DIR / "errors.json"

    books_file.write_text(
        json.dumps(valid_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    errors_file.write_text(
        json.dumps(errors, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"valid_records={len(valid_records)}")
    print(f"invalid_records={len(errors)}")
    print(f"books_file={books_file}")
    print(f"errors_file={errors_file}")

    return valid_records, errors

if __name__ == "__main__":
    raw_records = scrape_book_details()
    validate_and_store(raw_records)