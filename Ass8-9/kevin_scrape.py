#!/usr/bin/env python3
"""
Scrape UNFCCC BURs page for a given country, download BUR PDFs, and extract
sections relevant to:

- GHG Inventory Module
- Adaptation and Vulnerability Module

Outputs JSON files following the project conventions, e.g.:
    {Country}_{PIFSection}_{DocType}.json

The script starts from the BURs landing page:
    https://unfccc.int/BURs
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urljoin, urlparse

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup  # type: ignore


BASE_URL = "https://unfccc.int"
BUR_LANDING_URL = f"{BASE_URL}/BURs"
REPORTS_URL = f"{BASE_URL}/reports"
REPORTS_AJAX_URL = f"{BASE_URL}/views/ajax"

REQUEST_TIMEOUT = 45
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


# Target PIF-style sections for this script.
SECTION_DEFINITIONS: Dict[str, Dict[str, object]] = {
    "GHG Inventory Module": {
        "bundle": "GHG_inventory_bundle.json",
        "directory": "GHG_inventory_module",
        # Common BUR headings for national GHG inventories.
        "headings": (
            r"^\s*[IVXLCDM]+\.\s*National\s+greenhouse\s+gas\s+inventory[^\n]*",
            r"^\s*National\s+greenhouse\s+gas\s+inventory[^\n]*",
            r"^\s*National\s+GHG\s+inventory[^\n]*",
            r"^\s*Greenhouse\s+gas\s+emissions[^\n]*",
        ),
        # Fallback full-section patterns if headings can't be located exactly.
        "patterns": (
            r"(National\s+greenhouse\s+gas\s+inventory.*?)(?=\n[A-Z][^\n]+|$)",
            r"(Greenhouse\s+gas\s+emissions.*?)(?=\n[A-Z][^\n]+|$)",
        ),
    },
    "Adaptation and Vulnerability Module": {
        "bundle": "Adaptation_vulnerability_bundle.json",
        "directory": "Adaptation_and_vulnerability_module",
        "headings": (
            r"^\s*[IVXLCDM]+\.\s*Vulnerability\s+and\s+adaptation[^\n]*",
            r"^\s*Vulnerability\s+and\s+adaptation[^\n]*",
            r"^\s*Climate\s+change\s+impacts\s+and\s+adaptation[^\n]*",
            r"^\s*Adaptation\s+actions[^\n]*",
        ),
        "patterns": (
            r"(Vulnerability\s+and\s+adaptation.*?)(?=\n[A-Z][^\n]+|$)",
            r"(Climate\s+change\s+impacts\s+and\s+adaptation.*?)(?=\n[A-Z][^\n]+|$)",
            r"(Adaptation\s+actions.*?)(?=\n[A-Z][^\n]+|$)",
        ),
    },
}


@dataclass
class PDFLink:
    """Representation of a BUR PDF."""

    title: str
    url: str
    source_doc: str  # e.g. BUR1, BUR2


def slugify(value: str) -> str:
    """Convert a string into a safe filesystem slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_{2,}", "_", value).strip("_")


def ensure_directory(path: Path) -> None:
    """Create a directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def load_cookies(filepath: Path) -> Dict[str, str]:
    """
    Load cookies from a JSON file (same simple format used in Alicia's scraper).
    Expected format: { "cookieName": "value", ... }
    """
    with open(filepath, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Cookie file must contain a JSON object of name/value pairs.")
    return {str(key): str(value) for key, value in data.items()}


def request_session(cookies: Dict[str, str] | None = None) -> requests.Session:
    """Create a configured requests session, optionally seeded with cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.max_redirects = 10
    if cookies:
        session.cookies.update(cookies)
    return session


def resolve_pdf_url(session: requests.Session, href: str) -> str | None:
    """
    Resolve a PDF URL, following intermediate detail pages if necessary.

    The BUR listing often links to a country detail page rather than the PDF
    directly. This mirrors the behaviour in the main UNFCCC scraper.
    """
    absolute_url = urljoin(BASE_URL, href)
    if absolute_url.lower().endswith(".pdf"):
        return absolute_url

    logging.debug("Resolving PDF from %s", absolute_url)
    try:
        response = session.get(absolute_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed to load detail page %s: %s", absolute_url, exc)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    for anchor in soup.select("a[href]"):
        link = anchor["href"]
        if link.lower().endswith(".pdf"):
            logging.debug("Found PDF %s within %s", link, absolute_url)
            return urljoin(BASE_URL, link)

    logging.warning("No PDF link found within %s", absolute_url)
    return None


def fetch_country_results_via_ajax(
    session: requests.Session, country: str, items_per_page: int = 50
) -> str | None:
    """
    Hit the Drupal AJAX endpoint backing https://unfccc.int/reports to retrieve
    the filtered country listing HTML fragments (same approach as the main
    scraper).
    """
    params = {
        "_wrapper_format": "drupal_ajax",
        "search3": country,
        "items_per_page": items_per_page,
        "view_name": "documents",
        "view_display_id": "block_4",
        "view_args": "",
        "view_path": "/reports",
        "view_base_path": "",
        "pager_element": 2,
        "_drupal_ajax": 1,
    }
    headers = {
        "Referer": BUR_LANDING_URL,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }

    logging.info("Fetching UNFCCC reports via AJAX for %s", country)
    response = session.get(
        REPORTS_AJAX_URL,
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        logging.warning(
            "Unexpected content type from AJAX endpoint (%s) for %s",
            content_type,
            country,
        )
        return None

    payload = response.json()
    html_fragments: List[str] = []

    if isinstance(payload, list):
        for command in payload:
            if isinstance(command, dict) and isinstance(command.get("data"), str):
                html_fragments.append(command["data"])
    elif isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, str):
            html_fragments.append(data)

    if not html_fragments:
        logging.info("AJAX endpoint returned no HTML fragments for %s", country)
        return None

    return "\n".join(html_fragments)


def deduce_doc_type(label: str) -> str:
    """
    Infer a BUR-like label (BUR1, BUR2, etc.) from visible text.
    Falls back to 'BUR' if only generic BUR is present.
    """
    upper = label.upper()
    match = re.search(r"(BUR\s*\d+)", upper)
    if match:
        return match.group(1).replace(" ", "")
    if "BIENNIAL UPDATE REPORT" in upper or "BUR" in upper:
        return "BUR"
    return "UNKNOWN"


def get_bur_page(session: requests.Session) -> str:
    """Fetch the main BUR listing page HTML."""
    logging.info("Fetching BUR landing page %s", BUR_LANDING_URL)
    response = session.get(BUR_LANDING_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def get_country_bur_links(html: str, country: str, session: requests.Session) -> List[PDFLink]:
    """
    Parse the BUR listing HTML and return BUR PDFs for a given country.
    Uses table-row parsing (like Alicia's script) for more robust extraction.
    """
    soup = BeautifulSoup(html, "html.parser")
    pdf_links: List[PDFLink] = []
    seen: set[str] = set()

    # First, try table-row parsing (more robust, like Alicia's script)
    table_rows = soup.select("table tbody tr")
    if table_rows:
        for row in table_rows:
            cells = row.select("td")
            if not cells:
                continue
            row_text = " ".join(cell.get_text(" ", strip=True) for cell in cells)
            if country.lower() not in row_text.lower():
                continue

            # Check if this row mentions BUR
            if "bur" not in row_text.lower() and "biennial update report" not in row_text.lower():
                continue

            file_cell_text = cells[-1].get_text(" ", strip=True).lower()
            if "pdf" not in file_cell_text:
                continue

            link_element = row.select_one("a[href*='/documents/']") or row.select_one("a[href]")
            if not link_element:
                continue
            href = link_element.get("href")
            if not href:
                continue

            doc_type = deduce_doc_type(row_text)
            if not doc_type.upper().startswith("BUR"):
                continue

            pdf_url = resolve_pdf_url(session, href)
            if not pdf_url:
                continue
            if pdf_url in seen:
                continue
            seen.add(pdf_url)

            doc_name = cells[0].get_text(" ", strip=True) if cells else doc_type
            title = doc_name or f"{country} BUR"
            pdf_links.append(PDFLink(title=title, url=pdf_url, source_doc=doc_type))
    else:
        # Fallback to anchor-based parsing if no table rows found
        anchors = soup.select("a[href]")
        for a in anchors:
            href = a.get("href") or ""

            # Use nearby text to check for the country name and context first.
            parent = a.find_parent(["tr", "li", "div", "p"]) or a
            text_blob = parent.get_text(" ", strip=True)
            combined = f"{a.get_text(' ', strip=True)} {text_blob} {href}"

            if country.lower() not in combined.lower():
                continue

            # Decide if this looks like a BUR based on the label text.
            doc_type = deduce_doc_type(combined)
            if not doc_type.upper().startswith("BUR"):
                continue

            pdf_url = resolve_pdf_url(session, href)
            if not pdf_url:
                continue

            if pdf_url in seen:
                continue
            seen.add(pdf_url)

            title = a.get_text(" ", strip=True) or f"{country} BUR"
            pdf_links.append(PDFLink(title=title, url=pdf_url, source_doc=doc_type))

    logging.info("Found %d BUR PDFs for %s", len(pdf_links), country)
    return pdf_links


def parse_reports_pdf_links(
    session: requests.Session, html: str, country: str
) -> List[PDFLink]:
    """
    Parse HTML returned by the reports Ajax endpoint and extract BUR PDFs.
    """
    soup = BeautifulSoup(html, "html.parser")
    pdf_links: List[PDFLink] = []
    seen: set[str] = set()

    table_rows = soup.select("table tbody tr")
    if table_rows:
        for row in table_rows:
            cells = row.select("td")
            if not cells:
                continue
            row_text = " ".join(cell.get_text(" ", strip=True) for cell in cells)
            if country.lower() not in row_text.lower():
                continue

            doc_type = deduce_doc_type(row_text)
            if not doc_type.upper().startswith("BUR"):
                continue

            link_element = row.select_one("a[href]")
            if not link_element:
                continue
            href = link_element.get("href")
            if not href:
                continue

            pdf_url = resolve_pdf_url(session, href)
            if not pdf_url:
                continue
            if pdf_url in seen:
                continue
            seen.add(pdf_url)

            title = link_element.get_text(" ", strip=True) or doc_type
            pdf_links.append(PDFLink(title=title, url=pdf_url, source_doc=doc_type))

        if pdf_links:
            return pdf_links

    # Fallback: scan anchors if table structure not present
    anchors = soup.select("a[href]")
    for anchor in anchors:
        href = anchor.get("href") or ""
        text_blob = anchor.get_text(" ", strip=True)
        parent = anchor.find_parent(["article", "div", "li", "p"])
        if parent:
            text_blob += " " + parent.get_text(" ", strip=True)

        if country.lower() not in text_blob.lower():
            continue

        doc_type = deduce_doc_type(text_blob)
        if not doc_type.upper().startswith("BUR"):
            continue

        pdf_url = resolve_pdf_url(session, href)
        if not pdf_url:
            continue
        if pdf_url in seen:
            continue
        seen.add(pdf_url)

        title = anchor.get_text(" ", strip=True) or doc_type
        pdf_links.append(PDFLink(title=title, url=pdf_url, source_doc=doc_type))

    return pdf_links


def get_bur_pdfs_for_country(session: requests.Session, country: str) -> List[PDFLink]:
    """
    Try Ajax-based discovery first; if that fails, fall back to scraping the
    BUR landing page HTML, then try the main reports page.
    """
    try:
        ajax_html = fetch_country_results_via_ajax(session, country)
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "AJAX fetch failed for %s: %s; falling back to BUR landing page.",
            country,
            exc,
        )
        ajax_html = None

    if ajax_html:
        pdf_links = parse_reports_pdf_links(session, ajax_html, country)
        if pdf_links:
            logging.info(
                "Using AJAX pipeline, found %d BUR PDFs for %s",
                len(pdf_links),
                country,
            )
            return pdf_links
        logging.info(
            "AJAX pipeline returned no BUR PDFs for %s; falling back to BUR landing page.",
            country,
        )

    # Try BUR landing page
    html = get_bur_page(session)
    pdf_links = get_country_bur_links(html, country, session)
    if pdf_links:
        return pdf_links

    # Fallback: try main reports page with country search
    logging.info("Trying main reports page for %s", country)
    try:
        params = {"search_api_fulltext": country}
        response = session.get(REPORTS_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        reports_html = response.text
        pdf_links = get_country_bur_links(reports_html, country, session)
        if pdf_links:
            return pdf_links
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed to fetch reports page for %s: %s", country, exc)

    return []


def download_pdf(session: requests.Session, pdf: PDFLink, download_dir: Path) -> Path:
    """Download a PDF if not already present."""
    ensure_directory(download_dir)
    parsed = urlparse(pdf.url)
    filename = Path(parsed.path).name or f"{slugify(pdf.title)}.pdf"
    dest = download_dir / filename

    if dest.exists():
        logging.info("Skipping download (exists): %s", dest.name)
        return dest

    logging.info("Downloading %s", pdf.url)
    with session.get(pdf.url, stream=True, timeout=REQUEST_TIMEOUT) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                if chunk:
                    fh.write(chunk)

    return dest


def clean_extracted_text(text: str) -> str:
    """Normalize extracted PDF text for consistent regex processing."""
    text = text.replace("\r", "\n")
    text = re.sub(r"-\n(?=\w)", "", text)  # fix hyphenated line breaks
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract_sections_from_pdf(file_path: Path, section_definitions: Dict[str, Dict[str, object]]) -> Dict[str, str]:
    """
    Extract configured sections from a PDF using heading / pattern regexes.
    Closely mirrors the logic in `pdfextraction/alicia_ass7_pdfextraction/scrape_unfccc.py`
    but focused on the two modules.
    """
    logging.info("Extracting sections from %s", file_path.name)
    with fitz.open(file_path) as doc:
        pages = [page.get_text("text") for page in doc]
    combined_text = clean_extracted_text("\n".join(pages))

    extracted: Dict[str, str] = {}
    section_spans: Dict[str, Tuple[int, int]] = {}
    heading_flags = re.IGNORECASE | re.MULTILINE

    for section, config in section_definitions.items():
        raw_headings = config.get("headings", [])
        if isinstance(raw_headings, (str, bytes)):
            heading_patterns: Iterable[str] = [raw_headings]  # type: ignore[list-item]
        else:
            heading_patterns = list(raw_headings)  # type: ignore[assignment]

        heading_match = None
        for pattern in heading_patterns:
            try:
                heading_match = re.search(pattern, combined_text, flags=heading_flags)
            except re.error as exc:
                logging.error("Invalid heading regex '%s': %s", pattern, exc)
                continue
            if heading_match:
                section_spans[section] = (heading_match.start(), heading_match.end())
                logging.debug("Located heading for %s via pattern %s", section, pattern)
                break

        if section in section_spans:
            continue

        # Fallback to full-section patterns.
        raw_patterns = config.get("patterns", [])
        if isinstance(raw_patterns, (str, bytes)):
            patterns: Iterable[str] = [raw_patterns]  # type: ignore[list-item]
        else:
            patterns = list(raw_patterns)  # type: ignore[assignment]

        for pattern in patterns:
            try:
                match = re.search(pattern, combined_text, flags=re.IGNORECASE | re.DOTALL)
            except re.error as exc:
                logging.error("Invalid regex '%s': %s", pattern, exc)
                continue
            if match:
                section_spans[section] = (match.start(), match.end())
                logging.debug("Matched section %s via fallback pattern %s", section, pattern)
                break

        if section not in section_spans:
            logging.warning("Section '%s' not found in %s", section, file_path.name)

    if not section_spans:
        return extracted

    ordered_sections = sorted(section_spans.items(), key=lambda item: item[1][0])
    for idx, (section, (start, _)) in enumerate(ordered_sections):
        next_start = (
            ordered_sections[idx + 1][1][0]
            if idx + 1 < len(ordered_sections)
            else len(combined_text)
        )

        # Include preceding roman numeral label if present.
        prev_nl = combined_text.rfind("\n", 0, start)
        if prev_nl != -1:
            line = combined_text[prev_nl + 1 : start]
            if re.match(r"^\s*[ivxlcdm]+\.\s*$", line, flags=re.IGNORECASE):
                start = prev_nl + 1

        section_text = combined_text[start:next_start].strip()
        if section_text:
            extracted[section] = section_text
        else:
            logging.warning("Section '%s' text empty after extraction in %s", section, file_path.name)

    return extracted


def build_json_entry(
    country: str,
    section: str,
    source_doc: str,
    url: str,
    text: str,
    timestamp: datetime,
) -> Dict[str, object]:
    """Return a structured JSON entry ready for persistence."""
    return {
        "country": country,
        "section": section,
        "source_doc": source_doc,
        "doc_url": url,
        "extracted_text": text,
        "created_utc": timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def write_section_outputs(
    data_dir: Path,
    section: str,
    entries: List[Dict[str, object]],
) -> None:
    """
    Write:
    - one bundle JSON for the section (all countries/docs)
    - per-document JSON files named {Country}_{PIFSection}_{DocType}.json
    """
    ensure_directory(data_dir)
    section_config = SECTION_DEFINITIONS.get(section, {})
    bundle_name = section_config.get("bundle") or f"{slugify(section)}_bundle.json"
    directory_name = section_config.get("directory") or slugify(section)

    section_dir = data_dir / directory_name
    ensure_directory(section_dir)

    bundle_path = data_dir / bundle_name
    if bundle_path.exists():
        with open(bundle_path, "r", encoding="utf-8") as handle:
            existing_entries = json.load(handle)
    else:
        existing_entries = []

    all_entries = existing_entries + entries
    all_entries_sorted = sorted(
        all_entries,
        key=lambda e: (e.get("country", ""), e.get("source_doc", ""), e.get("created_utc", "")),
    )
    with open(bundle_path, "w", encoding="utf-8") as handle:
        json.dump(all_entries_sorted, handle, ensure_ascii=False, indent=2)
    logging.info("Wrote %s (%d records)", bundle_path, len(all_entries_sorted))

    # Per-document JSONs
    docs: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for entry in entries:
        key = (str(entry.get("country", "")), str(entry.get("source_doc", "")))
        docs.setdefault(key, []).append(entry)

    for (country, source_doc), doc_entries in docs.items():
        section_pascal = "".join(word.capitalize() for word in section.split())
        doc_name = f"{{{country}}}_{{{section_pascal}}}_{{{source_doc or 'document'}}}.json"
        doc_path = section_dir / doc_name
        with open(doc_path, "w", encoding="utf-8") as handle:
            json.dump(doc_entries, handle, ensure_ascii=False, indent=2)
        logging.debug("Wrote %s", doc_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape UNFCCC BURs for GHG Inventory and Adaptation/Vulnerability modules.",
    )
    parser.add_argument(
        "--country",
        required=True,
        help="Country name to filter BURs (e.g., 'Cuba', 'Jordan', 'Guinea-Bissau').",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional override for the output data directory (default: ./data_bur_modules).",
    )
    parser.add_argument(
        "--download-dir",
        default=None,
        help="Optional override for the PDF download directory (default: ./downloads_bur_modules).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )
    parser.add_argument(
        "--local-pdf",
        default=None,
        help="Optional path to a local BUR PDF file to process instead of scraping UNFCCC.",
    )
    parser.add_argument(
        "--cookies-file",
        default=None,
        help="Optional path to JSON file with unfccc.int cookies (same format as Alicia's scraper).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )

    country = args.country.strip()
    if not country:
        raise SystemExit("Country name cannot be empty.")

    output_root = (
        Path(args.output_dir)
        if args.output_dir
        else Path(__file__).resolve().parent / "data_bur_modules"
    )
    download_root = (
        Path(args.download_dir)
        if args.download_dir
        else Path(__file__).resolve().parent / "downloads_bur_modules"
    )
    ensure_directory(output_root)
    ensure_directory(download_root)

    timestamp = datetime.now(timezone.utc)
    collected: Dict[str, List[Dict[str, object]]] = {
        section: [] for section in SECTION_DEFINITIONS
    }

    # If a local PDF is provided, skip all web scraping and just process it.
    if args.local_pdf:
        pdf_path = Path(args.local_pdf).expanduser().resolve()
        if not pdf_path.exists():
            raise SystemExit(f"Local PDF not found: {pdf_path}")

        logging.info("Processing local BUR PDF: %s", pdf_path)
        sections = extract_sections_from_pdf(pdf_path, SECTION_DEFINITIONS)
        source_doc = deduce_doc_type(pdf_path.name)
        for section_name, text in sections.items():
            if not text:
                continue
            entry = build_json_entry(
                country=country,
                section=section_name,
                source_doc=source_doc,
                url=str(pdf_path),
                text=text,
                timestamp=timestamp,
            )
            collected[section_name].append(entry)
    else:
        cookies: Dict[str, str] | None = None
        if args.cookies_file:
            cookies = load_cookies(Path(args.cookies_file).expanduser().resolve())

        session = request_session(cookies)
        pdf_links = get_bur_pdfs_for_country(session, country)
        if not pdf_links:
            logging.warning("No BUR PDFs found for %s on %s", country, BUR_LANDING_URL)
            return

        for pdf in pdf_links:
            pdf_path = download_pdf(session, pdf, download_root)
            sections = extract_sections_from_pdf(pdf_path, SECTION_DEFINITIONS)
            for section_name, text in sections.items():
                if not text:
                    continue
                entry = build_json_entry(
                    country=country,
                    section=section_name,
                    source_doc=pdf.source_doc,
                    url=pdf.url,
                    text=text,
                    timestamp=timestamp,
                )
                collected[section_name].append(entry)

    for section_name, entries in collected.items():
        if entries:
            write_section_outputs(output_root, section_name, entries)
        else:
            logging.warning(
                "No entries extracted for section '%s' for %s", section_name, country
            )


if __name__ == "__main__":
    main()


