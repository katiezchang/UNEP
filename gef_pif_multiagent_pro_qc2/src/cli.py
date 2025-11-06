from __future__ import annotations
import asyncio
from rich.prompt import Prompt
from rich.console import Console
from .main import run

console = Console()

def main():
    console.rule("[bold]GEF-8 PIF Generator — QC Edition[/bold]")
    country = Prompt.ask("Country or Project name", default="Ghana")
    out_stem = Prompt.ask("Output file stem (no extension)", default=f"out/{country}_PIF")
    fmt = Prompt.ask("Format (md/docx/pdf)", default="docx")
    max_sources = int(Prompt.ask("Max sources", default="25"))
    crawl_depth = int(Prompt.ask("Crawl depth", default="2"))
    conf_target = int(Prompt.ask("Confidence target (0-100)", default="90"))
    max_passes = int(Prompt.ask("Max improvement passes", default="3"))
    fetch_conc = int(Prompt.ask("Fetch concurrency", default="4"))
    model = Prompt.ask("OpenAI model (empty = default)", default="")
    load_fb = Prompt.ask("Load feedback from file (optional path)", default="")
    templ = Prompt.ask("Template examples dir (optional)", default="")

    console.print("\n[green]Generating...[/green]\n")
    path = asyncio.run(run(
        country, out_stem, fmt=fmt,
        max_sources=max_sources, crawl_depth=crawl_depth,
        confidence_target=conf_target, max_improvement_passes=max_passes,
        fetch_concurrency=fetch_conc, model=(model or None),
        load_feedback=(load_fb or None), template_dir=(templ or None),
    ))
    console.print(f"[bold]Done.[/bold] Wrote: {path}")

if __name__ == "__main__":
    main()
