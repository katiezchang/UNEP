from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from textwrap import dedent
import os
from ..models.openai_client import OpenAIClient, ChatMessage

def _read_prompt(name: str) -> str:
    here = os.path.dirname(os.path.dirname(__file__))
    p = os.path.join(here, "prompts", name)
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

SECTION_WRITER_SYSTEM = _read_prompt("section_writer_system.txt")

@dataclass
class SectionSpec:
    key: str
    title: str
    word_limit: Optional[int] = None
    standard_text: Optional[str] = None
    prompt: Optional[str] = None
    keep_existing_prompt: bool = False

def build_messages(spec: SectionSpec, context: Dict[str, Any], example_override: str | None = None, feedback_text: str | None = None) -> List[ChatMessage]:
    country = context.get("country", "the Country")
    existing_prompts = context.get("existing_prompts", {})

    opening = []
    opening.append(f"SECTION_TITLE: {spec.title.format(Country=country)}\n")
    if spec.standard_text:
        opening.append("OPENING_PARAGRAPH: " + spec.standard_text.format(
            Country=country,
            UNFCCC_sign_date=context.get("UNFCCC_sign_date", "[TBD]"),
            UNFCCC_rat_date=context.get("UNFCCC_rat_date", "[TBD]"),
            KP_rat_date=context.get("KP_rat_date", "[TBD]"),
            PA_rat_date=context.get("PA_rat_date", "[TBD]"),
            PA_adopt_date=context.get("PA_adopt_date", "[TBD]"),
        ) + "\n")

    prompt_text = spec.prompt or ""
    if spec.keep_existing_prompt and spec.key in existing_prompts:
        prompt_text = existing_prompts[spec.key]
    if example_override:
        prompt_text += "\n\nFollow the tone/structure of this example snippet:\n" + example_override.strip()

    word_limit_text = spec.word_limit if spec.word_limit else 'n/a'

    feedback_block = ""
    if feedback_text:
        feedback_block = "\n\nPrior fact-check feedback to integrate:\n" + str(feedback_text).strip() + "\n"

    directive = dedent(
        f"""
        Draft this section for {country} in paragraph form (2–5 concise paragraphs, bullets/tables only if explicitly stated).

        Requirements:
        {prompt_text}

        Constraints:
        - Keep claims grounded in allowed sources where available; use conservative language otherwise.
        - Word limit: {word_limit_text}.
        - Return ONLY one strict RFC-8259 JSON object with exactly this shape:
          {{"body": "<STRING>"}}
          Where "body" is:
            • For narrative sections: a single string with the final paragraphs.
            • For table sections: a single string that contains a strict JSON object representing the table schema requested in the prompt (e.g., {{ "table_data": [...] , "summary": "..." }}).
        - No code fences, no trailing commas, double-quoted strings only.
        {feedback_block}
        """
    ).strip()

    msgs = [
        ChatMessage(role="system", content=SECTION_WRITER_SYSTEM),
        ChatMessage(role="user", content="\n".join(opening) + "\n" + directive),
    ]
    return msgs

async def draft_section(client: OpenAIClient, spec: SectionSpec, context: Dict[str, Any], example_override: str | None = None, *, feedback_text: str | None = None) -> str:
    messages = build_messages(spec, context, example_override=example_override, feedback_text=feedback_text)
    return await client.chat(messages, temperature=0.0, max_tokens=1800)
