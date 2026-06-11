"""MA50 스크리너 — signals.json 조립 빌더."""
from __future__ import annotations
from datetime import date
from typing import Optional


def build_signal_item(
    ticker: str,
    signal_type: str,
    state: str,
    score: float,
    trigger_reason: str,
    metrics: dict,
    position_status: Optional[str] = None,
) -> dict:
    """signals.json items 배열의 단일 항목."""
    item: dict = {
        "ticker":         ticker,
        "signal_type":    signal_type,
        "state":          state,
        "score":          score,
        "trigger_reason": trigger_reason,
        "metrics":        metrics,
    }
    if position_status is not None:
        item["position_status"] = position_status
    return item


def build_signals_json(
    as_of: date,
    regime: str,
    items: list,
) -> dict:
    """signals.json 전체 구조."""
    return {
        "as_of":  str(as_of),
        "regime": regime,
        "items":  items,
    }
