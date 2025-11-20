from __future__ import annotations
from typing import Dict, Any, List, Tuple
import os, json
import re
from collections import defaultdict
from ..models.openai_client import OpenAIClient, ChatMessage
from ..utils.json_sanitizer import parse_model_json

def _read_prompt(name: str) -> str:
    here = os.path.dirname(os.path.dirname(__file__))
    p = os.path.join(here, "prompts", name)
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

REVISER_SYSTEM = _read_prompt("reviser_system.txt")

def _normalize_amount(amount_str: str) -> str:
    """Normalize monetary amounts for comparison (e.g., "$50M" -> "50 million")"""
    # Remove common currency symbols and normalize
    normalized = amount_str.upper().strip()
    # Remove currency symbols
    normalized = re.sub(r'[USD$€£¥]', '', normalized)
    # Normalize million/billion abbreviations
    normalized = re.sub(r'\bM\b', ' million', normalized)
    normalized = re.sub(r'\bB\b', ' billion', normalized)
    normalized = re.sub(r'\bK\b', ' thousand', normalized)
    # Remove commas and extra spaces
    normalized = re.sub(r'[, ]+', ' ', normalized).strip()
    return normalized

def _extract_monetary_amounts(text: str) -> List[Tuple[str, str]]:
    """Extract monetary amounts from text. Returns list of (original_text, normalized_amount) tuples."""
    # Pattern to match various monetary formats: $50M, USD 50 million, 50 million USD, $50,000, etc.
    patterns = [
        r'\$[\d,]+(?:\.\d+)?\s*(?:million|billion|thousand|M|B|K)?',
        r'USD\s*[\d,]+(?:\.\d+)?\s*(?:million|billion|thousand|M|B|K)?',
        r'[\d,]+(?:\.\d+)?\s*(?:million|billion|thousand|M|B|K)?\s*USD',
        r'[\d,]+(?:\.\d+)?\s*(?:million|billion|thousand)\s*(?:USD|dollars?)?',
    ]
    amounts = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            original = match.group(0)
            normalized = _normalize_amount(original)
            amounts.append((original, normalized))
    return amounts

def _detect_duplicate_amounts(sections: Dict[str, str]) -> List[str]:
    """Detect duplicate monetary amounts across sections. Returns list of warning messages."""
    warnings = []
    amount_locations = defaultdict(list)  # normalized_amount -> [(section_key, original_text)]
    
    # Extract all amounts from all sections
    for section_key, section_text in sections.items():
        amounts = _extract_monetary_amounts(section_text)
        for original, normalized in amounts:
            amount_locations[normalized].append((section_key, original))
    
    # Find duplicates (amounts appearing in multiple sections)
    for normalized_amount, locations in amount_locations.items():
        if len(locations) > 1:
            sections_with_amount = [loc[0] for loc in locations]
            examples = [loc[1] for loc in locations[:3]]  # Show first 3 examples
            warnings.append(
                f"DUPLICATE DETECTED: Amount '{examples[0]}' (normalized: '{normalized_amount}') "
                f"appears in {len(sections_with_amount)} sections: {', '.join(sections_with_amount)}. "
                f"Keep it in ONE section only and remove/rephrase in others."
            )
    
    return warnings

async def revise_all(client: OpenAIClient, sections: Dict[str, str]) -> Dict[str, str]:
    # Detect duplicate amounts before revision
    duplicate_warnings = _detect_duplicate_amounts(sections)
    
    user_prompt_parts = [
        "Harmonize style across these sections. Return JSON with the same keys and revised paragraph or table strings."
    ]
    
    if duplicate_warnings:
        user_prompt_parts.append("\n\n⚠️ DUPLICATE AMOUNTS DETECTED - ACTION REQUIRED:")
        user_prompt_parts.append("The following monetary amounts appear in multiple sections. You MUST:")
        user_prompt_parts.append("1. Keep each amount in ONLY ONE section (prefer sections with citations or better context)")
        user_prompt_parts.append("2. Remove or rephrase the duplicate amounts in all other sections")
        user_prompt_parts.append("\nDuplicates found:")
        for warning in duplicate_warnings:
            user_prompt_parts.append(f"- {warning}")
        user_prompt_parts.append("")
    
    user_prompt_parts.append(f"Sections to revise:\n{json.dumps(sections, indent=2)}")
    user_prompt = "\n".join(user_prompt_parts)
    messages = [
        ChatMessage(role="system", content=REVISER_SYSTEM),
        ChatMessage(role="user", content=user_prompt),
    ]
    raw = await client.chat(messages, temperature=0.0, max_tokens=1600)
    data = None
    try:
        data = parse_model_json(raw, debug_path="out/reviser_last_raw.txt")
    except Exception:
        return sections
    out = {}
    for k in [
    "baseline_national_tf_header",
    "baseline_institutional",
    "baseline_policy",
    "baseline_stakeholders",
    "baseline_unfccc_reporting",
    "module_header",
    "module_ghg",
    "module_adaptation",
    "module_ndc_tracking",
    "module_support",
    "other_baseline_initiatives",]:
        out[k] = data.get(k, sections.get(k, ""))
    return out

