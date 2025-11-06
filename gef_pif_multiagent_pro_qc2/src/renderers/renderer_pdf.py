from __future__ import annotations
from typing import Dict
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

def assemble_document_pdf(parts: Dict[str, str], titles: Dict[str, str], country: str, out_path: str) -> str:
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    order = [
        "rationale_intro","paris_etf","climate_transparency_country",
        "baseline_national_tf_header","baseline_institutional","baseline_policy",
        "baseline_stakeholders","baseline_unfccc_reporting",
        "module_header","module_ghg","module_adaptation","module_ndc_tracking","module_support",
        "other_baseline_initiatives","key_barriers",
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

    draw_wrapped(f"GEF-8 PROJECT IDENTIFICATION FORM (PIF) — {country}", size=14, leading=18, bold=True)
    y -= 8

    for key in order:
        body = (parts.get(key) or "").strip()
        if not body: continue
        draw_wrapped(titles.get(key, key), size=12, leading=16, bold=True); y -= 4
        for p in [p.strip() for p in body.split("\n") if p.strip()]:
            draw_wrapped(p, size=11, leading=14); y -= 8

    c.save()
    return out_path
