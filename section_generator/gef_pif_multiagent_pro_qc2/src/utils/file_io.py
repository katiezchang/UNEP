from __future__ import annotations
import os

def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)

def write_text(path: str, text: str) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
