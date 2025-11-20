# UNEP X Voyager
# Project focused on generating PIF prompt summaries and GEF documents for review
git clone https://github.com/katiezchang/UNEP.git
cd UNEP
pip install -r requirements.txt

# UNEP / GEF PIF Drafting Pipeline

This repository contains a prototype pipeline for semi-automated drafting of
GEF-8 Project Identification Forms (PIFs) using:

1. **PDF/web extraction** from UNFCCC reports (BURs, BTRs, NCs, NDCs, etc.).
2. **Section generation** for the PIF, using templated prompts and structured
   extractions.

The goal is to reduce manual work by:
- Automatically pulling relevant climate-transparency text from UNFCCC documents.
- Reusing that text to generate consistent, well-structured PIF sections.

---

## High-Level Workflow

1. **PDF / Web Extraction (`pdfextraction/`)**
   - Navigate to the UNFCCC reports for a given country.
   - Download or read BUR/BTR/NC/NDC PDFs.
   - Extract the paragraphs relevant to each PIF section into plain text.
   - each folder within pdfextraction extracts text for specific sections, which are denoted by the consultant's name

2. **Section Generation (`section_generator/`)**
   - Take the extracted snippets and section prompts.
   - Generate draft PIF sections aligned with the official GEF-8 template.
   - `gef_pif_updated/` contains the most up-to-date code for this step.

3. **Orchestration (`main.py`)**
   - (Planned / WIP) Tie extraction and generation together into a single run
     for a given country.
