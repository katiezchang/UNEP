# PDF Extraction for GEF8 PIF Sections

This directory contains Python scripts for scraping UNFCCC country reports and extracting relevant sections for GEF8 PIF generation.

## Overview

This project is the **first stage** of a two-stage workflow:

1. **Data Extraction** (this project) - Python scripts scrape UNFCCC country reports, extract relevant sections from PDFs, and save them to JSON bundle files
2. **Section Generation** (`../section_generator/alicia_ass7/`) - TypeScript/Node.js project reads extracted data, uses LLM to generate polished PIF sections, and exports to PDF

## Directory Structure

- `alicia_ass7_pdfextraction/` - Main extraction project containing:
  - `scrape_unfccc.py` - Main scraper that downloads and extracts sections from UNFCCC reports
  - `upload_to_supabase.py` - Script to upload extracted data to Supabase database
  - `data/` - Extracted data in JSON format:
    - `Institutional_framework_bundle.json` - All institutional framework extractions
    - `National_policy_framework_bundle.json` - All national policy framework extractions
    - Individual country JSON files organized by section type
  - `downloads/` - Downloaded PDF files from UNFCCC
  - `SUPABASE_README.md` - Guide for uploading data to Supabase

## Quick Start

### Prerequisites

```bash
pip install requests beautifulsoup4 PyMuPDF supabase python-dotenv
```

### Configuration

1. **Set up cookies** (for UNFCCC website access):
   - Create `alicia_ass7_pdfextraction/cookies.json` with your UNFCCC session cookies
   - See `scrape_unfccc.py` for cookie format requirements

2. **Set up Supabase** (optional, for database storage):
   - Configure `alicia_ass7_pdfextraction/supabase_config.json` with your Supabase credentials
   - See `SUPABASE_README.md` for detailed setup instructions

### Extract Sections for a Country

```bash
cd alicia_ass7_pdfextraction
python scrape_unfccc.py --country "Cuba"
```

This will:
1. Scrape UNFCCC website for country reports (BURs, BTRs, NDCs, NCs)
2. Download relevant PDF files to `downloads/`
3. Extract "Institutional Framework for Climate Action" and "National Policy Framework" sections
4. Save extracted text to JSON files in `data/`
5. Create/update bundle JSON files with all extractions

### Upload to Supabase (Optional)

```bash
python upload_to_supabase.py
```

Uploads all bundle JSON files to your Supabase database for centralized storage and querying.

## How It Works

### Extraction Process

1. **Web Scraping**: `scrape_unfccc.py` searches UNFCCC reports page for country-specific documents
2. **PDF Download**: Downloads relevant PDF files (BURs, BTRs, NDCs, National Communications)
3. **Section Extraction**: Uses pattern matching to find and extract:
   - "Institutional Framework for Climate Action" sections
   - "National Policy Framework" sections
4. **Data Storage**: Saves extracted text to JSON files with metadata:
   - Country name
   - Section type
   - Source document type (BUR1, BTR1, NDC, etc.)
   - Document URL
   - Extracted text
   - Timestamp

### Output Format

Extracted data is saved in two formats:

1. **Individual JSON files**: `data/{SectionType}/{Country}_{SectionType}_{DocType}.json`
2. **Bundle JSON files**: 
   - `data/Institutional_framework_bundle.json` - All institutional framework extractions
   - `data/National_policy_framework_bundle.json` - All national policy framework extractions

Bundle files are arrays of extraction objects that the section generator reads.

## Integration with Section Generator

The extracted data is used by the section generator (`../section_generator/alicia_ass7/`):

1. **Data Flow**:
   - Extraction scripts create JSON bundle files in `data/`
   - Section generator reads from these bundle files
   - LLM uses extracted text as source material for generating polished PIF sections

2. **File Paths**:
   - Section generator expects bundle files at:
     - `pdfextraction/alicia_ass7_pdfextraction/data/Institutional_framework_bundle.json`
     - `pdfextraction/alicia_ass7_pdfextraction/data/National_policy_framework_bundle.json`

3. **Optional Integration**:
   - The section generator's `pdfExport.ts` can optionally call `scrape_unfccc.py` directly to refresh data before generation
   - This ensures the latest UNFCCC data is used for section generation

## Supported Countries

The extraction scripts support any country with UNFCCC reports. Examples in the data folder include:
- Cuba
- Guinea-Bissau
- India
- Jordan
- Kenya
- Sierra Leone

## Extracted Sections

The scripts extract two main section types:

1. **Institutional Framework for Climate Action**: Describes national institutions, ministries, and agencies involved in climate action and reporting
2. **National Policy Framework**: Describes laws, policies, decrees, and strategies related to climate action

## Notes

- PDF extraction uses pattern matching and may require manual verification for accuracy
- Some PDFs may have formatting issues that affect extraction quality
- The bundle JSON files aggregate all extractions for easy querying by country
- Extracted text is stored as-is from PDFs; the section generator handles formatting and polishing

