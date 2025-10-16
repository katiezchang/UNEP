#!/usr/bin/env python3
"""
Beautiful Soup Web Scraper – Assignment Submission

Scrapes the Fake Python Jobs board and extracts job title, company, location, and application URL.
Optionally filters by a keyword (case-insensitive) that must appear in the job title.

Site scraped (static practice site maintained by Real Python):
https://realpython.github.io/fake-jobs/

Usage:
    python scraper.py --keyword python --out jobs.csv
    python scraper.py                     # defaults: no keyword filter, prints to stdout
    python scraper.py --keyword data --limit 5
    python scraper.py --help

Notes:
- This script targets a static practice site suitable for scraping.
- For dynamic pages you may need Selenium or similar tools.
- Always respect sites' Terms of Service and robots.txt when scraping.
"""
import sys
import argparse
import csv
from typing import Iterable, List, Dict, Optional

import requests
from bs4 import BeautifulSoup

URL = "https://realpython.github.io/fake-jobs/"


def fetch_html(url: str, timeout: float = 15.0) -> str:
    """Fetch raw HTML from URL and return text content."""
    resp = requests.get(url, timeout=timeout, headers={
        "User-Agent": "AssignmentScraper/1.0 (+https://example.edu)"
    })
    resp.raise_for_status()
    return resp.text


def parse_jobs(html: str) -> List[Dict[str, str]]:
    """Parse the HTML and return a list of job dicts with title, company, location, url."""
    soup = BeautifulSoup(html, "html.parser")
    results = soup.find(id="ResultsContainer")
    if results is None:
        return []

    job_cards = results.find_all("div", class_="card-content")
    jobs = []
    for card in job_cards:
        title_el = card.find("h2", class_="title")
        company_el = card.find("h3", class_="company")
        location_el = card.find("p", class_="location")
        link_els = card.find_all("a")

        # Basic defensive checks
        title = title_el.get_text(strip=True) if title_el else ""
        company = company_el.get_text(strip=True) if company_el else ""
        location = location_el.get_text(strip=True) if location_el else ""
        # The second <a> is the "Apply" link on this site
        url = ""
        if len(link_els) >= 2 and link_els[1].has_attr("href"):
            url = link_els[1]["href"]

        if any([title, company, location, url]):
            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "apply_url": url,
            })
    return jobs


def filter_jobs(jobs: Iterable[Dict[str, str]], keyword: Optional[str]) -> List[Dict[str, str]]:
    """Filter jobs by keyword in title (case-insensitive). If keyword is None/empty, returns all."""
    if not keyword:
        return list(jobs)
    kw = keyword.lower()
    return [j for j in jobs if kw in j.get("title", "").lower()]


def to_csv(jobs: Iterable[Dict[str, str]], fileobj):
    """Write jobs to CSV file-like object with header."""
    fieldnames = ["title", "company", "location", "apply_url"]
    writer = csv.DictWriter(fileobj, fieldnames=fieldnames)
    writer.writeheader()
    for j in jobs:
        writer.writerow(j)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Scrape the Fake Python Jobs site with Beautiful Soup.")
    parser.add_argument("--keyword", "-k", type=str, default=None,
                        help="Filter by keyword appearing in the job title (case-insensitive).")
    parser.add_argument("--out", "-o", type=str, default=None,
                        help="Optional output CSV path. If omitted, prints to stdout.")
    parser.add_argument("--limit", "-n", type=int, default=None,
                        help="Optional limit on number of rows to output.")
    args = parser.parse_args(argv)

    try:
        html = fetch_html(URL)
        jobs = parse_jobs(html)
        jobs = filter_jobs(jobs, args.keyword)

        if args.limit is not None and args.limit >= 0:
            jobs = jobs[:args.limit]

        if args.out:
            with open(args.out, "w", newline="", encoding="utf-8") as f:
                to_csv(jobs, f)
            print(f"Wrote {len(jobs)} jobs to {args.out}")
        else:
            # Print nicely to stdout as CSV
            to_csv(jobs, sys.stdout)

        return 0
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        return 2
    except requests.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
