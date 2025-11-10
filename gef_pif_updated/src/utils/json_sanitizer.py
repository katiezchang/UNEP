from __future__ import annotations
import json, re, ast, os
from typing import Any
try:
    import json5 as _json5
except Exception:
    _json5 = None

def parse_model_json(raw: str, debug_path: str | None = None) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.S|re.I)
    if m:
        snippet = m.group(1)
        for attempt in (json.loads, ast.literal_eval, (_json5.loads if _json5 else None)):
            if attempt:
                try:
                    return attempt(snippet)
                except Exception:
                    pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        blob = raw[start:end+1]
        for attempt in (json.loads, ast.literal_eval, (_json5.loads if _json5 else None)):
            if attempt:
                try:
                    return attempt(blob)
                except Exception:
                    pass
    if debug_path:
        try:
            os.makedirs(os.path.dirname(debug_path) or ".", exist_ok=True)
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(raw)
        except Exception:
            pass
    raise ValueError("Model did not return valid JSON; raw content saved for inspection.")

def _strip_code_fences(text: str) -> str:
    text = re.sub(r"^```[\w-]*\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def parse_or_wrap_body(raw: str, debug_path: str | None = None):
    try:
        return parse_model_json(raw, debug_path=debug_path)
    except Exception:
        cleaned = _strip_code_fences(raw)
        cleaned = re.sub(r"^(assistant|system|user)\s*:\s*", "", cleaned, flags=re.I).strip()
        if debug_path:
            try:
                os.makedirs(os.path.dirname(debug_path) or ".", exist_ok=True)
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(raw)
            except Exception:
                pass
        return {"body": cleaned}
