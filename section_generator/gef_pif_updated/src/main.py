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
from .prompts.sections_update import SECTIONS #WHAT I UPDATED - katie
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
    sections: list[str] | None = None,
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

    # Optional: targeted section generation only (fast prompt-engineering loop)
    if sections:
        requested = [s.strip() for s in sections if s and s.strip()]
        selected = [k for k in requested if k in SECTIONS]
        if not selected:
            raise ValueError("No valid section keys provided.")

        def _looks_like_table_json(s: str) -> bool:
            try:
                obj = json.loads(s)
                return isinstance(obj, dict) and "table_data" in obj
            except Exception:
                return False

        parts: Dict[str, str] = {}
        overall_conf = 0.0
        for p in range(1, int(max_improvement_passes) + 1):
            # Draft selected sections only
            for key in selected:
                spec = SECTIONS[key]
                raw = await draft_section(
                    client, spec, context,
                    example_override=overrides.get(key),
                    feedback_text=(prev_feedback_text if p > 1 else None),
                )
                obj = parse_or_wrap_body(raw, debug_path=f"out/{key}_last_raw.txt")
                parts[key] = obj.get("body", "")

            # Enforce table JSON if a selected section is a table
            for table_key in ("baseline_stakeholders", "baseline_unfccc_reporting", "other_baseline_initiatives"):
                if table_key not in selected:
                    continue
                body = (parts.get(table_key) or "").strip()
                if not body or not _looks_like_table_json(body):
                    spec = SECTIONS[table_key]
                    raw = await draft_section(
                        client, spec, context,
                        example_override=overrides.get(table_key),
                        feedback_text=(prev_feedback_text if p > 1 else None),
                    )
                    obj = parse_or_wrap_body(raw, debug_path=f"out/{table_key}_last_raw.txt")
                    body_new = obj.get("body", "")
                    if body_new:
                        parts[table_key] = body_new

            # Fact-check the subset
            def _normalize_items(items):
                out = []
                for it in (items or []):
                    if isinstance(it, str):
                        out.append(it)
                    elif isinstance(it, dict):
                        for k in ("message", "text", "issue", "description", "detail"):
                            v = it.get(k)
                            if isinstance(v, str) and v.strip():
                                out.append(v.strip())
                                break
                        else:
                            try:
                                out.append(json.dumps(it, ensure_ascii=False))
                            except Exception:
                                out.append(str(it))
                    else:
                        out.append(str(it))
                return out

            fc = await fact_check_sections(client, {"sections": parts, "citations": []})
            fc_conf = float(fc.get("confidence_estimate", 0))
            issues_norm = _normalize_items(fc.get("issues_found", []))
            fixes_norm = _normalize_items(fc.get("fixes_recommended", []))
            risks_norm = _normalize_items(fc.get("residual_risks", []))

            overall_raw = aggregate_confidence(overall_conf, fc_conf)
            overall_adj = adjust_confidence(overall_raw, len(issues_norm), len(risks_norm))
            quality_log.append({
                "pass": p,
                "writer_confidence": overall_conf,
                "checker_confidence": fc_conf,
                "aggregated_confidence_raw": overall_raw,
                "aggregated_confidence_adjusted": overall_adj,
                "issues_found": issues_norm,
                "fixes_recommended": fixes_norm,
                "residual_risks": risks_norm,
                "notes": "Targeted SectionWriter generation",
            })
            overall_conf = overall_adj
            if overall_conf >= float(confidence_target):
                break

            fb_parts = []
            if issues_norm:
                fb_parts.append("Issues found:\n- " + "\n- ".join(issues_norm))
            if fixes_norm:
                fb_parts.append("Fixes recommended:\n- " + "\n- ".join(fixes_norm))
            if risks_norm:
                fb_parts.append("Residual risks:\n- " + "\n- ".join(risks_norm))
            prev_feedback_text = "\n\n".join(fb_parts) if fb_parts else None

        # Attach quality appendix and render
        parts["appendix_quality"] = build_quality_appendix(quality_log, float(confidence_target))
        titles = make_titles(country)
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

    # Helper for normalization
    def _normalize_items(items):
        out = []
        for it in (items or []):
            if isinstance(it, str):
                out.append(it)
            elif isinstance(it, dict):
                for k in ("message", "text", "issue", "description", "detail"):
                    v = it.get(k)
                    if isinstance(v, str) and v.strip():
                        out.append(v.strip())
                        break
                else:
                    try:
                        out.append(json.dumps(it, ensure_ascii=False))
                    except Exception:
                        out.append(str(it))
            else:
                out.append(str(it))
        return out

    # Iterative drafting loop
    parts: Dict[str, str] = {}
    overall_conf = 0.0
    for pass_number in range(1, int(max_improvement_passes) + 1):
        if pass_number == 1:
            # Core via ndc_writer
            ndc_payload = await generate_sections(
                client, country, today_iso, sources_table,
                max_sources=max_sources, crawl_depth=crawl_depth,
                confidence_target=confidence_target, max_improvement_passes=1,
                fetch_concurrency=fetch_concurrency, model=model,
                load_feedback_path=load_feedback, previous_feedback_text=prev_feedback_text
            )
            writer_conf = float(ndc_payload.get("confidence_score", 0))
            overall_conf = writer_conf
            quality_log.append({
                "pass": pass_number,
                "writer_confidence": writer_conf,
                "checker_confidence": None,
                "aggregated_confidence_raw": writer_conf,
                "aggregated_confidence_adjusted": writer_conf,
                "issues_found": _normalize_items(ndc_payload.get("issues_found", [])),
                "fixes_recommended": _normalize_items(ndc_payload.get("fixes_applied", [])),
                "residual_risks": _normalize_items(ndc_payload.get("residual_risks", [])),
                "notes": "Initial writer pass (core via ndc_writer; others via SectionWriter)",
            })
            core = ndc_payload.get("sections", {}) or {}
            parts.update({
                "baseline_national_tf_header": core.get("baseline_national_tf_header", ""),
                "baseline_institutional": core.get("baseline_institutional", ""),
                "baseline_policy": core.get("baseline_policy", ""),
                "baseline_stakeholders": core.get("baseline_stakeholders", ""),
                "baseline_unfccc_reporting": core.get("baseline_unfccc_reporting", ""),
                "module_header": core.get("module_header", ""),
                "module_ghg": core.get("module_ghg", ""),
                "module_adaptation": core.get("module_adaptation", ""),
                "module_ndc_tracking": core.get("module_ndc_tracking", ""),
                "module_support": core.get("module_support", ""),
                "other_baseline_initiatives": core.get("other_baseline_initiatives", ""),
            })
            # Fill missing cores via SectionWriter
            for ck in (
                "baseline_national_tf_header","baseline_institutional","baseline_policy",
                "baseline_stakeholders","baseline_unfccc_reporting",
                "module_header","module_ghg","module_adaptation","module_ndc_tracking","module_support",
                "other_baseline_initiatives",
            ):
                if not (parts.get(ck) or "").strip():
                    spec = SECTIONS.get(ck)
                    if spec:
                        raw = await draft_section(client, spec, context, example_override=overrides.get(ck))
                        obj = parse_or_wrap_body(raw, debug_path=f"out/{ck}_last_raw.txt")
                        parts[ck] = obj.get("body", "")
            # Draft remaining sections
            for key, spec in SECTIONS.items():
                if key in parts and (parts.get(key) or "").strip():
                    continue
                raw = await draft_section(client, spec, context, example_override=overrides.get(key))
                obj = parse_or_wrap_body(raw, debug_path=f"out/{key}_last_raw.txt")
                parts[key] = obj.get("body", "")
        else:
            # Re-draft all via SectionWriter using previous feedback text
            for key, spec in SECTIONS.items():
                raw = await draft_section(client, spec, context, example_override=overrides.get(key), feedback_text=prev_feedback_text)
                obj = parse_or_wrap_body(raw, debug_path=f"out/{key}_last_raw.txt")
                parts[key] = obj.get("body", "")
            quality_log.append({
                "pass": pass_number,
                "writer_confidence": overall_conf,
                "checker_confidence": None,
                "aggregated_confidence_raw": overall_conf,
                "aggregated_confidence_adjusted": overall_conf,
                "issues_found": [],
                "fixes_recommended": [],
                "residual_risks": [],
                "notes": "Writer re-draft via SectionWriter integrating fact-check feedback",
            })

        # Ensure table sections are strict JSON
        import json as _json
        def _looks_like_table_json(s: str) -> bool:
            try:
                obj = _json.loads(s)
                return isinstance(obj, dict) and "table_data" in obj
            except Exception:
                return False
        for table_key in ("baseline_stakeholders", "baseline_unfccc_reporting", "other_baseline_initiatives"):
            body = (parts.get(table_key) or "").strip()
            if not body or not _looks_like_table_json(body):
                spec = SECTIONS.get(table_key)
                if spec:
                    raw = await draft_section(client, spec, context, example_override=overrides.get(table_key), feedback_text=(prev_feedback_text if pass_number > 1 else None))
                    obj = parse_or_wrap_body(raw, debug_path=f"out/{table_key}_last_raw.txt")
                    body_new = obj.get("body", "")
                    if body_new:
                        parts[table_key] = body_new

        # Fact-check combined parts
        fc = await fact_check_sections(client, {"sections": parts, "citations": []})
        fc_conf = float(fc.get("confidence_estimate", 0))
        issues_norm = _normalize_items(fc.get("issues_found", []))
        fixes_norm = _normalize_items(fc.get("fixes_recommended", []))
        risks_norm = _normalize_items(fc.get("residual_risks", []))

        overall_raw = aggregate_confidence(overall_conf, fc_conf)
        overall_adj = adjust_confidence(overall_raw, len(issues_norm), len(risks_norm))

        quality_log[-1]["checker_confidence"] = fc_conf
        quality_log[-1]["aggregated_confidence_raw"] = overall_raw
        quality_log[-1]["aggregated_confidence_adjusted"] = overall_adj
        quality_log[-1]["issues_found"] = issues_norm or quality_log[-1]["issues_found"]
        quality_log[-1]["fixes_recommended"] = fixes_norm
        quality_log[-1]["residual_risks"] = risks_norm

        overall_conf = overall_adj

        if overall_conf >= float(confidence_target):
            break

        fb_parts = []
        if issues_norm:
            fb_parts.append("Issues found:\n- " + "\n- ".join(issues_norm))
        if fixes_norm:
            fb_parts.append("Fixes recommended:\n- " + "\n- ".join(fixes_norm))
        if risks_norm:
            fb_parts.append("Residual risks:\n- " + "\n- ".join(risks_norm))
        prev_feedback_text = "\n\n".join(fb_parts) if fb_parts else None

    # 4) Revise core for style harmonization
    core_for_revise = {
        "baseline_national_tf_header": parts["baseline_national_tf_header"],
        "baseline_institutional": parts["baseline_institutional"],
        "baseline_policy": parts["baseline_policy"],
        "baseline_stakeholders": parts["baseline_stakeholders"],
        "baseline_unfccc_reporting": parts["baseline_unfccc_reporting"],
        "module_header": parts["module_header"],
        "module_ghg": parts["module_ghg"],
        "module_adaptation": parts["module_adaptation"],
        "module_ndc_tracking": parts["module_ndc_tracking"],
        "module_support": parts["module_support"],
        "other_baseline_initiatives": parts["other_baseline_initiatives"],
    }
    revised_core = await revise_all(client, core_for_revise)
    parts["baseline_national_tf_header"] = revised_core.get("baseline_national_tf_header", parts["baseline_national_tf_header"])
    parts["baseline_institutional"] = revised_core.get("baseline_institutional", parts["baseline_institutional"])
    parts["baseline_policy"] = revised_core.get("baseline_policy", parts["baseline_policy"])
    parts["baseline_stakeholders"] = revised_core.get("baseline_stakeholders", parts["baseline_stakeholders"])
    parts["baseline_unfccc_reporting"] = revised_core.get("baseline_unfccc_reporting", parts["baseline_unfccc_reporting"])
    parts["module_header"] = revised_core.get("module_header", parts["module_header"])
    parts["module_ghg"] = revised_core.get("module_ghg", parts["module_ghg"])
    parts["module_adaptation"] = revised_core.get("module_adaptation", parts["module_adaptation"])
    parts["module_ndc_tracking"] = revised_core.get("ndc_tracking_module", parts["module_ndc_tracking"])
    parts["module_support"] = revised_core.get("support_needed_and_received", parts["module_support"])
    parts["other_baseline_initiatives"] = revised_core.get("other_baseline_initiatives", parts["other_baseline_initiatives"])

    # 5) Final fact-check across ALL sections (core + section-writer)
    try:
        combined_fc = await fact_check_sections(client, {
            "sections": parts,
            "citations": [],
        })
        quality_log.append({
            "pass": (pass_number + 1),
            "writer_confidence": None,
            "checker_confidence": float(combined_fc.get("confidence_estimate", 0)),
            "aggregated_confidence_raw": None,
            "aggregated_confidence_adjusted": None,
            "issues_found": _normalize_items(combined_fc.get("issues_found", [])),
            "fixes_recommended": _normalize_items(combined_fc.get("fixes_recommended", [])),
            "residual_risks": _normalize_items(combined_fc.get("residual_risks", [])),
            "notes": "Final combined fact-check across all sections",
        })
    except Exception:
        pass

    # 6) Build Quality Appendix and attach
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
    parser.add_argument("--sections", type=str, default=None, help="Comma-separated section keys to generate only those")
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
    only_sections = [s.strip() for s in args.sections.split(",")] if args.sections else None
    path = asyncio.run(run(
        args.country, out_stem, fmt=args.format, sections=only_sections,
        max_sources=args.max_sources, crawl_depth=args.crawl_depth,
        confidence_target=args.confidence_target, max_improvement_passes=args.max_passes,
        fetch_concurrency=args.fetch_concurrency, model=args.model,
        load_feedback=args.load_feedback, template_dir=args.template_dir,
    ))
    print(f"Wrote: {path}")
