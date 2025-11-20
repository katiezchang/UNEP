# GEF PIF Generator — Multi‑Agent (QC Edition)

Includes:
- Multi-agent loop (Writer → Fact‑Checker → Accuracy → Reviser)
- Paragraph-first sections
- Strict/forgiving JSON parsing for LLM outputs
- **Quality & Confidence Appendix** with per-pass scores and feedback
- Exports: DOCX / PDF / Markdown

## Quickstart
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

export OPENAI_API_KEY=

# Interactive
python3 -m src.cli

# Or direct
python3 -m src.main --country "Cuba" --out out/Cuba_PIF --format docx   --max-sources 25 --crawl-depth 2 --confidence-target 90 --max-passes 3   --fetch-concurrency 4 --model gpt-4o-mini
```
# entire draft
OPENAI_API_KEY=" " python3 -m src.main --country "Cuba" --out out/Cuba_PIF --format docx --max-sources 25 --crawl-depth 2 --confidence-target 90 --max-passes 3 --fetch-concurrency 4 --model gpt-4o-mini
# by section
OPENAI_API_KEY=" " python -m src.main --country "Cuba" --sections "baseline_stakeholders,baseline_unfccc_reporting" --out out/Cuba_subset --format docx --max-sources 25 --crawl-depth 2 --confidence-target 90 --max-passes 2 --fetch-concurrency 4 --model gpt-4o-mini

sections: 
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
