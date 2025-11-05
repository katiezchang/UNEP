from __future__ import annotations
import os, argparse, asyncio, datetime

from src.config import DEFAULT_MODEL, OUT_DIR, SOURCES_DIR
from src.retriever.web_retriever import gather_sources, default_seeds
from src.agents.ndc_writer import generate_sections
from src.agents.fact_checker import check_facts
from src.agents.accuracy_agent import second_opinion
from src.agents.final_drafter import finalize
from src.agents.reviser import revise_with_feedback
from src.models.openai_client import OpenAIClient
from src.utils.score import extract_confidence

def parse_args():
    ap = argparse.ArgumentParser(description="GEF PIF Multi-Agent Drafting Pipeline (Terminal Edition)")
    ap.add_argument("--country", required=True)
    ap.add_argument("--country-portal", default=None, help="Official admin climate portal URL (optional).")
    ap.add_argument("--max-sources", type=int, default=10)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--feedback", default=None, help="Path to a feedback text/markdown file to integrate into the draft.")
    ap.add_argument("--sources-file", default=None, help="Path to a newline-delimited list of allowed-domain URLs.")
    ap.add_argument("--confidence-target", type=int, default=85, help="If Fact-Checker confidence < target, run strict re-check and revise.")
    ap.add_argument("--max-passes", type=int, default=2, help="Re-run revise/check/finalize up to N times to reach confidence target.")
    ap.add_argument("--depth", type=int, default=1, help="Crawler depth (1 = just seeds).")
    ap.add_argument("--auto-sources", action="store_true", help="Auto-load sources/<country>.txt and sources/_common.txt if present.")
    return ap.parse_args()

async def run(country: str, seeds: list[str], max_sources: int, concurrency: int, no_fetch: bool, model: str, verbose: bool, dry: bool, max_passes: int, depth: int, confidence_target: int, feedback_path: str | None):
    today_iso = datetime.date.today().isoformat()
    client = OpenAIClient(model=model)

    if verbose:
        print("Fetching sources...")
    source_table = await gather_sources(seeds, no_fetch=no_fetch, max_sources=max_sources, concurrency=concurrency, depth=depth, verbose=verbose)

    if verbose:
        print("Running Agent 1 (NDC Writer)...")
    agent1_output = await generate_sections(client, country, today_iso, source_table)

    if verbose:
        print("Running Agent 2 (Fact-Checker)...")
    fact_report = await check_facts(client, agent1_output, source_table, strict=False)
    conf = extract_confidence(fact_report)
    if verbose:
        print(f"Fact-Checker confidence: {conf}% (target {confidence_target}%)")
    if conf < confidence_target:
        if verbose:
            print("Confidence below target — running Strict Fact-Checker...")
        fact_report = await check_facts(client, agent1_output, source_table, strict=True)

    if verbose:
        print("Running Accuracy Agent...")
    accuracy_json = await second_opinion(client, agent1_output, fact_report)

    if verbose:
        print("Running Agent 3 (Final Drafter)...")
    final_text = await finalize(client, agent1_output, fact_report, accuracy_json)

    revised_text = final_text
    feedback_text = None
    if os.getenv("FEEDBACK_INLINE"):
        feedback_text = os.getenv("FEEDBACK_INLINE")
    elif feedback_path:
        with open(feedback_path, "r", encoding="utf-8") as f:
            feedback_text = f.read()

    passes = 0
    artifact = final_text

    while passes < max_passes:
        current_text = revised_text if (feedback_text and passes > 0) else artifact

        if verbose:
            print(f"Re-checking confidence (pass {passes+1}/{max_passes})...")
        fact_report2 = await check_facts(client, current_text, source_table, strict=False)
        conf2 = extract_confidence(fact_report2)
        if verbose:
            print(f"Fact-Checker confidence: {conf2}% (target {confidence_target}%)")

        if conf2 >= confidence_target:
            artifact = current_text
            break

        if verbose:
            print("Confidence below target — running Strict Fact-Checker...")
        fact_report2 = await check_facts(client, current_text, source_table, strict=True)

        auto_feedback = None
        if not feedback_text:
            auto_feedback = ("AUTO: Apply all items under 'Suggested Revisions' from the latest Fact-Checker report. "
                             "Prioritize adding ISO-dated citations, triangulating numerics (UNFCCC + PATPA/ICAT), "
                             "and removing or softening unsupported claims.")

        if verbose:
            print("Integrating feedback via Reviser...")
        revised_text = await revise_with_feedback(
            client=client,
            current_final_text=current_text,
            user_feedback_text=feedback_text or auto_feedback or "",
            country=country,
            today_iso=today_iso,
            source_table=source_table,
        )

        if verbose:
            print("Running Accuracy Agent on revised draft...")
        accuracy_json2 = await second_opinion(client, revised_text, fact_report2)

        if verbose:
            print("Finalizing revised draft...")
        revised_text = await finalize(client, revised_text, fact_report2, accuracy_json2)

        artifact = revised_text
        passes += 1

    if not dry:
        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"{country}_final.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(artifact)
        if verbose:
            print(f"Saved: {out_path}")
    else:
        print(artifact)

def load_seeds(args) -> list[str]:
    seeds = default_seeds(args.country, args.country_portal)
    if args.sources_file:
        with open(args.sources_file, "r", encoding="utf-8") as f:
            extra = [ln.strip() for ln in f if ln.strip()]
        return extra + seeds

    if args.auto_sources or True:
        country_key = args.country.lower().replace(" ", "_")
        base = os.getenv("SOURCES_DIR", "sources")
        auto_file = os.path.join(base, f"{country_key}.txt")
        if os.path.exists(auto_file):
            with open(auto_file, "r", encoding="utf-8") as f:
                extra = [ln.strip() for ln in f if ln.strip()]
            seeds = extra + seeds
        common_file = os.path.join(base, "_common.txt")
        if os.path.exists(common_file):
            with open(common_file, "r", encoding="utf-8") as f:
                common_extra = [ln.strip() for ln in f if ln.strip()]
            seeds = common_extra + seeds
    return seeds

if __name__ == "__main__":
    args = parse_args()
    seeds = load_seeds(args)
    asyncio.run(
        run(
            country=args.country,
            seeds=seeds,
            max_sources=args.max_sources,
            concurrency=args.concurrency,
            no_fetch=args.no_fetch,
            model=args.model,
            verbose=args.verbose,
            dry=args.dry,
            max_passes=args.max_passes,
            depth=args.depth,
            confidence_target=args.confidence_target,
            feedback_path=args.feedback,
        )
    )
