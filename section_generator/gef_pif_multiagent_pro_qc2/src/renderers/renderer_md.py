from __future__ import annotations
from typing import Dict, List, Any
import json

def _try_parse_table(body: str) -> Dict[str, Any] | None:
    try:
        obj = json.loads(body)
        if isinstance(obj, dict) and "table_data" in obj:
            return obj
    except Exception:
        pass
    return None

def _render_stakeholders_md(obj: Dict[str, Any]) -> str:
    lines: List[str] = []
    for group in obj.get("table_data", []):
        group_type = group.get("type", "Group")
        lines.append(f"### {group_type}")
        lines.append("")
        # Detect simplified schema (name + existing_activities) vs original detailed schema
        entries = group.get("entries", []) or []
        use_simple = any(isinstance(e, dict) and ("existing_activities" in e) for e in entries)
        if use_simple:
            lines.append("| Name | Existing activities |")
            lines.append("|---|---|")
        else:
            lines.append("| Name | Activities | Source URLs | Confidence |")
            lines.append("|---|---|---|---|")
        for entry in group.get("entries", []):
            name = entry.get("name", "")
            if use_simple:
                existing = entry.get("existing_activities", "")
                lines.append(f"| {name} | {existing} |")
            else:
                activities = ", ".join(entry.get("activities", []) or [])
                urls = ", ".join(entry.get("source_urls", []) or [])
                conf = str(entry.get("confidence", ""))
                lines.append(f"| {name} | {activities} | {urls} | {conf} |")
        lines.append("")
    return "\n".join(lines).strip()

def _render_simple_table_md(obj: Dict[str, Any], columns: List[str]) -> str:
    lines: List[str] = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")
    for row in obj.get("table_data", []):
        vals = [str(row.get(col, "")) for col in columns]
        lines.append("| " + " | ".join(vals) + " |")
    if "summary" in obj and isinstance(obj["summary"], str) and obj["summary"].strip():
        lines.append("")
        lines.append(obj["summary"].strip())
    return "\n".join(lines).strip()

def _render_other_baseline_initiatives_md(obj: Dict[str, Any]) -> str:
    # Support both old and new key names via alias resolution
    aliases: Dict[str, List[str]] = {
        "program": ["program_project", "program/project", "program", "project"],
        "entities": ["leading_entities", "Leading Ministry and Supporting Entities"],
        "desc": ["description"],
        "duration": ["duration"],
        "value": ["value_usd", "value"],
        "relation": ["relation_to_etf", "Relationship with ETF and the transparency system"],
    }
    def pick(row: Dict[str, Any], keys: List[str]) -> str:
        for k in keys:
            v = row.get(k)
            if isinstance(v, (str, int, float)) and str(v).strip():
                return str(v)
        return ""
    headers = ["Program/Project", "Leading Entities", "Description", "Duration", "Value (USD)", "Relation to ETF"]
    lines: List[str] = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in obj.get("table_data", []):
        vals = [
            pick(row, aliases["program"]),
            pick(row, aliases["entities"]),
            pick(row, aliases["desc"]),
            pick(row, aliases["duration"]),
            pick(row, aliases["value"]),
            pick(row, aliases["relation"]),
        ]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines).strip()

def assemble_document_md(parts: Dict[str, str], titles: Dict[str, str], country: str) -> str:
    order = [
        "rationale_intro","paris_etf","climate_transparency_country",
        "baseline_national_tf_header","baseline_institutional","baseline_policy",
        "baseline_stakeholders","baseline_unfccc_reporting",
        "module_header","module_ghg","module_adaptation","module_ndc_tracking","module_support",
        "other_baseline_initiatives","key_barriers","barrier1","barrier2","barrier3",
        "appendix_quality"
    ]
    lines: List[str] = []
    lines.append(f"# GEF-8 PROJECT IDENTIFICATION FORM (PIF) — {country}\n\n")
    for key in order:
        body = (parts.get(key) or "").strip()
        if not body:
            continue
        title = titles.get(key, key)
        lines.append(f"## {title}\n")
        # Try to render table formats for specific sections
        table_obj = _try_parse_table(body)
        if key == "baseline_stakeholders" and table_obj:
            lines.append(_render_stakeholders_md(table_obj) + "\n\n")
            continue
        if key == "baseline_unfccc_reporting" and table_obj:
            lines.append(_render_simple_table_md(table_obj, ["year", "report", "comment"]) + "\n\n")
            continue
        if key == "other_baseline_initiatives" and table_obj:
            lines.append(_render_other_baseline_initiatives_md(table_obj) + "\n\n")
            continue
        # Fallback: narrative
        body_fmt = "\n\n".join([p.strip() for p in body.split("\n") if p.strip()])
        lines.append(body_fmt + "\n\n")
    return "\n".join(lines)
