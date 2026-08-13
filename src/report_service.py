import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOOKS_JSON = PROJECT_ROOT / "output" / "books.json"
DATABASE_PATH = PROJECT_ROOT / "output" / "reports.db"
REPORTS_DIRECTORY = PROJECT_ROOT / "output" / "reports"


def prepare_database() -> None:
    with BOOKS_JSON.open("r", encoding="utf-8") as file:
        books = json.load(file)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                title TEXT NOT NULL,
                price_gbp REAL NOT NULL,
                availability TEXT NOT NULL,
                rating TEXT NOT NULL,
                product_url TEXT NOT NULL
            )
            """
        )

        connection.execute("DELETE FROM books")

        connection.executemany(
            """
            INSERT INTO books (
                title,
                price_gbp,
                availability,
                rating,
                product_url
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    book["title"],
                    book["price_gbp"],
                    book["availability_text"],
                    book["rating_text"],
                    book["product_url"],
                )
                for book in books
            ],
        )


def query_report_data() -> tuple[dict, list[tuple]]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        summary_row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_books,
                ROUND(AVG(price_gbp), 2) AS average_price,
                ROUND(MIN(price_gbp), 2) AS lowest_price,
                ROUND(MAX(price_gbp), 2) AS highest_price
            FROM books
            """
        ).fetchone()

        rating_rows = connection.execute(
            """
            SELECT
                rating,
                COUNT(*) AS book_count,
                ROUND(AVG(price_gbp), 2) AS average_price
            FROM books
            GROUP BY rating
            ORDER BY
                CASE rating
                    WHEN 'One' THEN 1
                    WHEN 'Two' THEN 2
                    WHEN 'Three' THEN 3
                    WHEN 'Four' THEN 4
                    WHEN 'Five' THEN 5
                    ELSE 6
                END
            """
        ).fetchall()

    summary = {
        "total_books": summary_row[0],
        "average_price": summary_row[1],
        "lowest_price": summary_row[2],
        "highest_price": summary_row[3],
    }

    return summary, rating_rows


def generate_pdf_report() -> dict:
    prepare_database()
    summary, rating_rows = query_report_data()

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    report_id = str(uuid4())
    pdf_path = REPORTS_DIRECTORY / f"book-report-{report_id}.pdf"

    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    pdf.setTitle("Polite Scraper Book Report")

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, height - 60, "Polite Scraper Book Report")

    generated_at = datetime.now(timezone.utc).isoformat()

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, height - 82, f"Generated: {generated_at}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 125, "Summary")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(
        65,
        height - 150,
        f"Total books: {summary['total_books']}",
    )
    pdf.drawString(
        65,
        height - 172,
        f"Average price: GBP {summary['average_price']:.2f}",
    )
    pdf.drawString(
        65,
        height - 194,
        f"Lowest price: GBP {summary['lowest_price']:.2f}",
    )
    pdf.drawString(
        65,
        height - 216,
        f"Highest price: GBP {summary['highest_price']:.2f}",
    )

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 260, "Books grouped by rating")

    y_position = height - 292

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(65, y_position, "Rating")
    pdf.drawString(220, y_position, "Book count")
    pdf.drawString(360, y_position, "Average price")

    pdf.line(60, y_position - 5, width - 60, y_position - 5)

    pdf.setFont("Helvetica", 11)

    for rating, book_count, average_price in rating_rows:
        y_position -= 25
        pdf.drawString(65, y_position, str(rating))
        pdf.drawString(220, y_position, str(book_count))
        pdf.drawString(
            360,
            y_position,
            f"GBP {average_price:.2f}",
        )

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        50,
        45,
        "Data source: output/books.json | Aggregated using SQLite SQL",
    )

    pdf.save()

    return {
        "report_id": report_id,
        "file_name": pdf_path.name,
        "file_path": str(pdf_path),
        "generated_at": generated_at,
        "summary": summary,
    }