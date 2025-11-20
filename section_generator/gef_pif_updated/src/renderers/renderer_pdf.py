from __future__ import annotations
from typing import Dict, Any, List
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os
import json

def _try_parse_table(body: str) -> Dict[str, Any] | None:
    try:
        obj = json.loads(body)
        if isinstance(obj, dict) and "table_data" in obj:
            return obj
    except Exception:
        pass
    return None

def assemble_document_pdf(parts: Dict[str, str], titles: Dict[str, str], country: str, out_path: str) -> str:
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    order = [
        "rationale_intro","paris_etf","climate_transparency_country",
        "baseline_national_tf_header","baseline_institutional","baseline_policy",
        "baseline_stakeholders","baseline_unfccc_reporting",
        "module_header","module_ghg","module_adaptation","module_ndc_tracking","module_support",
        "other_baseline_initiatives","key_barriers","barrier1","barrier2","barrier3",
        "appendix_quality"
    ]
    c = canvas.Canvas(out_path, pagesize=LETTER)
    width, height = LETTER
    left = 1*inch; right = width - 1*inch; top = height - 1*inch
    y = top

    def draw_wrapped(text, font="Times-Roman", size=11, leading=14, bold=False):
        nonlocal y
        from reportlab.lib.utils import simpleSplit
        c.setFont("Times-Bold" if bold else font, size)
        lines = simpleSplit(text, "Times-Bold" if bold else font, size, right-left)
        for line in lines:
            if y < 1*inch:
                c.showPage(); y = top
                c.setFont("Times-Bold" if bold else font, size)
            c.drawString(left, y, line); y -= leading

    def draw_table(columns: List[str], rows: List[List[str]]):
        nonlocal y
        # simple text table rendering
        draw_wrapped(" | ".join(columns), bold=True); y -= 2
        for r in rows:
            draw_wrapped(" | ".join(r)); y -= 2

    def render_other_baseline_initiatives(obj: Dict[str, Any]):
        aliases = {
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
        cols = ["Program/Project","Leading Entities","Description","Duration","Value (USD)","Relation to ETF"]
        rows: List[List[str]] = []
        for row in obj.get("table_data", []):
            rows.append([
                pick(row, aliases["program"]),
                pick(row, aliases["entities"]),
                pick(row, aliases["desc"]),
                pick(row, aliases["duration"]),
                pick(row, aliases["value"]),
                pick(row, aliases["relation"]),
            ])
        draw_table(cols, rows)

    draw_wrapped(f"GEF-8 PROJECT IDENTIFICATION FORM (PIF) — {country}", size=14, leading=18, bold=True)
    y -= 8

    for key in order:
        body = (parts.get(key) or "").strip()
        if not body: continue
        draw_wrapped(titles.get(key, key), size=12, leading=16, bold=True); y -= 4
        table_obj = _try_parse_table(body)
        if key == "baseline_unfccc_reporting" and table_obj:
            cols = ["year","report","comment"]
            rows = [[str(row.get(col, "")) for col in cols] for row in table_obj.get("table_data", [])]
            draw_table(cols, rows); y -= 8
            summary = table_obj.get("summary")
            if isinstance(summary, str) and summary.strip():
                draw_wrapped(summary.strip(), size=11, leading=14); y -= 8
            continue
        if key == "other_baseline_initiatives" and table_obj:
            render_other_baseline_initiatives(table_obj); y -= 8
            continue
        if key == "baseline_stakeholders" and table_obj:
            for group in table_obj.get("table_data", []):
                draw_wrapped(group.get("type","Group"), size=11, leading=14, bold=True); y -= 4
                entries = group.get("entries", []) or []
                use_simple = any(isinstance(e, dict) and ("existing_activities" in e) for e in entries)
                if use_simple:
                    cols = ["Name","Existing activities"]
                    rows: List[List[str]] = []
                    for entry in entries:
                        rows.append([
                            str(entry.get("name","")),
                            str(entry.get("existing_activities","")),
                        ])
                    draw_table(cols, rows); y -= 8
                else:
                    cols = ["Name","Activities","Source URLs","Confidence"]
                    rows: List[List[str]] = []
                    for entry in entries:
                        rows.append([
                            str(entry.get("name","")),
                            ", ".join(entry.get("activities", []) or []),
                            ", ".join(entry.get("source_urls", []) or []),
                            str(entry.get("confidence","")),
                        ])
                    draw_table(cols, rows); y -= 8
            continue
        for p in [p.strip() for p in body.split("\n") if p.strip()]:
            draw_wrapped(p, size=11, leading=14); y -= 8

    c.save()
    return out_path
