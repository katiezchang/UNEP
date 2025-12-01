import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber
import requests
from dotenv import load_dotenv

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# Load environment variables from .env if present
load_dotenv()


@dataclass
class SupabaseConfig:
    url: str
    api_key: str
    table: str = "country_sections"
    country_column: str = "country"
    sections_column: str = "sections"

    @classmethod
    def read_from_pif_generator_rtf(cls) -> Tuple[Optional[str], Optional[str]]:
        """
        Read Supabase credentials from PIF Generator/SupaBase Info.rtf file.
        Returns (url, api_key) tuple or (None, None) if not found.
        """
        try:
            script_dir = Path(__file__).parent.resolve()
            project_root = script_dir.parent
            rtf_path = project_root / "PIF Generator" / "SupaBase Info.rtf"
            
            if not rtf_path.exists():
                return None, None
            
            with open(rtf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract URL and API key from RTF content
            url = None
            api_key = None
            
            # Look for URL pattern
            url_match = re.search(r'Project URL:\s*(https?://[^\s\\}]+)', content, re.IGNORECASE)
            if url_match:
                url = url_match.group(1).rstrip('\\').rstrip('}').strip()
            
            # Look for API key pattern (JWT token format: three parts separated by dots)
            # Handle both "API KEY:" and "Anon public API KEY:" formats
            api_key_match = re.search(r'(?:Anon public )?API KEY:\s*([A-Za-z0-9_\-\.]+)', content, re.IGNORECASE)
            if api_key_match:
                api_key = api_key_match.group(1).rstrip('}').rstrip('\\').strip()
            
            return url, api_key
        except Exception:
            return None, None

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        """
        Read Supabase configuration from environment variables or PIF Generator folder.

        First tries environment variables, then falls back to PIF Generator/SupaBase Info.rtf

        Required:
        - SUPABASE_URL
        - SUPABASE_API_KEY

        Optional (with defaults):
        - SUPABASE_TABLE
        - SUPABASE_COUNTRY_COLUMN
        - SUPABASE_SECTIONS_COLUMN
        """
        url = os.getenv("SUPABASE_URL")
        api_key = os.getenv("SUPABASE_API_KEY")

        # If not in environment, try reading from PIF Generator folder
        if not url or not api_key:
            pif_url, pif_api_key = cls.read_from_pif_generator_rtf()
            if pif_url:
                url = pif_url
            if pif_api_key:
                api_key = pif_api_key

        if not url or not api_key:
            raise RuntimeError(
                "Supabase config missing. Please set SUPABASE_URL and SUPABASE_API_KEY "
                "environment variables (e.g. in a .env file), or ensure PIF Generator/SupaBase Info.rtf exists."
            )

        table = os.getenv("SUPABASE_TABLE", "country_sections")
        country_column = os.getenv("SUPABASE_COUNTRY_COLUMN", "country")
        sections_column = os.getenv("SUPABASE_SECTIONS_COLUMN", "sections")

        return cls(
            url=url.rstrip("/"),
            api_key=api_key,
            table=table,
            country_column=country_column,
            sections_column=sections_column,
        )


SECTION_NAMES = [
    "NDC Tracking Module",
    "Support Needed and Received Module",
    "Other baseline initiatives",
]

# Keyword patterns used as a fallback for documents that do not
# contain the explicit module headings (e.g. BURs, NCs).
SECTION_KEYWORDS: Dict[str, List[str]] = {
    "NDC Tracking Module": [
        "ndc tracking module",
        "ndc tracking",
        "tracking progress",
        "progress toward achieving its 2030 emission reduction target",
        "progress toward achieving its",
        "description of kenya’s ndc",
        "description of kenya's ndc",
        "description of the ndc",
        "mitigation policies and measures",
        "mitigation actions and their effects",
        "tracking ndc",
        "tracking systems for nationally determined contributions",
        "ndc 2.0",
        "ndc 3.0",
        "ndcs",
    ],
    "Support Needed and Received Module": [
        "support needed and received module",
        "support needed and received",
        "information on financial support needed",
        "information on financial support received",
        "support flows",
        "support needed",
        "support received",
        "support for the implementation of the 2020 ndc",
        "support for the implementation of the ndc",
        "climate finance",
        "means of implementation",
        "technology development and transfer support needed",
        "capacity-building support needed",
        "capacity-building support received",
    ],
    "Other baseline initiatives": [
        "other baseline initiatives",
        "baseline analysis",
        "other initiatives",
        "ongoing transparency projects and initiatives",
        "transparency initiatives",
        "program / project and supporting",
        "leading ministry duration relationship with etf",
        "this cbit project is aligned with and complements other initiatives",
        "baseline of components",
        "baseline of component",
    ],
}


def validate_openai_api_key(api_key: str) -> bool:
    """
    Validate an OpenAI API key by making a simple API call.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        True if the API key is valid, False otherwise
    """
    if not OPENAI_AVAILABLE:
        return False
    
    if not api_key or not api_key.strip():
        return False
    
    try:
        client = OpenAI(api_key=api_key.strip())
        # Make a simple API call to validate the key
        client.models.list()
        return True
    except Exception:
        return False


def load_examples_from_folder(examples_folder: Path) -> Dict[str, str]:
    """
    Load example PDFs from the Examples folder and extract their sections.
    
    Args:
        examples_folder: Path to the Examples folder
        
    Returns:
        Dictionary mapping example filename to extracted sections text
    """
    examples: Dict[str, str] = {}
    
    if not examples_folder.exists() or not examples_folder.is_dir():
        return examples
    
    for pdf_file in examples_folder.glob("*.pdf"):
        try:
            text = extract_text_from_pdf(pdf_file)
            examples[pdf_file.name] = text
        except Exception as exc:
            print(f"Warning: Could not load example {pdf_file.name}: {exc}")
    
    return examples


def extract_sections_with_openai(
    pdf_text: str,
    api_key: str,
    examples: Dict[str, str],
    keywords: Dict[str, List[str]]
) -> Dict[str, str]:
    """
    Use OpenAI to extract the three target sections from PDF text.
    
    Args:
        pdf_text: The full text extracted from the PDF
        api_key: OpenAI API key
        examples: Dictionary of example PDF texts
        keywords: Dictionary mapping section names to keyword lists
        
    Returns:
        Dictionary mapping section names to extracted text
    """
    if not OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI library is not available")
    
    client = OpenAI(api_key=api_key)
    
    # Prepare examples text for the prompt
    examples_text = ""
    if examples:
        examples_text = "\n\n--- Example Documents ---\n"
        for example_name, example_text in examples.items():
            # Truncate example text to avoid token limits (keep first 5000 chars)
            truncated_example = example_text[:5000] + "..." if len(example_text) > 5000 else example_text
            examples_text += f"\nExample: {example_name}\n{truncated_example}\n"
    
    # Prepare keywords text
    keywords_text = "\n\n--- Keywords to Look For ---\n"
    for section_name, kw_list in keywords.items():
        keywords_text += f"\n{section_name}: {', '.join(kw_list[:10])}...\n"
    
    # Truncate PDF text if too long (keep first 100000 chars to stay within token limits)
    truncated_pdf_text = pdf_text[:100000] + "\n[... text truncated ...]" if len(pdf_text) > 100000 else pdf_text
    
    # Create the prompt
    prompt = f"""You are an expert at extracting structured information from climate change documents, specifically BURs (Biennial Update Reports).

Your task is to extract ALL relevant information related to three specific sections from the provided document text:

1. "NDC Tracking Module"
2. "Support Needed and Received Module"
3. "Other baseline initiatives"

{examples_text}

{keywords_text}

--- Document to Analyze ---
{truncated_pdf_text}

IMPORTANT: Extract as much relevant information as possible for each section. Be INCLUSIVE and COMPREHENSIVE:
- Include information that directly matches the section name or keywords
- Include information that is remotely connected or related to the section, even if the connection is indirect
- Include contextual information that helps understand the section's content
- Include related policies, measures, initiatives, data, statistics, or discussions that are thematically related
- Look beyond explicit headings - search the entire document for any content that could be relevant
- For "NDC Tracking Module": Include any mentions of NDCs, emission targets, mitigation actions, progress tracking, implementation status, policies, measures, or related climate actions
- For "Support Needed and Received Module": Include any mentions of financial support, technical assistance, capacity building, technology transfer, funding, grants, loans, or any form of climate finance or support mechanisms
- For "Other baseline initiatives": Include any mentions of ongoing projects, transparency initiatives, baseline analyses, complementary programs, or related climate and environmental initiatives

Extract comprehensive, detailed text for each section. Include all paragraphs, sentences, and information that could be relevant, even if the connection is indirect. The goal is to capture as much related information as possible.

If a section truly has no relevant content anywhere in the document, return an empty string for that section.

Return your response as a JSON object with exactly these keys:
- "NDC Tracking Module"
- "Support Needed and Received Module"
- "Other baseline initiatives"

Each value should be the comprehensive extracted text for that section (as much relevant information as possible), or an empty string only if absolutely no relevant content exists.

Return ONLY valid JSON, no additional text or explanation."""

    response_text = ""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a cost-effective model
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert document analyst that extracts comprehensive, detailed information from climate documents. Your goal is to be INCLUSIVE - extract all relevant content including remotely related information. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=8000  # Increased to allow for comprehensive extraction of all related information
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Try to parse JSON from the response
        # Sometimes the response might be wrapped in markdown code blocks
        if response_text.startswith("```"):
            # Extract JSON from code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
        
        sections = json.loads(response_text)
        
        # Ensure all three sections are present
        result: Dict[str, str] = {}
        for section_name in SECTION_NAMES:
            result[section_name] = sections.get(section_name, "").strip()
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse OpenAI response as JSON: {e}")
        if response_text:
            print(f"Response was: {response_text[:500]}")
        # Fallback: return empty sections
        return {name: "" for name in SECTION_NAMES}
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise


def extract_text_from_pdf(path: Path) -> str:
    """Extract raw text from a PDF file using pdfplumber."""
    texts: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            texts.append(page_text)
    return "\n".join(texts)


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces and normalize line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # remove trailing spaces on each line
    lines = [re.sub(r"\s+$", "", line) for line in text.split("\n")]
    return "\n".join(lines)


def find_section_ranges(lines: List[str]) -> Dict[str, Tuple[int, int]]:
    """
    Find index ranges (start, end) in `lines` for each section name.

    We assume section titles appear as standalone (or nearly standalone) lines.
    """
    # Precompile patterns for fuzzy matching of headings
    patterns = {
        name: re.compile(re.escape(name), re.IGNORECASE)
        for name in SECTION_NAMES
    }

    # Record first occurrence index for each section
    starts: Dict[str, int] = {}
    for i, line in enumerate(lines):
        for section_name, pattern in patterns.items():
            if section_name in starts:
                continue
            if pattern.search(line):
                starts[section_name] = i

    # Compute end indices: for each section, end at next section's start or EOF
    ranges: Dict[str, Tuple[int, int]] = {}
    sorted_sections = [
        s for s in SECTION_NAMES if s in starts
    ]  # preserve logical order
    for idx, section_name in enumerate(sorted_sections):
        start = starts[section_name]
        if idx + 1 < len(sorted_sections):
            next_section = sorted_sections[idx + 1]
            end = starts[next_section]
        else:
            end = len(lines)
        ranges[section_name] = (start, end)

    return ranges


def extract_sections_by_keywords(text: str) -> Dict[str, str]:
    """
    Fallback extraction based on keyword proximity.

    Used when explicit headings like 'NDC Tracking Module' are not present
    in the document (e.g. BURs and National Communications).
    """
    cleaned = normalize_whitespace(text)
    lines = cleaned.split("\n")

    sections: Dict[str, str] = {}

    for section_name in SECTION_NAMES:
        keywords = [kw.lower() for kw in SECTION_KEYWORDS.get(section_name, [])]
        if not keywords:
            sections[section_name] = ""
            continue

        matched_indices: List[int] = []
        for idx, line in enumerate(lines):
            lower_line = line.lower()
            if any(kw in lower_line for kw in keywords):
                matched_indices.append(idx)

        if not matched_indices:
            sections[section_name] = ""
            continue

        # Cluster nearby matches and expand a context window around each cluster
        clusters: List[Tuple[int, int]] = []
        start = matched_indices[0]
        prev = matched_indices[0]
        for i in matched_indices[1:]:
            if i - prev <= 2:
                prev = i
                continue
            clusters.append((start, prev))
            start = i
            prev = i
        clusters.append((start, prev))

        context_lines: List[str] = []
        seen_spans: set[Tuple[int, int]] = set()
        for start_idx, end_idx in clusters:
            ctx_start = max(start_idx - 5, 0)
            ctx_end = min(end_idx + 5, len(lines) - 1)
            span = (ctx_start, ctx_end)
            if span in seen_spans:
                continue
            seen_spans.add(span)
            context_lines.extend(lines[ctx_start : ctx_end + 1])
            context_lines.append("")  # blank line between clusters

        sections[section_name] = "\n".join(context_lines).strip()

    return sections


def extract_sections(text: str) -> Dict[str, str]:
    """
    Extract the three target sections from the full document text.

    Returns: dict mapping section_name -> extracted_text (may be empty string if not found).
    """
    cleaned = normalize_whitespace(text)
    lines = cleaned.split("\n")
    ranges = find_section_ranges(lines)

    # If we find explicit headings (as in the GEF8 PIF documents),
    # use the clean range-based extraction.
    if ranges:
        sections: Dict[str, str] = {}
        for name in SECTION_NAMES:
            if name in ranges:
                start, end = ranges[name]
                body_lines = lines[start:end]
                extracted = "\n".join(body_lines).strip()
            else:
                extracted = ""
            sections[name] = extracted
        return sections

    # Otherwise, fall back to a keyword-based extraction tuned using the
    # provided GEF8 PIF examples (Cuba + template) as reference.
    return extract_sections_by_keywords(text)


def infer_country_from_filename(path: Path) -> str:
    """
    Infer country name from filename.

    Basic heuristic:
    - Try to find a country-like word after an underscore and before another underscore or dot.
      Example: GEF8_PIF_Cuba_DRAFT.pdf -> Cuba
    - Fallback: use the whole stem (filename without extension).
    """
    stem = path.stem
    # Split on underscores and hyphens as common separators
    parts = re.split(r"[_\-]+", stem)

    # Filter out obvious metadata tokens (project codes, statuses, dates)
    metadata_tokens = {
        "GEF", "GEF8", "PIF", "PFD", "DRAFT", "FINAL", "REV", "V1", "V2", "V3"
    }
    tokens = [
        p
        for p in parts
        if p
        and not re.fullmatch(r"\d+(\.\d+)*", p)  # pure numbers / versions / dates
    ]

    # Prefer tokens that look like proper country names:
    # - Title case (first letter uppercase, not all caps)
    # - Not in common metadata tokens
    country_like = [
        t
        for t in tokens
        if t[0].isupper() and not t.isupper() and t.upper() not in metadata_tokens
    ]
    if country_like:
        # Take the first good-looking token (e.g. "Cuba" in GEF8_PIF_Cuba_DRAFT_...)
        return country_like[0]

    # Fallback: last non-metadata token
    remaining = [t for t in tokens if t.upper() not in metadata_tokens]
    if remaining:
        return remaining[-1]

    # Last resort: use the whole stem
    return stem


def infer_doc_type_from_filename(path: Path) -> str:
    """
    Infer a simple 'doc type' identifier from the filename.
    Detects BUR1, BUR2, etc. from patterns like "BUR", "BUR1", "BUR2", etc.

    Example:
    - Kenya_BUR.pdf -> BUR1
    - Kenya_BUR2.pdf -> BUR2
    - GEF8_PIF_Cuba_DRAFT_23.10.25.pdf -> GEF8_PIF_Cuba_DRAFT_23.10.25
    """
    stem = path.stem.upper()
    
    # Check for BUR patterns (BUR, BUR1, BUR2, etc.)
    bur_match = re.search(r'BUR(\d*)', stem)
    if bur_match:
        bur_num = bur_match.group(1)
        if bur_num:
            return f"BUR{bur_num}"
        else:
            return "BUR1"
    
    # Fallback to original stem
    return path.stem


class SupabaseClient:
    def __init__(self, config: SupabaseConfig):
        self.config = config
        self.base_rest_url = f"{config.url}/rest/v1"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "apikey": config.api_key,
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }
        )

    def get_country_record(self, country: str) -> Optional[Dict]:
        """Fetch existing record for a given country, if any."""
        params = {
            "select": "*",
            f"{self.config.country_column}": f"eq.{country}",
        }
        url = f"{self.base_rest_url}/{self.config.table}"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        # Assume unique by country; take first row
        return data[0]

    def upsert_country_sections(
        self,
        country: str,
        new_sections_for_doc: Dict[str, str],
        doc_type: str,
    ) -> Dict:
        """
        Merge new section text into the country's existing sections JSON and upsert.

        New sections JSON shape:
        {
          "sections": [
            {
              "name": "NDC Tracking Module",
              "documents": [
                {
                  "doc_type": "BUR1",
                  "extracted_text": "text..."
                }
              ]
            },
            {
              "name": "Support Needed and Received Module",
              "documents": [...]
            },
            ...
          ]
        }
        """
        existing = self.get_country_record(country)
        if existing and self.config.sections_column in existing:
            sections_data = existing.get(self.config.sections_column) or {}
        else:
            sections_data = {}

        # Convert old format to new format if needed
        if "sections" not in sections_data:
            # Check if it's the old format (dict of section_name -> dict of doc_types)
            if isinstance(sections_data, dict) and sections_data:
                # Check if first key is a section name (old format)
                first_key = list(sections_data.keys())[0]
                if first_key in SECTION_NAMES:
                    # Convert old format to new format
                    sections_list = []
                    for section_name in SECTION_NAMES:
                        if section_name in sections_data:
                            documents = []
                            for old_doc_type, text in sections_data[section_name].items():
                                if text:  # Only include non-empty texts
                                    documents.append({
                                        "doc_type": old_doc_type,
                                        "extracted_text": text
                                    })
                            if documents:  # Only add section if it has documents
                                sections_list.append({
                                    "name": section_name,
                                    "documents": documents
                                })
                    sections_data = {"sections": sections_list}
                else:
                    sections_data = {"sections": []}
            else:
                sections_data = {"sections": []}

        # Ensure sections list exists
        if "sections" not in sections_data:
            sections_data["sections"] = []

        sections_list = sections_data["sections"]

        # Process each new section
        for section_name, text in new_sections_for_doc.items():
            if not text:
                # Skip empty sections (nothing found)
                continue

            # Find or create the section object
            section_obj = None
            for sec in sections_list:
                if sec.get("name") == section_name:
                    section_obj = sec
                    break

            if section_obj is None:
                # Create new section
                section_obj = {
                    "name": section_name,
                    "documents": []
                }
                sections_list.append(section_obj)

            # Ensure documents list exists
            if "documents" not in section_obj:
                section_obj["documents"] = []

            # Find or update the document for this doc_type
            doc_found = False
            for doc in section_obj["documents"]:
                if doc.get("doc_type") == doc_type:
                    doc["extracted_text"] = text
                    doc_found = True
                    break

            if not doc_found:
                # Add new document
                section_obj["documents"].append({
                    "doc_type": doc_type,
                    "extracted_text": text
                })

        payload = {
            self.config.country_column: country,
            self.config.sections_column: sections_data,
        }

        url = f"{self.base_rest_url}/{self.config.table}"

        # If the country already exists, perform an UPDATE to avoid
        # creating duplicate rows for the same country.
        if existing:
            # Filter by the existing row's primary key if available,
            # otherwise fall back to the country column.
            row_id = existing.get("id")
            if row_id is not None:
                update_url = f"{url}?id=eq.{row_id}"
            else:
                update_url = f"{url}?{self.config.country_column}=eq.{country}"

            headers = {
                "Prefer": "return=representation",
            }
            resp = self.session.patch(
                update_url,
                data=json.dumps({self.config.sections_column: sections_data}),
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()[0] if resp.content else {}

        # Otherwise, INSERT a new row for this country.
        headers = {
            "Prefer": "return=representation",
        }
        resp = self.session.post(url, data=json.dumps(payload), headers=headers)
        resp.raise_for_status()
        return resp.json()[0] if resp.content else {}


def process_pdf_file(
    pdf_path: Path,
    supabase_client: SupabaseClient,
    openai_api_key: Optional[str] = None,
    examples: Optional[Dict[str, str]] = None
) -> Dict:
    """
    Extract sections from one PDF and upsert into Supabase.
    
    Args:
        pdf_path: Path to the PDF file
        supabase_client: Supabase client instance
        openai_api_key: Optional OpenAI API key. If provided, uses OpenAI for extraction.
        examples: Optional dictionary of example PDF texts for OpenAI extraction
    """
    print(f"Processing PDF: {pdf_path}")
    raw_text = extract_text_from_pdf(pdf_path)
    
    # Use OpenAI if API key is provided, otherwise use original method
    if openai_api_key and examples is not None:
        print("Using OpenAI for extraction...")
        sections = extract_sections_with_openai(
            raw_text,
            openai_api_key,
            examples,
            SECTION_KEYWORDS
        )
    else:
        print("Using original extraction method...")
        sections = extract_sections(raw_text)

    country = infer_country_from_filename(pdf_path)
    doc_type = infer_doc_type_from_filename(pdf_path)

    result = supabase_client.upsert_country_sections(
        country=country,
        new_sections_for_doc=sections,
        doc_type=doc_type,
    )

    print(f"Upserted data for country='{country}', doc_type='{doc_type}'.")
    return result


def collect_pdf_files(target: Path) -> List[Path]:
    """Collect all PDF files from a directory or a single PDF path."""
    if target.is_file():
        if target.suffix.lower() == ".pdf":
            return [target]
        raise ValueError(f"File is not a PDF: {target}")

    pdfs: List[Path] = []
    for root, _dirs, files in os.walk(target):
        for name in files:
            if name.lower().endswith(".pdf"):
                pdfs.append(Path(root) / name)
    return sorted(pdfs)


def find_bur_files_for_country(country_name: str, bur_folder: Path) -> List[Path]:
    """
    Find BUR PDF files in the BUR folder that match the given country name.
    
    Args:
        country_name: The country name to search for (case-insensitive)
        bur_folder: Path to the BUR folder
        
    Returns:
        List of Path objects for matching PDF files
    """
    if not bur_folder.exists() or not bur_folder.is_dir():
        return []
    
    country_lower = country_name.lower()
    matching_files: List[Path] = []
    
    for pdf_file in bur_folder.glob("*.pdf"):
        # Check if the filename contains the country name (case-insensitive)
        filename_lower = pdf_file.stem.lower()
        if country_lower in filename_lower:
            matching_files.append(pdf_file)
    
    return sorted(matching_files)


def main() -> None:
    # Ask user for country name
    country_name = input("Enter country name: ").strip()
    
    if not country_name:
        print("Error: Country name cannot be empty.")
        return
    
    # Determine script directory (used for both Examples and BUR folders)
    script_dir = Path(__file__).parent.resolve()
    
    # Ask for OpenAI API key with validation
    openai_api_key: Optional[str] = None
    examples: Optional[Dict[str, str]] = None
    
    while True:
        api_key_input = input("Please enter OpenAI API KEY (If you wish to not use one just press enter): ").strip()
        
        if not api_key_input:
            # User pressed enter without providing a key - use original method
            print("Using original extraction method (no OpenAI).")
            break
        
        # Validate the API key
        if validate_openai_api_key(api_key_input):
            openai_api_key = api_key_input
            print("OpenAI API key validated successfully.")
            
            # Load examples from Examples folder
            examples_folder = script_dir / "Examples"
            examples = load_examples_from_folder(examples_folder)
            
            if examples:
                print(f"Loaded {len(examples)} example document(s) from Examples folder.")
            else:
                print("Warning: No examples found in Examples folder.")
            
            break
        else:
            # Invalid API key - ask again
            print("Not a valid api key, if you dont want to use one just press enter: ", end="")
    
    # Determine the BUR folder path
    bur_folder = script_dir / "BUR"
    
    # Check if BUR folder exists
    if not bur_folder.exists():
        print(f"Error: BUR folder not found at {bur_folder}")
        return
    
    # Find BUR files for the specified country
    pdf_files = find_bur_files_for_country(country_name, bur_folder)
    
    if not pdf_files:
        print(f"The BUR folder does not have files about {country_name}")
        return
    
    print(f"Found {len(pdf_files)} BUR file(s) for {country_name}.")
    
    # Initialize Supabase client
    config = SupabaseConfig.from_env()
    client = SupabaseClient(config)
    
    # Process each matching PDF file
    for pdf in pdf_files:
        try:
            process_pdf_file(pdf, client, openai_api_key, examples)
        except Exception as exc:  # noqa: BLE001
            print(f"Error processing {pdf}: {exc}")


if __name__ == "__main__":
    main()



