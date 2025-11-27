from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
import unicodedata
from typing import Iterable, Optional, Sequence
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://unfccc.int/BURs"
STORAGE_DIR = Path(__file__).parent / "storage"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
    )
}


@dataclass
class BurDocument:
    """Represents a BUR PDF that can be stored locally."""

    country: str
    title: str
    url: str
    year: Optional[int] = None

    @property
    def normalized_country(self) -> str:
        return normalize_country(self.country)

    @property
    def filename(self) -> str:
        year_part = str(self.year) if self.year else "LATEST"
        return f"{self.normalized_country}_BUR_{year_part}.pdf"

    @property
    def destination(self) -> Path:
        return STORAGE_DIR / self.filename


def normalize_country(country: str) -> str:
    cleaned = re.sub(r"\s+", " ", country.strip())
    decomposed = unicodedata.normalize("NFKD", cleaned)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return ascii_only.upper()


def ensure_storage_dir() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def list_local_documents(country: str) -> list[Path]:
    ensure_storage_dir()
    normalized = normalize_country(country)
    candidates = sorted(
        STORAGE_DIR.glob(f"{normalized}_BUR_*.pdf"),
        key=lambda path: extract_year_from_name(path.name) or 0,
        reverse=True,
    )
    return candidates


def extract_year_from_name(name: str) -> Optional[int]:
    match = re.search(r"(19|20)\d{2}", name)
    if match:
        return int(match.group())
    return None


def extract_year_from_text(text: str) -> Optional[int]:
    match = re.search(r"(19|20)\d{2}", text)
    if match:
        return int(match.group())
    return None


def scrape_latest_bur(country: str) -> Optional[BurDocument]:
    soup = fetch_html(BASE_URL)
    normalized = normalize_country(country)
    candidates: list[BurDocument] = []

    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        country_cell_text = " ".join(" ".join(cells[0].stripped_strings).split())
        if not country_cell_text:
            continue
        if normalize_country(country_cell_text) != normalized:
            continue

        for cell in cells[1:]:
            for anchor in cell.find_all("a", href=True):
                href = anchor["href"].strip()
                label = " ".join(anchor.get_text(strip=True).split())
                if not href:
                    continue

                target_url = urljoin(BASE_URL, href)
                pdf_url = target_url if href.lower().endswith(".pdf") else resolve_pdf_url(target_url)
                if not pdf_url:
                    continue

                full_context = f"{label} {cell.get_text(' ', strip=True)}"
                year = extract_year_from_text(full_context)
                candidates.append(
                    BurDocument(
                        country=country,
                        title=label or country_cell_text,
                        url=pdf_url,
                        year=year,
                    )
                )

    if not candidates:
        return None

    def sort_key(doc: BurDocument) -> tuple[int, str]:
        return (doc.year or 0, doc.title)

    return sorted(candidates, key=sort_key, reverse=True)[0]


def fetch_html(url: str) -> BeautifulSoup:
    response = requests.get(url, timeout=30, headers=REQUEST_HEADERS)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def resolve_pdf_url(page_url: str) -> Optional[str]:
    """Follow a UNFCCC document page and extract the first PDF asset link."""
    soup = fetch_html(page_url)
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.lower().endswith(".pdf"):
            return urljoin(page_url, href)
    return None


def download_document(doc: BurDocument) -> Path:
    ensure_storage_dir()
    response = requests.get(doc.url, timeout=60, headers=REQUEST_HEADERS)
    response.raise_for_status()
    with doc.destination.open("wb") as handle:
        handle.write(response.content)
    return doc.destination


def ensure_local_copy(country: str) -> Path:
    local_docs = list_local_documents(country)
    if local_docs:
        print(f"Found existing BUR for {country}: {local_docs[0]}")
        return local_docs[0]

    remote_doc = scrape_latest_bur(country)
    if remote_doc is None:
        raise RuntimeError(f"No BUR PDFs found for {country} at {BASE_URL}")

    print(f"Downloading latest BUR for {country}: {remote_doc.url}")
    return download_document(remote_doc)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and cache the most recent BUR PDF for a country."
    )
    parser.add_argument(
        "-c",
        "--country",
        required=True,
        help="Country to fetch (e.g. 'Cuba').",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    try:
        destination = ensure_local_copy(args.country)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Document ready at {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

