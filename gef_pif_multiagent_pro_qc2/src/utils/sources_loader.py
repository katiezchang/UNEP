from __future__ import annotations
import os
def load_sources_table(country: str) -> str:
    base = os.path.join(os.getcwd(), "sources")
    common_p = os.path.join(base, "_common.txt")
    country_p = os.path.join(base, f"{country.lower()}.txt")
    def read_if(p: str) -> str:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""
    common = read_if(common_p)
    target = read_if(country_p)
    lines = []
    idx = 1
    for block in [common, target]:
        if block:
            for row in block.splitlines():
                row = row.strip()
                if not row:
                    continue
                lines.append(f"S{idx}\t{row}")
                idx += 1
    if not lines:
        lines = ["S1\t[TBD source placeholder]"]
    return "\n".join(lines)
