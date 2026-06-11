"""MA50 ticker 상태 persistence — 순수 함수, I/O 최소화."""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from typing import Optional

_DEFAULT_POSITION: dict = {
    "state": "WATCH",
    "days_in_state": 0,
    "entered_at": None,
    "entry_price": None,
    "stop_level": None,
    "signal_type": None,
    "recent_high": 0.0,
    "trailing_stop_line": None,
    "position_status": None,
    "horizontal_support": None,
}


def load_positions(path: str) -> dict:
    """positions.json 로드. 파일 없으면 빈 구조 반환 (첫 실행 대응)."""
    p = Path(path)
    if not p.exists():
        return {"as_of": None, "positions": {}}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_positions(positions: dict, path: str) -> None:
    """positions dict를 JSON으로 저장. 디렉토리 없으면 자동 생성."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=2, default=str)


def get_position(positions: dict, ticker: str) -> dict:
    """ticker의 저장된 상태 반환. 없으면 기본 WATCH 상태."""
    return dict(positions.get("positions", {}).get(ticker, _DEFAULT_POSITION))


def update_position(
    positions: dict,
    ticker: str,
    state: str,
    days_in_state: int,
    entered_at: Optional[str],
    entry_price: Optional[float],
    stop_level: Optional[float],
    signal_type: Optional[str],
    recent_high: float = 0.0,
    trailing_stop_line: Optional[float] = None,
    position_status: Optional[str] = None,
    horizontal_support: Optional[float] = None,
) -> dict:
    """불변 패턴 — 새 dict 반환. 원본 positions 변경 없음."""
    updated_positions = dict(positions.get("positions", {}))
    updated_positions[ticker] = {
        "state": state,
        "days_in_state": days_in_state,
        "entered_at": entered_at,
        "entry_price": entry_price,
        "stop_level": stop_level,
        "signal_type": signal_type,
        "recent_high": recent_high,
        "trailing_stop_line": trailing_stop_line,
        "position_status": position_status,
        "horizontal_support": horizontal_support,
    }
    return {
        "as_of": str(date.today()),
        "positions": updated_positions,
    }
