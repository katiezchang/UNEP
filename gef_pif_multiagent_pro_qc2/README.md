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

export OPENAI_API_KEY=sk-...

# Interactive
python3 -m src.cli

# Or direct
python3 -m src.main --country "Ghana" --out out/Ghana_PIF --format docx   --max-sources 25 --crawl-depth 2 --confidence-target 90 --max-passes 3   --fetch-concurrency 4 --model gpt-4o-mini
```
