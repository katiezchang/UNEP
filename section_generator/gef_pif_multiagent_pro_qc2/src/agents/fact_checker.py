from __future__ import annotations
from typing import Dict, Any
import os, json
from ..models.openai_client import OpenAIClient, ChatMessage
from ..prompts.sections_update import SECTIONS as UPDATED_SECTIONS
from ..utils.json_sanitizer import parse_model_json

def _read_prompt(name: str) -> str:
    here = os.path.dirname(os.path.dirname(__file__))
    p = os.path.join(here, "prompts", name)
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

FACT_CHECKER_SYSTEM = _read_prompt("fact_checker_system.txt")

def _build_section_guidance(sections: Dict[str, Any]) -> str:
    lines = []
    keys = list(sections.keys())
    # Tailored checks per known section keys
    if "baseline_unfccc_reporting" in keys:
        lines.append(
            "- baseline_unfccc_reporting: Verify entries against https://unfccc.int/reports (Party page if available). "
            "Parse year from submission date (YYYY), standardize report names (e.g., 'First BUR'), sort by year descending "
            "Do not delete valid rows; propose corrections with exact URLs."
            "Make sure it is to the most UPDATED year (2024+) for each document, report all entries from the website for that country."
        )
    if "baseline_stakeholders" in keys:
        lines.append(
            "- baseline_stakeholders: Ensure each entry is classified into the specified groups; "
            "keep entries within limits (≤8 per type)."
        )
    if "other_baseline_initiatives" in keys:
        lines.append(
            "- other_baseline_initiatives: Cross-check program names, durations, and values against official sources (GEF, GCF, ICAT, etc.); "
            "prefer official project pages; keep numeric values verbatim unless demonstrably incorrect."
        )
    if "module_ghg" in keys:
        lines.append(
            "- module_ghg: Check references to IPCC Guidelines versions and inventory submissions against NCs/BURs/NIRs; flag missing citations."
        )
    # Include general instruction to respect section-specific prompts
    lines.append(
        "- General: Respect the section-specific instructions defined in the writer prompts; prioritize the referenced document sections."
    )
    return "\n".join(lines)

async def fact_check_sections(client: OpenAIClient, payload: Dict[str, Any]) -> Dict[str, Any]:
    sections = payload.get("sections", {})
    citations = payload.get("citations", [])
    tailored_checks = _build_section_guidance(sections)

    user_prompt = f"""You will receive paragraph and table-form sections for a GEF-8 PIF with citation tags.
Return ONLY STRICT JSON with keys: issues_found, fixes_recommended, residual_risks, updated_citations, confidence_estimate.

sections:
{json.dumps(sections)}

citations:
{json.dumps(citations)}

Section-specific checks to apply:
{tailored_checks}
"""
    messages = [
        ChatMessage(role="system", content=FACT_CHECKER_SYSTEM),
        ChatMessage(role="user", content=user_prompt),
    ]
    raw = await client.chat(messages, temperature=0.0, max_tokens=1600)
    data = parse_model_json(raw, debug_path="out/fact_checker_last_raw.txt")
    data.setdefault("issues_found", [])
    data.setdefault("fixes_recommended", [])
    data.setdefault("residual_risks", [])
    data.setdefault("updated_citations", citations or [])
    data.setdefault("confidence_estimate", 0)
    return data
