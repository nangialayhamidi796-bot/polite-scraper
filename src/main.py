from pathlib import Path

import requests


PAGE_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": (
        "FlyRankInternship-A9/1.0 "
        "(+https://github.com/nangialayhamidi796-bot/polite-scraper)"
    )
}

TIMEOUT = 10

PROJECT_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_DIR / "cache"
CACHE_FILE = CACHE_DIR / "catalogue-page-1.html"


def fetch_page():
    CACHE_DIR.mkdir(exist_ok=True)

    if CACHE_FILE.exists():
        html = CACHE_FILE.read_text(encoding="utf-8")
        size = len(html.encode("utf-8"))

        print(f"CACHE HIT: {size} bytes")
        return html

    print(f"FETCH: {PAGE_URL}")

    response = requests.get(
        PAGE_URL,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed with status {response.status_code}"
        )

    html = response.text
    CACHE_FILE.write_text(html, encoding="utf-8")

    size = len(html.encode("utf-8"))
    print(f"FETCH COMPLETE: status=200, size={size} bytes")

    return html

if __name__ == "__main__":
    fetch_page()