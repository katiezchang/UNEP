from __future__ import annotations
import asyncio, os, json, datetime
from typing import Dict, Any

from .models.openai_client import OpenAIClient
from .agents.ndc_writer import generate_sections
from .agents.section_writer import draft_section, SectionSpec
from .agents.fact_checker import fact_check_sections
from .agents.accuracy_agent import aggregate_confidence, adjust_confidence, should_continue
from .agents.reviser import revise_all
from .agents.final_drafter import make_titles
from .prompts.sections import SECTIONS
from .renderers.renderer_md import assemble_document_md
from .renderers.renderer_docx import assemble_document_docx
from .renderers.renderer_pdf import assemble_document_pdf
from .utils.file_io import write_text
from .utils.sources_loader import load_sources_table
from .utils.template_overrides import load_overrides
from .utils.json_sanitizer import parse_model_json, parse_or_wrap_body

def build_quality_appendix(quality_log, confidence_target: float) -> str:
    lines = []
    lines.append("This appendix summarizes the quality loop across improvement passes, including writer and fact-checker confidence, raw aggregated confidence, adjusted (penalized) confidence, and the key feedback integrated into each iteration.\n")
    lines.append(f"Target confidence: {confidence_target:.1f}\n")
    for entry in quality_log:
        p = entry.get("pass")
        w = entry.get("writer_confidence")
        c = entry.get("checker_confidence")
        a_raw = entry.get("aggregated_confidence_raw")
        a_adj = entry.get("aggregated_confidence_adjusted")
        notes = entry.get("notes") or ""
        issues = entry.get("issues_found") or []
        fixes = entry.get("fixes_recommended") or []
        risks = entry.get("residual_risks") or []

        lines.append(f"Pass {p} — {notes}")
        lines.append(f"  • Writer confidence: {w if w is not None else 'n/a'}")
        lines.append(f"  • Fact-checker confidence: {c if c is not None else 'n/a'}")
        lines.append(f"  • Aggregated (raw): {a_raw if a_raw is not None else 'n/a'}")
        lines.append(f"  • Aggregated (adjusted for issues/risks): {a_adj if a_adj is not None else 'n/a'}")

        if issues:
            lines.append("  • Key issues found:")
            for s in issues[:8]:
                lines.append(f"     - {s}")
            if len(issues) > 8:
                lines.append(f"     - (+{len(issues)-8} more)")
        if fixes:
            lines.append("  • Fixes recommended / applied:")
            for s in fixes[:8]:
                lines.append(f"     - {s}")
            if len(fixes) > 8:
                lines.append(f"     - (+{len(fixes)-8} more)")
        if risks:
            lines.append("  • Residual risks / potential red flags:")
            for s in risks[:8]:
                lines.append(f"     - {s}")
            if len(risks) > 8:
                lines.append(f"     - (+{len(risks)-8} more)")
        lines.append("")
    return "\n".join(lines).strip()

async def run(
    country: str,
    out_stem: str,
    fmt: str = "docx",
    *,
    max_sources: int = 25,
    crawl_depth: int = 2,
    confidence_target: int = 90,
    max_improvement_passes: int = 3,
    fetch_concurrency: int = 4,
    model: str | None = None,
    load_feedback: str | None = None,
    template_dir: str | None = None,
) -> str:
    client = OpenAIClient(model=model)
    today_iso = datetime.date.today().isoformat()
    os.makedirs("out", exist_ok=True)
    sources_table = load_sources_table(country)
    overrides = load_overrides(template_dir)

    context: Dict[str, Any] = {
        "country": country,
        "UNFCCC_sign_date": "[TBD]",
        "UNFCCC_rat_date": "[TBD]",
        "KP_rat_date": "[TBD]",
        "PA_rat_date": "[TBD]",
        "PA_adopt_date": "[TBD]",
        "existing_prompts": {
            "module_ndc_tracking": (
                "Using prior system prompts, generate baseline for NDC Tracking: current coordination, pilots, templates, "
                "integration with planning, gaps in mandates/tools/reporting cycles, subnational coverage, recommendations."
            ),
            "module_support": (
                "Using prior prompts, generate Support Needed & Received baseline: finance needs and flows, tracking systems/templates, "
                "institutional mandates, gaps (disaggregation, alignment, off-budget), and next steps."
            ),
        },
    }

    prev_feedback_text = None
    if load_feedback and os.path.exists(load_feedback):
        with open(load_feedback, "r", encoding="utf-8") as f:
            prev_feedback_text = f.read()

    quality_log = []

    # 1) NDC writer for three core sections with internal self-loop (confidence)
    draft_payload = await generate_sections(
        client, country, today_iso, sources_table,
        max_sources=max_sources, crawl_depth=crawl_depth,
        confidence_target=confidence_target, max_improvement_passes=1,
        fetch_concurrency=fetch_concurrency, model=model,
        load_feedback_path=load_feedback, previous_feedback_text=prev_feedback_text
    )
    pass_number = 1
    writer_conf = float(draft_payload.get("confidence_score", 0))

    # Log initial writer pass
    quality_log.append({
        "pass": pass_number,
        "writer_confidence": writer_conf,
        "checker_confidence": None,
        "aggregated_confidence_raw": writer_conf,
        "aggregated_confidence_adjusted": writer_conf,
        "issues_found": draft_payload.get("issues_found", []),
        "fixes_recommended": draft_payload.get("fixes_applied", []),
        "residual_risks": draft_payload.get("residual_risks", []),
        "notes": "Initial writer pass",
    })

    overall_conf = writer_conf

    while True:
        # 2) Fact-check
        fc = await fact_check_sections(client, draft_payload)
        fc_conf = float(fc.get("confidence_estimate", 0))

        # Raw aggregation (weighted towards fact-checker)
        overall_raw = aggregate_confidence(overall_conf, fc_conf)

        # Adjust for issues/risks
        issues_count = len(fc.get("issues_found", []) or [])
        residuals_count = len(fc.get("residual_risks", []) or [])
        overall_adj = adjust_confidence(overall_raw, issues_count, residuals_count)

        # Update current log entry
        quality_log[-1]["checker_confidence"] = fc_conf
        quality_log[-1]["aggregated_confidence_raw"] = overall_raw
        quality_log[-1]["aggregated_confidence_adjusted"] = overall_adj
        quality_log[-1]["issues_found"] = fc.get("issues_found", []) or quality_log[-1]["issues_found"]
        quality_log[-1]["fixes_recommended"] = fc.get("fixes_recommended", [])
        quality_log[-1]["residual_risks"] = fc.get("residual_risks", [])

        # Use adjusted score for gating
        overall_conf = overall_adj

        if not should_continue(overall_conf, float(confidence_target), pass_number, int(max_improvement_passes)):
            break

        # Summarize feedback passed to re-draft
        fb_parts = []
        if fc.get("issues_found"):
            fb_parts.append("Issues found:\n- " + "\n- ".join(fc["issues_found"]))
        if fc.get("fixes_recommended"):
            fb_parts.append("Fixes recommended:\n- " + "\n- ".join(fc["fixes_recommended"]))
        if fc.get("residual_risks"):
            fb_parts.append("Residual risks:\n- " + "\n- ".join(fc["residual_risks"]))
        feedback_text = "\n\n".join(fb_parts) if fb_parts else None

        pass_number += 1
        draft_payload = await generate_sections(
            client, country, today_iso, sources_table,
            max_sources=max_sources, crawl_depth=crawl_depth,
            confidence_target=confidence_target, max_improvement_passes=1,
            fetch_concurrency=fetch_concurrency, model=model,
            previous_feedback_text=feedback_text
        )
        writer_conf = float(draft_payload.get("confidence_score", 0))

        # Log new writer pass placeholder (checker will update in next loop iteration)
        quality_log.append({
            "pass": pass_number,
            "writer_confidence": writer_conf,
            "checker_confidence": None,
            "aggregated_confidence_raw": writer_conf,
            "aggregated_confidence_adjusted": writer_conf,
            "issues_found": draft_payload.get("issues_found", []),
            "fixes_recommended": draft_payload.get("fixes_applied", []),
            "residual_risks": draft_payload.get("residual_risks", []),
            "notes": "Writer re-draft after integrating fact-check feedback",
        })

        if pass_number >= max_improvement_passes:
            break

    # Gather core sections
    core_sections = draft_payload.get("sections", {})
    parts: Dict[str, str] = {}
    parts["module_ndc_tracking"] = core_sections.get("ndc_tracking_module", "")
    parts["module_support"] = core_sections.get("support_needed_and_received", "")
    parts["other_baseline_initiatives"] = core_sections.get("other_baseline_initiatives", "")

    # 3) Draft the rest with SectionWriter
    for key, spec in SECTIONS.items():
        if key in parts:
            continue
        example = overrides.get(key)
        raw = await draft_section(client, spec, context, example_override=example)
        obj = parse_or_wrap_body(raw, debug_path=f"out/{key}_last_raw.txt")
        body = obj.get("body", "")
        parts[key] = body

    # 4) Revise core for style harmonization
    core_for_revise = {
        "ndc_tracking_module": parts["module_ndc_tracking"],
        "support_needed_and_received": parts["module_support"],
        "other_baseline_initiatives": parts["other_baseline_initiatives"],
    }
    revised_core = await revise_all(client, core_for_revise)
    parts["module_ndc_tracking"] = revised_core.get("ndc_tracking_module", parts["module_ndc_tracking"])
    parts["module_support"] = revised_core.get("support_needed_and_received", parts["module_support"])
    parts["other_baseline_initiatives"] = revised_core.get("other_baseline_initiatives", parts["other_baseline_initiatives"])

    # 5) Build Quality Appendix and attach
    appendix_text = build_quality_appendix(quality_log, float(confidence_target))
    parts["appendix_quality"] = appendix_text

    titles = make_titles(country)

    # Render
    if fmt == "md":
        text = assemble_document_md(parts, titles, country)
        out_path = out_stem if out_stem.endswith(".md") else out_stem + ".md"
        write_text(out_path, text)
        return out_path
    elif fmt == "docx":
        out_path = out_stem if out_stem.endswith(".docx") else out_stem + ".docx"
        return assemble_document_docx(parts, titles, country, out_path)
    elif fmt == "pdf":
        out_path = out_stem if out_stem.endswith(".pdf") else out_stem + ".pdf"
        return assemble_document_pdf(parts, titles, country, out_path)
    else:
        raise ValueError("Unknown format. Use md|docx|pdf.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GEF-8 PIF Generator (QC Edition)")
    parser.add_argument("--country", required=True)
    parser.add_argument("--out", default=None, help="Output path stem (no extension)")
    parser.add_argument("--format", default="docx", choices=["md","docx","pdf"])
    parser.add_argument("--max-sources", type=int, default=25)
    parser.add_argument("--crawl-depth", type=int, default=2)
    parser.add_argument("--confidence-target", type=int, default=90)
    parser.add_argument("--max-passes", type=int, default=3)
    parser.add_argument("--fetch-concurrency", type=int, default=4)
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--load-feedback", type=str, default=None)
    parser.add_argument("--template-dir", type=str, default=None)
    args = parser.parse_args()

    out_stem = args.out or f"out/{args.country}_PIF"
    path = asyncio.run(run(
        args.country, out_stem, fmt=args.format,
        max_sources=args.max_sources, crawl_depth=args.crawl_depth,
        confidence_target=args.confidence_target, max_improvement_passes=args.max_passes,
        fetch_concurrency=args.fetch_concurrency, model=args.model,
        load_feedback=args.load_feedback, template_dir=args.template_dir,
    ))
    print(f"Wrote: {path}")
