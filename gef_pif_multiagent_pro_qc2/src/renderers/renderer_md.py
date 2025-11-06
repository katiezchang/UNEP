from __future__ import annotations
from typing import Dict, List

def assemble_document_md(parts: Dict[str, str], titles: Dict[str, str], country: str) -> str:
    order = [
        "rationale_intro","paris_etf","climate_transparency_country",
        "baseline_national_tf_header","baseline_institutional","baseline_policy",
        "baseline_stakeholders","baseline_unfccc_reporting",
        "module_header","module_ghg","module_adaptation","module_ndc_tracking","module_support",
        "other_baseline_initiatives","key_barriers",
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
        body = "\n\n".join([p.strip() for p in body.split("\n") if p.strip()])
        lines.append(body + "\n\n")
    return "\n".join(lines)
