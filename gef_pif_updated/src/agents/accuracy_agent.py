from __future__ import annotations

def _clamp01(x: float) -> float:
    try:
        v = float(x)
    except Exception:
        v = 0.0
    if v < 0: v = 0.0
    if v > 100: v = 100.0
    return v

def aggregate_confidence(writer_score: float, checker_score: float) -> float:
    """
    Weighted aggregation that prioritizes the fact-checker's score, but uses writer when present.
    - If writer is 0 and checker > 0, treat writer as "unknown" and rely 90% on checker.
    - Otherwise, blend 40% writer and 60% checker.
    """
    w = _clamp01(writer_score)
    c = _clamp01(checker_score)
    if w == 0 and c > 0:
        return round(0.90 * c, 1)
    return round(0.40 * w + 0.60 * c, 1)

def adjust_confidence(base: float, issues_count: int, residuals_count: int) -> float:
    """
    Penalize aggregate confidence for outstanding issues and residual risks.
    Simple linear penalty:
      -2 per issue
      -3 per residual risk
    Never below 0.
    """
    try:
        issues = max(int(issues_count or 0), 0)
        residuals = max(int(residuals_count or 0), 0)
    except Exception:
        issues, residuals = 0, 0
    penalty = issues * 2 + residuals * 3
    adj = max(_clamp01(base) - penalty, 0.0)
    return round(adj, 1)

def should_continue(current_score: float, target: float, pass_number: int, max_passes: int) -> bool:
    if current_score >= target:
        return False
    return pass_number < max_passes
