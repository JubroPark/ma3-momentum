"""공통 시장환경 데이터 수집 — market.json 생성."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.ma50_indicators import calc_regime

_OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "market.json"


def _fetch_vix() -> float | None:
    try:
        df = yf.download("^VIX", period="5d", auto_adjust=True, progress=False)
        close = df["Close"].squeeze().dropna()
        return round(float(close.iloc[-1]), 2) if not close.empty else None
    except Exception:
        return None


def _fetch_regime() -> tuple[str, str]:
    """SPY 기준 regime. (regime, as_of_str) 반환."""
    df = yf.download("SPY", period="2y", auto_adjust=True, progress=False)
    close = df["Close"].squeeze().dropna()
    regime = calc_regime(close)
    as_of = str(close.index[-1].date())
    return regime, as_of


def _fetch_market_context() -> dict:
    """FRED 금리/QE 컨텍스트. FRED_API_KEY 없으면 None 필드로 graceful degradation."""
    key = os.getenv("FRED_API_KEY")
    if not key:
        return {"rate_env": None, "dff": None, "qe_active": None, "qe_state": None}
    try:
        from fredapi import Fred
        from engines.market_context import get_market_context
        ctx = get_market_context(Fred(api_key=key))
        return {
            "rate_env": ctx["rate_env"],
            "dff": ctx["dff"],
            "qe_active": ctx["qe_active"],
            "qe_state": ctx["qe_state"],
        }
    except Exception as e:
        print(f"FRED 데이터 수집 실패 (무시): {e}")
        return {"rate_env": None, "dff": None, "qe_active": None, "qe_state": None}


def run() -> dict:
    print("=" * 50)
    print("시장환경 데이터 수집")
    print("=" * 50)

    print("SPY·VIX 다운로드 중...")
    regime, as_of = _fetch_regime()
    vix = _fetch_vix()
    ctx = _fetch_market_context()

    result = {
        "as_of": as_of,
        "regime": regime,
        "vix": vix,
        "rate_env": ctx["rate_env"],
        "dff": ctx["dff"],
        "qe_active": ctx["qe_active"],
        "qe_state": ctx["qe_state"],
        "fear_greed": None,   # Phase 0 확정 후 추가
        "pmi": None,          # 대체 소스 탐색 후 추가
    }

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print(f"market.json 저장: {_OUTPUT_PATH}")
    print(f"레짐: {regime} | VIX: {vix} | 금리: {ctx.get('rate_env')} | QE: {ctx.get('qe_active')}")
    return result


if __name__ == "__main__":
    run()
