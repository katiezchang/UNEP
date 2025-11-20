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
        "sections": {
            "type": "object",
            "properties": {
                "baseline_national_tf_header": {"type": "string"},
                "baseline_institutional": {"type": "string"},
                "baseline_policy": {"type": "string"},
                "baseline_stakeholders": {"type": "string"},
                "baseline_unfccc_reporting": {"type": "string"},
                "module_header": {"type": "string"},
                "module_ghg": {"type": "string"},
                "module_adaptation": {"type": "string"},
                "module_ndc_tracking": {"type": "string"},
                "module_support": {"type": "string"},
                "other_baseline_initiatives": {"type": "string"},
            },
            "required": [
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
                "other_baseline_initiatives"
            ],
        },
        "citations": {"type": "array", "items": {"type": "string"}},
        "issues_found": {"type": "array", "items": {"type": "string"}},
        "fixes_applied": {"type": "array", "items": {"type": "string"}},
        "residual_risks": {"type": "array", "items": {"type": "string"}},
        "confidence_score": {"type": "number"},
        "pass_number": {"type": "integer"}
    },
    "required": ["sections", "citations", "confidence_score", "pass_number"]
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

TABLE_SECTIONS = [
    "baseline_unfccc_reporting",
    "baseline_stakeholders",
    "other_baseline_initiatives",
]


# def _build_messages(cfg: NDCWriterConfig, pass_number: int, section_key: str | None = None) -> List[ChatMessage]:
#     feedback_text = _load_feedback_text(cfg)

#     # select table prompt if needed
#     section_prompt = (
#             f"Draft 2–5 concise paragraphs describing {section_key.replace('_', ' ')} for {cfg.country}."
#         )
#     if section_key in TABLE_SECTIONS:
#         paragraph_hint = "Return text specified, table format, plus one concise summary paragraph and anything else prompted."
#     else:
#         paragraph_hint = "Return only paragraphs, no bullets unless explicitly required."

#     user_prompt = f"""You are drafting content for a GEF-8 PIF.

# Country: {cfg.country}
# Today: {cfg.today_iso}
# Section: {section_key}

# Crawling constraints:
# - max_sources: {cfg.max_sources}
# - crawl_depth: {cfg.crawl_depth}
# - fetch_concurrency: {cfg.fetch_concurrency}

# Quality loop (pass #{pass_number} of {cfg.max_improvement_passes}):
# - Target confidence: {cfg.confidence_target}

# Allowed sources (summary):
# {cfg.source_table}

# Prior feedback to integrate:
# {feedback_text if feedback_text else "[none]"}

# TASK PROMPT:
# {section_prompt}

# OUTPUT FORMAT:
# - STRICT RFC-8259 JSON only (no code fences).
# - {paragraph_hint}
# """

#     return [
#         ChatMessage(role="system", content=NDC_WRITER_SYSTEM),
#         ChatMessage(role="user", content=user_prompt),
#     ]


# async def generate_sections(
#     client: OpenAIClient,
#     country: str,
#     today_iso: str,
#     source_table: str,
#     *,
#     max_sources: int = 25,
#     crawl_depth: int = 1,
#     confidence_target: int = 90,
#     max_improvement_passes: int = 3,
#     fetch_concurrency: int = 4,
#     model: Optional[str] = None,
#     load_feedback_path: Optional[str] = None,
#     previous_feedback_text: Optional[str] = None,
# ) -> Dict[str, Any]:
#     """Iterates across all schema sections and builds each section (tables or text)."""
#     if model and hasattr(client, "set_model"):
#         try:
#             client.set_model(model)
#         except Exception:
#             pass

#     cfg = NDCWriterConfig(
#         country=country, today_iso=today_iso, source_table=source_table,
#         max_sources=max_sources, crawl_depth=crawl_depth,
#         confidence_target=confidence_target, max_improvement_passes=max_improvement_passes,
#         fetch_concurrency=fetch_concurrency, model=model,
#         load_feedback_path=load_feedback_path, previous_feedback_text=previous_feedback_text
#     )

#     sections_out: Dict[str, Any] = {}
#     for section_key in JSON_SCHEMA["properties"]["sections"]["properties"].keys():
#         for p in range(1, max_improvement_passes + 1):
#             messages = _build_messages(cfg, pass_number=p, section_key=section_key)
#             raw = await client.chat(messages, temperature=0.0, max_tokens=2800)
#             payload = parse_model_json(raw, debug_path=f"out/{section_key}_last_raw.txt")
#             payload.setdefault("confidence_score", 0)
#             payload.setdefault("sections", {})
#             content = payload.get("sections", {})

#             # For table sections, accept the top-level table JSON
#             if section_key in TABLE_SECTIONS:
#                 sections_out[section_key] = json.dumps(payload, ensure_ascii=False)
#             else:
#                 sections_out[section_key] = content.get(section_key, "")

#             if float(payload.get("confidence_score", 0)) >= float(confidence_target):
#                 break

#     return sections_out

def _build_messages(cfg: NDCWriterConfig, pass_number: int) -> List[ChatMessage]:
    feedback_text = _load_feedback_text(cfg)
    user_prompt = f"""You are drafting *paragraph- and table-form* content for a GEF-8 PIF.

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
Where each section is 2–5 cohesive paragraphs or table if specified (no bullets) with inline source tags like [S1] after each paragraph.
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
