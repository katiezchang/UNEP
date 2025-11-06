from __future__ import annotations
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import os, json
from ..models.openai_client import OpenAIClient, ChatMessage
from ..utils.json_sanitizer import parse_model_json

def _read_prompt(name: str) -> str:
    here = os.path.dirname(os.path.dirname(__file__))
    p = os.path.join(here, "prompts", name)
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

NDC_WRITER_SYSTEM = _read_prompt("ndc_writer_system.txt")

@dataclass
class NDCWriterConfig:
    country: str
    today_iso: str
    source_table: str
    max_sources: int = 25
    crawl_depth: int = 1
    confidence_target: int = 90
    max_improvement_passes: int = 3
    fetch_concurrency: int = 4
    model: Optional[str] = None
    load_feedback_path: Optional[str] = None
    previous_feedback_text: Optional[str] = None

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {"type": "object", "properties": {
            "ndc_tracking_module": {"type": "string"},
            "support_needed_and_received": {"type": "string"},
            "other_baseline_initiatives": {"type": "string"},
        }, "required": ["ndc_tracking_module","support_needed_and_received","other_baseline_initiatives"]},
        "citations": {"type": "array","items":{"type":"string"}},
        "issues_found": {"type": "array","items":{"type":"string"}},
        "fixes_applied": {"type": "array","items":{"type":"string"}},
        "residual_risks": {"type": "array","items":{"type":"string"}},
        "confidence_score": {"type": "number"},
        "pass_number": {"type": "integer"}
    },
    "required": ["sections","citations","confidence_score","pass_number"]
}

def _load_feedback_text(cfg: NDCWriterConfig) -> str:
    parts: List[str] = []
    if cfg.previous_feedback_text:
        parts.append(str(cfg.previous_feedback_text).strip())
    if cfg.load_feedback_path and os.path.exists(cfg.load_feedback_path):
        try:
            with open(cfg.load_feedback_path, "r", encoding="utf-8") as f:
                parts.append(f.read())
        except Exception as e:
            parts.append(f"[Note] Could not read feedback file: {cfg.load_feedback_path} ({e})")
    return "\n\n".join([p for p in parts if p])

def _build_messages(cfg: NDCWriterConfig, pass_number: int) -> List[ChatMessage]:
    feedback_text = _load_feedback_text(cfg)
    user_prompt = f"""You are drafting *paragraph-form* content for a GEF-8 PIF.

Country: {cfg.country}
Today: {cfg.today_iso}

Crawling/grounding constraints (upstream retriever; you do not browse here):
- max_sources: {cfg.max_sources}
- crawl_depth: {cfg.crawl_depth}
- fetch_concurrency: {cfg.fetch_concurrency}

Quality loop (you are pass #{pass_number} of at most {cfg.max_improvement_passes}):
- Target confidence (0–100): {cfg.confidence_target}
- If confidence is below target, enumerate issues and apply fixes in the text itself.

Allowed sources (compressed):
{cfg.source_table}

Prior fact-check feedback to integrate (may be empty):
{feedback_text if feedback_text else "[none]"}

OUTPUT FORMAT — IMPORTANT:
Return ONLY STRICT RFC-8259 JSON with these keys (no prose, no code fences):
{json.dumps(JSON_SCHEMA, indent=2)}
Where each section is 2–5 cohesive paragraphs (no bullets) with inline source tags like [S1] after each paragraph.
"""
    return [
        ChatMessage(role="system", content=NDC_WRITER_SYSTEM),
        ChatMessage(role="user", content=user_prompt),
    ]

async def generate_sections(
    client: OpenAIClient,
    country: str,
    today_iso: str,
    source_table: str,
    *,
    max_sources: int = 25,
    crawl_depth: int = 1,
    confidence_target: int = 90,
    max_improvement_passes: int = 3,
    fetch_concurrency: int = 4,
    model: Optional[str] = None,
    load_feedback_path: Optional[str] = None,
    previous_feedback_text: Optional[str] = None,
) -> Dict[str, Any]:
    if model and hasattr(client, "set_model"):
        try:
            client.set_model(model)
        except Exception:
            pass

    cfg = NDCWriterConfig(
        country=country, today_iso=today_iso, source_table=source_table,
        max_sources=max_sources, crawl_depth=crawl_depth,
        confidence_target=confidence_target, max_improvement_passes=max_improvement_passes,
        fetch_concurrency=fetch_concurrency, model=model,
        load_feedback_path=load_feedback_path, previous_feedback_text=previous_feedback_text
    )

    last_payload: Dict[str, Any] = {}
    for p in range(1, max_improvement_passes + 1):
        messages = _build_messages(cfg, pass_number=p)
        raw = await client.chat(messages, temperature=0.0, max_tokens=2800)
        payload = parse_model_json(raw, debug_path="out/ndc_writer_last_raw.txt")
        payload.setdefault("pass_number", p)
        payload.setdefault("confidence_score", 0)
        payload.setdefault("citations", [])
        payload.setdefault("issues_found", [])
        payload.setdefault("fixes_applied", [])
        payload.setdefault("residual_risks", [])
        payload.setdefault("sections", {})
        last_payload = payload
        try:
            if float(payload.get("confidence_score", 0)) >= float(confidence_target):
                break
        except Exception:
            pass
        cfg.previous_feedback_text = "Residual risks from previous pass:\n- " + "\n- ".join(payload.get("residual_risks", []))
    return last_payload
