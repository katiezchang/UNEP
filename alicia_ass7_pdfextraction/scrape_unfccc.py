#!/usr/bin/env python3
"""
Scrape and extract PIF-relevant sections from UNFCCC country reports.

Expected usage:
    python scrape_unfccc.py --country "Cuba"

Dependencies:
    pip install requests beautifulsoup4 PyMuPDF
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Iterable
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup  # type: ignore
except ImportError as import_error:  # pragma: no cover - dependency guard
    raise SystemExit(
        "Missing dependencies. Please run: pip install requests beautifulsoup4"
    ) from import_error

try:
    import fitz  # PyMuPDF
except ImportError as import_error:  # pragma: no cover - dependency guard
    raise SystemExit(
        "Missing dependency 'PyMuPDF'. Please run: pip install PyMuPDF"
    ) from import_error


BASE_URL = "https://unfccc.int"
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

SECTION_DEFINITIONS: Dict[str, Dict[str, object]] = {
    "Institutional framework for climate action": {
        "bundle": "Institutional_framework_bundle.json",
        "directory": "Institutional_framework_for_climate_action",
        "headings": (
            r"^\s*[ivxlcdm]+\.\s*Institutional\sframework[^\n]*",
            r"^\s*Institutional\sframework[^\n]*",
            r"^\s*Institutional\sarrangements[^\n]*",
        ),
        "patterns": (
            r"(Institutional\sframework(?:\sfor\s(?:climate|mitigation|adaptation|the\simplementation))?.*?)"
            r"(?=\n[A-Z][^\n]+|$)",
            r"(Institutional\sarrangements\s(?:for|on)\s(?:climate|implementation).*?)"
            r"(?=\n[A-Z][^\n]+|$)",
            r"(Institutional\ssetup.*?)(?=\n[A-Z][^\n]+|$)",
        )
    },
    "National policy framework": {
        "bundle": "National_policy_framework_bundle.json",
        "directory": "National_policy_framework",
        "headings": (
            r"^\s*[ivxlcdm]+\.\s*National\s(?:policy|strategic)\sframework[^\n]*",
            r"^\s*National\s(?:policy|strategic)\sframework[^\n]*",
            r"^\s*Policy\sand\sregulatory\sframework[^\n]*",
        ),
        "patterns": (
            r"(National\s(?:policy|strategic)\sframework.*?)(?=\n[A-Z][^\n]+|$)",
            r"(National\s(?:strategy|policies)\s(?:for|on)\sclimate.*?)(?=\n[A-Z][^\n]+|$)",
            r"(Policy\sand\sregulatory\sframework.*?)(?=\n[A-Z][^\n]+|$)",
        )
    },
}

DOC_TYPE_HINTS: Tuple[Tuple[str, str], ...] = (
    ("BUR", "BUR"),
    ("Biennial Update Report", "BUR"),
    ("BTR", "BTR"),
    ("Biennial Transparency Report", "BTR"),
    ("NDC", "NDC"),
    ("Nationally Determined Contribution", "NDC"),
    ("National Communication", "NC"),
    ("NC", "NC"),
    ("Fourth National Communication", "NC4"),
    ("Third National Communication", "NC3"),
    ("Second National Communication", "NC2"),
    ("Initial National Communication", "NC1"),
)

TARGET_DOC_PREFIXES: Tuple[str, ...] = ("BUR", "BTR", "NDC", "NC")


@dataclass
class PDFLink:
    """Representation of a PDF resource of interest."""

    title: str
    url: str
    source_doc: str
    local_path: Optional[Path] = None


def slugify(value: str) -> str:
    """Convert a string into a safe filesystem slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_{2,}", "_", value).strip("_")


def ensure_directory(path: Path) -> None:
    """Create a directory path if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)


def request_session(cookies: Optional[Dict[str, str]] = None) -> requests.Session:
    """Create a configured requests session."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.max_redirects = 10
    if cookies:
        session.cookies.update(cookies)
    return session


def get_country_page(session: requests.Session, country_name: str) -> Tuple[str, str]:
    """
    Retrieve the HTML for the UNFCCC reports listing filtered by country.

    The site is Drupal-based; the simplest approach is to hit the reports
    listing with a full-text filter, then filter in get_pdf_links.
    """
    params = {"search_api_fulltext": country_name}
    logging.info("Fetching report listing for %s", country_name)
    response = session.get(REPORTS_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    if "_Incapsula_Resource" in response.text or "Request unsuccessful" in response.text:
        logging.error(
            "Blocked by site protection when requesting %s. Try refreshing cookies or rerunning "
            "with a cookies file captured directly from a successful browser request.",
            response.url,
        )
    logging.debug("Resolved listing URL: %s", response.url)
    return response.text, response.url


def fetch_country_results_via_ajax(session: requests.Session, country_name: str, items_per_page: int = 50) -> Optional[str]:
    """
    Query the Drupal views AJAX endpoint to retrieve filtered HTML for a country.

    Returns the concatenated HTML snippets if successful, otherwise None.
    """
    params = {
        "_wrapper_format": "drupal_ajax",
        "search3": country_name,
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
        "Referer": REPORTS_URL,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    logging.info("Fetching AJAX listings for %s", country_name)
    response = session.get(
        REPORTS_AJAX_URL,
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        logging.warning("Unexpected content type from AJAX endpoint: %s", content_type)
        return None

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        logging.error("Failed to decode AJAX response JSON: %s", exc)
        return None

    html_fragments: List[str] = []
    if isinstance(payload, list):
        for command in payload:
            if not isinstance(command, dict):
                continue
            data = command.get("data")
            if isinstance(data, str):
                html_fragments.append(data)
    elif isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, str):
            html_fragments.append(data)

    if not html_fragments:
        logging.warning("AJAX endpoint returned no HTML fragments for %s", country_name)
        return None

    combined_html = "\n".join(html_fragments)
    logging.debug("Retrieved %d HTML fragments via AJAX", len(html_fragments))
    return combined_html


def deduce_doc_type(label: str) -> str:
    """Infer a canonical source doc label from link text or URL."""
    upper_label = label.upper()
    for needle, mapped in DOC_TYPE_HINTS:
        if needle.upper() in upper_label:
            bur_match = re.search(r"(BUR\s*\d+)", upper_label)
            if bur_match:
                return bur_match.group(1).replace(" ", "")
            btr_match = re.search(r"(BTR\s*\d+)", upper_label)
            if btr_match:
                return btr_match.group(1).replace(" ", "")
            ndc_match = re.search(r"(NDC\s*\d+)", upper_label)
            if ndc_match:
                return ndc_match.group(1).replace(" ", "")
            return mapped
    # Fallback: return uppercase alphanumeric words to avoid Unknown
    fallback = re.findall(r"[A-Z]{2,}\d*", upper_label)
    return fallback[0] if fallback else "UNKNOWN"


def build_local_pdf_link(path: Path) -> PDFLink:
    """Create a PDFLink instance for a local PDF."""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Local PDF not found: {path}")
    title = path.stem
    doc_type = deduce_doc_type(title)
    url = path.resolve().as_uri()
    return PDFLink(title=title, url=url, source_doc=doc_type, local_path=path.resolve())


def resolve_pdf_url(session: requests.Session, href: str) -> Optional[str]:
    """Resolve a PDF URL, following detail pages if necessary."""
    absolute_url = urljoin(BASE_URL, href)
    if absolute_url.lower().endswith(".pdf"):
        return absolute_url

    logging.debug("Resolving PDF from %s", absolute_url)
    response = session.get(absolute_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for anchor in soup.select("a[href]"):
        link = anchor["href"]
        if link.lower().endswith(".pdf"):
            logging.debug("Found PDF %s within %s", link, absolute_url)
            return urljoin(BASE_URL, link)
    logging.warning("No PDF link found within %s", absolute_url)
    return None


def get_pdf_links(session: requests.Session, html: str, country_name: str) -> List[PDFLink]:
    """
    Extract all PDF links matching BUR, BTR, NDC, or NC for the provided country.
    """
    soup = BeautifulSoup(html, "html.parser")
    table_rows = soup.select("table tbody tr")
    pdf_links: List[PDFLink] = []
    seen_urls: set[str] = set()

    if table_rows:
        for row in table_rows:
            cells = row.select("td")
            if not cells:
                continue
            row_text = " ".join(cell.get_text(" ", strip=True) for cell in cells)
            if country_name.lower() not in row_text.lower():
                continue

            file_cell_text = cells[-1].get_text(" ", strip=True).lower()
            if "pdf" not in file_cell_text:
                continue

            link_element = row.select_one("a[href*='/documents/']")
            if not link_element:
                continue
            href = link_element.get("href")
            if not href:
                continue

            doc_name = cells[0].get_text(" ", strip=True)
            doc_type_text = row_text
            doc_type = deduce_doc_type(doc_type_text or doc_name)

            if doc_type == "UNKNOWN":
                continue
            normalized_type = re.sub(r"\s+", "", doc_type.upper())
            if not any(normalized_type.startswith(prefix) for prefix in TARGET_DOC_PREFIXES):
                continue

            pdf_url = resolve_pdf_url(session, href)
            if not pdf_url:
                continue
            if pdf_url in seen_urls:
                continue
            seen_urls.add(pdf_url)
            title = doc_name or doc_type
            pdf_links.append(PDFLink(title=title, url=pdf_url, source_doc=doc_type))
    else:
        anchors = soup.select("a[href]")
        for anchor in anchors:
            href = anchor.get("href")
            if not href:
                continue
            parent = anchor.find_parent(["article", "div", "li"])
            parent_text = parent.get_text(" ", strip=True) if parent else ""
            text_blob = " ".join(
                filter(None, [anchor.get_text(strip=True), parent_text, href])
            )
            if country_name.lower() not in text_blob.lower():
                continue

            doc_type = deduce_doc_type(text_blob)
            if doc_type == "UNKNOWN":
                continue

            pdf_url = resolve_pdf_url(session, href)
            if not pdf_url:
                continue
            if pdf_url in seen_urls:
                continue
            seen_urls.add(pdf_url)
            title = anchor.get_text(strip=True) or doc_type
            pdf_links.append(PDFLink(title=title, url=pdf_url, source_doc=doc_type))

    logging.info("Identified %d candidate PDFs", len(pdf_links))
    return pdf_links


def download_pdf(session: requests.Session, pdf: PDFLink, download_dir: Path) -> Path:
    """Download a PDF if not already present."""
    if pdf.local_path:
        logging.info("Using local PDF: %s", pdf.local_path)
        return pdf.local_path

    ensure_directory(download_dir)
    parsed = urlparse(pdf.url)
    filename = Path(parsed.path).name or slugify(pdf.title) + ".pdf"
    file_path = download_dir / filename

    if file_path.exists():
        logging.info("Skipping download (exists): %s", file_path.name)
        return file_path

    logging.info("Downloading %s", pdf.url)
    with session.get(pdf.url, stream=True, timeout=REQUEST_TIMEOUT) as response:
        response.raise_for_status()
        with open(file_path, "wb") as file_handle:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    file_handle.write(chunk)

    return file_path


def clean_extracted_text(text: str) -> str:
    """Normalize extracted PDF text for consistent regex processing."""
    text = text.replace("\r", "\n")
    text = re.sub(r"-\n(?=\w)", "", text)  # fix hyphenated line breaks
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract_sections_from_pdf(file_path: Path, section_definitions: Dict[str, Dict[str, object]]) -> Dict[str, str]:
    """Extract configured sections from a PDF using regex patterns."""
    logging.info("Extracting sections from %s", file_path.name)
    with fitz.open(file_path) as document:
        pages = [page.get_text("text") for page in document]
    combined_text = clean_extracted_text("\n".join(pages))

    extracted: Dict[str, str] = {}
    section_spans: Dict[str, Tuple[int, int]] = {}
    heading_flags = re.IGNORECASE | re.MULTILINE

    for section, config in section_definitions.items():
        # First, try to locate the heading.
        raw_headings = config.get("headings", [])
        if isinstance(raw_headings, (str, bytes)):
            heading_patterns: Iterable[str] = [raw_headings]  # type: ignore[list-item]
        elif isinstance(raw_headings, Iterable):
            heading_patterns = raw_headings  # type: ignore[assignment]
        else:
            heading_patterns = []

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

        # Fallback to legacy full-section patterns.
        raw_patterns = config.get("patterns", [])
        if isinstance(raw_patterns, (str, bytes)):
            patterns: Iterable[str] = [raw_patterns]  # type: ignore[list-item]
        elif isinstance(raw_patterns, Iterable):
            patterns = raw_patterns  # type: ignore[assignment]
        else:
            patterns = []

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
    for index, (section, (start, _)) in enumerate(ordered_sections):
        next_start = (
            ordered_sections[index + 1][1][0]
            if index + 1 < len(ordered_sections)
            else len(combined_text)
        )

        # Include preceding roman numeral label if present.
        previous_newline = combined_text.rfind("\n", 0, start)
        if previous_newline != -1:
            line = combined_text[previous_newline + 1 : start]
            if re.match(r"^\s*[ivxlcdm]+\.\s*$", line, flags=re.IGNORECASE):
                start = previous_newline + 1

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
        "stale": False,
    }


def merge_bundles(
    bundle_path: Path,
    new_entries: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    """Merge new entries with existing bundle file, marking stale ones as needed."""
    if bundle_path.exists():
        with open(bundle_path, "r", encoding="utf-8") as handle:
            existing_entries = json.load(handle)
    else:
        existing_entries = []

    key_fields = ("country", "section", "source_doc", "doc_url")
    existing_lookup = {
        tuple(entry[field] for field in key_fields): entry for entry in existing_entries
    }

    updated_entries: List[Dict[str, object]] = []
    seen_keys: set[Tuple[str, ...]] = set()

    for entry in new_entries:
        key = tuple(entry[field] for field in key_fields)
        seen_keys.add(key)
        existing = existing_lookup.get(key)
        if existing:
            if existing.get("extracted_text") == entry["extracted_text"]:
                entry["created_utc"] = existing.get("created_utc", entry["created_utc"])
                entry["stale"] = existing.get("stale", False)
            else:
                existing["stale"] = True
                updated_entries.append(existing)
        updated_entries.append(entry)

    for key, entry in existing_lookup.items():
        if key not in seen_keys:
            entry["stale"] = True
            updated_entries.append(entry)

    updated_entries.sort(key=lambda item: (item["country"], item["source_doc"], item["created_utc"]))
    return updated_entries


def write_section_outputs(
    data_dir: Path,
    section: str,
    entries: List[Dict[str, object]],
) -> None:
    """Persist bundle and per-document JSONs for a section."""
    ensure_directory(data_dir)
    section_config = SECTION_DEFINITIONS.get(section, {})
    bundle_name = section_config.get("bundle") or f"{slugify(section)}_bundle.json"
    directory_name = section_config.get("directory") or slugify(section)

    section_dir = data_dir / directory_name
    ensure_directory(section_dir)

    bundle_path = data_dir / bundle_name
    merged_entries = merge_bundles(bundle_path, entries)

    with open(bundle_path, "w", encoding="utf-8") as handle:
        json.dump(merged_entries, handle, ensure_ascii=False, indent=2)
    logging.info("Wrote %s (%d records)", bundle_path, len(merged_entries))

    # Write per source_doc files inside section directory for inspection.
    docs: Dict[str, List[Dict[str, object]]] = {}
    for entry in entries:
        docs.setdefault(entry["source_doc"], []).append(entry)

    for source_doc, doc_entries in docs.items():
        doc_name = slugify(source_doc or "document") + ".json"
        doc_path = section_dir / doc_name
        with open(doc_path, "w", encoding="utf-8") as handle:
            json.dump(doc_entries, handle, ensure_ascii=False, indent=2)
        logging.debug("Wrote %s", doc_path)


def main(
    country: str,
    output_root: Optional[Path] = None,
    download_root: Optional[Path] = None,
    cookies: Optional[Dict[str, str]] = None,
    local_pdfs: Optional[List[Path]] = None,
    local_pdf_dir: Optional[Path] = None,
    skip_scrape: bool = False,
) -> None:
    """End-to-end pipeline orchestrator."""
    session = request_session(cookies=cookies)
    pdf_links: List[PDFLink] = []

    if not skip_scrape:
        try:
            ajax_html = fetch_country_results_via_ajax(session, country)
            if ajax_html:
                logging.info("Processing AJAX listings for %s", country)
                pdf_links.extend(get_pdf_links(session, ajax_html, country))
            else:
                html, resolved_url = get_country_page(session, country)
                logging.info("Processing listings from %s", resolved_url)
                pdf_links.extend(get_pdf_links(session, html, country))
        except requests.HTTPError as exc:
            logging.error("Failed to scrape UNFCCC site: %s", exc)
        except Exception as exc:  # pragma: no cover - network guard
            logging.error("Unexpected scraping error: %s", exc)

    local_pdfs = local_pdfs or []
    for local_path in local_pdfs:
        try:
            pdf_links.append(build_local_pdf_link(local_path))
        except Exception as exc:
            logging.error("Failed to register local PDF %s: %s", local_path, exc)

    if local_pdf_dir:
        for pdf_path in sorted(Path(local_pdf_dir).glob("*.pdf")):
            try:
                pdf_links.append(build_local_pdf_link(pdf_path))
            except Exception as exc:
                logging.error("Failed to register local PDF %s: %s", pdf_path, exc)

    deduped: List[PDFLink] = []
    seen_urls: set[str] = set()
    for link in pdf_links:
        key = link.url if link.url else str(link.local_path)
        if key in seen_urls:
            continue
        seen_urls.add(key)
        deduped.append(link)
    pdf_links = deduped

    if not pdf_links:
        logging.warning("No PDFs found for %s. Exiting.", country)
        return

    timestamp = datetime.now(timezone.utc)
    output_root = output_root or Path(__file__).resolve().parent / "data"
    download_root = download_root or Path(__file__).resolve().parent / "downloads"
    ensure_directory(output_root)
    ensure_directory(download_root)

    collected: Dict[str, List[Dict[str, object]]] = {
        section: [] for section in SECTION_DEFINITIONS
    }

    for pdf in pdf_links:
        file_path = download_pdf(session, pdf, download_root)
        sections = extract_sections_from_pdf(file_path, SECTION_DEFINITIONS)
        for section_name, text in sections.items():
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
            logging.warning("No entries extracted for section '%s'", section_name)


def load_cookies(filepath: Path) -> Dict[str, str]:
    """Load cookies from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Cookie file must contain a JSON object of name/value pairs.")
    # Ensure all values are strings
    return {str(key): str(value) for key, value in data.items()}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Scrape UNFCCC reports for PIF sections.")
    parser.add_argument("--country", required=True, help="Country name to filter UNFCCC reports.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional override for the output data directory.",
    )
    parser.add_argument(
        "--download-dir",
        default=None,
        help="Optional override for the PDF download directory.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )
    parser.add_argument(
        "--cookies-file",
        default=None,
        help="Optional path to a JSON file containing cookie name/value pairs to bypass WAF.",
    )
    parser.add_argument(
        "--local-pdf",
        action="append",
        default=[],
        help="Path to a local PDF to process (can be passed multiple times).",
    )
    parser.add_argument(
        "--local-pdf-dir",
        default=None,
        help="Process all PDFs inside this directory.",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip remote scraping and use only local PDFs.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    arguments = parse_args()
    logging.basicConfig(
        level=getattr(logging, arguments.log_level.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )
    output_dir = Path(arguments.output_dir) if arguments.output_dir else None
    download_dir = Path(arguments.download_dir) if arguments.download_dir else None

    cookies: Optional[Dict[str, str]] = None
    if arguments.cookies_file:
        cookies = load_cookies(Path(arguments.cookies_file))

    local_pdf_paths = [Path(item) for item in arguments.local_pdf] if arguments.local_pdf else None
    local_pdf_directory = Path(arguments.local_pdf_dir) if arguments.local_pdf_dir else None

    try:
        main(
            arguments.country,
            output_dir,
            download_dir,
            cookies,
            local_pdf_paths,
            local_pdf_directory,
            arguments.skip_scrape,
        )
    except requests.HTTPError as err:
        logging.error("HTTP error: %s", err)
        sys.exit(1)
    except Exception as err:  # pragma: no cover - top-level guard
        logging.exception("Unexpected error: %s", err)
        sys.exit(1)

