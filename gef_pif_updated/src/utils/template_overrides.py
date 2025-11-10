from __future__ import annotations
import os, json
def load_overrides(template_dir: str | None) -> dict:
    data = {}
    if not template_dir or not os.path.isdir(template_dir):
        return data
    jpath = os.path.join(template_dir, "template.json")
    if os.path.exists(jpath):
        try:
            with open(jpath, "r", encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, dict):
                data.update(m)
        except Exception:
            pass
    for name in os.listdir(template_dir):
        if name == "template.json":
            continue
        if name.lower().endswith((".txt", ".md")):
            key = os.path.splitext(name)[0]
            try:
                with open(os.path.join(template_dir, name), "r", encoding="utf-8") as f:
                    data[key] = f.read()
            except Exception:
                pass
    return data
