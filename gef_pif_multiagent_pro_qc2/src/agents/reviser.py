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

REVISER_SYSTEM = _read_prompt("reviser_system.txt")

async def revise_all(client: OpenAIClient, sections: Dict[str, str]) -> Dict[str, str]:
    user_prompt = f"""Harmonize style across these sections. Return JSON with the same keys and revised paragraph strings.
{json.dumps(sections)}
"""
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
    for k in ["ndc_tracking_module", "support_needed_and_received", "other_baseline_initiatives"]:
        out[k] = data.get(k, sections.get(k, ""))
    return out
