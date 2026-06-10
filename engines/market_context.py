"""금리환경 + QE 컨텍스트 — FRED 데이터 기반."""
import os
import pandas as pd
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()
_QE_THRESHOLD = 0.1  # %


def get_market_context(fred: "Fred | None" = None) -> dict:
    """
    금리환경(DFF)과 QE 상태(WALCL)를 하나의 dict로 반환.

    Returns:
        rate_env: "ZERO" | "NON_ZERO"
        dff: float
        qe_active: bool
        qe_state: "QE_ON" | "QE_OFF" | "AMBIGUOUS"
        slope_pct: float
        last_updated: str (YYYY-MM-DD)
    """
    if fred is None:
        key = os.getenv("FRED_API_KEY")
        if not key:
            raise EnvironmentError("FRED_API_KEY environment variable is not set")
        fred = Fred(api_key=key)

    rate = _get_rate_env(fred)
    qe = _get_qe_state(fred)

    return {
        "rate_env": rate["rate_env"],
        "dff": rate["dff"],
        "last_updated": rate["last_updated"],
        "qe_active": qe["qe_active"],
        "qe_state": qe["qe_state"],
        "slope_pct": qe["slope_pct"],
    }


def _get_rate_env(fred: "Fred") -> dict:
    """
    FRED DFF(연방기금금리 실효치)로 금리환경 판단.
    DFF ≤ 0.25% → ZERO / DFF > 0.25% → NON_ZERO
    """
    series = fred.get_series("DFF").dropna()
    if series.empty:
        raise ValueError("FRED DFF series returned no data")
    latest = float(series.iloc[-1])
    last_date = series.index[-1].strftime("%Y-%m-%d")

    rate_env = "ZERO" if latest <= 0.25 else "NON_ZERO"

    return {
        "rate_env": rate_env,
        "dff": round(latest, 2),
        "last_updated": last_date,
    }


def _get_qe_state(fred: "Fred") -> dict:
    """
    FRED WALCL(연준 총자산) 4주 이동평균 기울기로 QE 자동 감지.
    기울기 > +0.1% → QE_ON / 기울기 < -0.1% → QE_OFF / 그 사이 → AMBIGUOUS
    """
    series = fred.get_series("WALCL").dropna().tail(8)

    ma4 = series.rolling(4).mean().dropna()
    if len(ma4) < 2:
        return {
            "qe_active": False,
            "qe_state": "AMBIGUOUS",
            "slope_pct": 0.0,
        }

    # slope_pct: percent change from previous 4-week MA to current (weekly series, 8-point window)
    slope_pct = round(float((ma4.iloc[-1] / ma4.iloc[-2] - 1) * 100), 4)

    if slope_pct > _QE_THRESHOLD:
        return {"qe_active": True, "qe_state": "QE_ON", "slope_pct": slope_pct}
    elif slope_pct < -_QE_THRESHOLD:
        return {"qe_active": False, "qe_state": "QE_OFF", "slope_pct": slope_pct}
    else:
        return {"qe_active": False, "qe_state": "AMBIGUOUS", "slope_pct": slope_pct}
