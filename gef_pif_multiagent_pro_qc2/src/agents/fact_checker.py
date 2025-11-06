from __future__ import annotations
from typing import Dict, Any
import os, json
from ..models.openai_client import OpenAIClient, ChatMessage
from ..utils.json_sanitizer import parse_model_json

def _read_prompt(name: str) -> str:
    here = os.path.dirname(os.path.dirname(__file__))
    p = os.path.join(here, "prompts", name)
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

FACT_CHECKER_SYSTEM = _read_prompt("fact_checker_system.txt")

async def fact_check_sections(client: OpenAIClient, payload: Dict[str, Any]) -> Dict[str, Any]:
    sections = payload.get("sections", {})
    citations = payload.get("citations", [])
    user_prompt = f"""You will receive three paragraph-form sections for a GEF-8 PIF with citation tags.
Return ONLY STRICT JSON with keys: issues_found, fixes_recommended, residual_risks, updated_citations, confidence_estimate.

sections:
{json.dumps(sections)}

citations:
{json.dumps(citations)}
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
