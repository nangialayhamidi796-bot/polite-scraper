import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


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


def fetch_page(url, cache_name):
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / cache_name

    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
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

    html = response.text
    cache_file.write_text(html, encoding="utf-8")

    size = len(html.encode("utf-8"))
    print(f"FETCH COMPLETE: status=200, size={size} bytes")

    return html


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


if __name__ == "__main__":
    discover_books()