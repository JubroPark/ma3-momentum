"""MA50 스크리너 — 매수·매도 시그널 + 상태머신 + 스코어."""
from __future__ import annotations
from typing import Optional
import pandas as pd
from engines.ma50_indicators import calc_highN

MA50_DEFAULT_PARAMS: dict = {
    "breakout_high_lookback": 20,
    "lookback_below":         7,
    "vol_mult":               1.5,
    "vol_cap":                3.0,
    "overshoot_max":          0.07,
    "proximity_pct":          0.03,
    "break_tol":              0.01,
    "sell_tol":               0.01,
    "consec_below_sell":      2,
    "max_hold_watch_days":    5,
    "rs_early_th":            80.0,
    "slope_cap":              0.05,
    "score_weights":          (0.25, 0.25, 0.25, 0.25),
    "regime_mode":            "strict",
    "early_trend_enabled":    False,
    "bounce_lookback":        5,
}


def check_common_gate(
    vol_ratio: float,
    gap50: float,
    regime: str,
    params: dict,
) -> bool:
    """레짐 + gap50 ≤ overshoot_max + vol_ratio ≥ vol_mult."""
    if regime == "RISK_OFF" and params.get("regime_mode", "strict") == "strict":
        return False
    if gap50 > params["overshoot_max"]:
        return False
    if vol_ratio < params["vol_mult"]:
        return False
    return True


def check_strong_breakout(
    close: pd.Series,
    ma50: pd.Series,
    high: pd.Series,
    params: dict,
) -> bool:
    """
    선행: close[-1] ≤ MA50[-1] AND 최근 lookback_below일 중 60%+ close<MA50
    돌파: close[0] > MA50[0] AND close[0] > highN
    """
    if len(close) < 2 or len(ma50.dropna()) < 2:
        return False

    today_close     = float(close.iloc[-1])
    today_ma50      = float(ma50.dropna().iloc[-1])
    yesterday_close = float(close.iloc[-2])
    yesterday_ma50  = float(ma50.dropna().iloc[-2])

    high_n = calc_highN(high, params["breakout_high_lookback"])

    if not (today_close > today_ma50 and today_close > high_n):
        return False
    if not (yesterday_close <= yesterday_ma50):
        return False

    lb = params["lookback_below"]
    recent_c = close.iloc[-(lb + 1):-1]
    recent_m = ma50.iloc[-(lb + 1):-1]
    if len(recent_c) == 0:
        return False
    below_ratio = (recent_c.values < recent_m.values).mean()
    return bool(below_ratio >= 0.60)


def check_early_trend(
    close: pd.Series,
    ma50: pd.Series,
    slope_pct: float,
    rs_pct: float,
    params: dict,
) -> bool:
    """
    돌파: close[0] > MA50[0] AND close[-1] ≤ MA50[-1]
    안전장치: RS_pct ≥ rs_early_th AND slope_pct > 0
    """
    if len(close) < 2 or len(ma50.dropna()) < 2:
        return False
    today_close     = float(close.iloc[-1])
    today_ma50      = float(ma50.dropna().iloc[-1])
    yesterday_close = float(close.iloc[-2])
    yesterday_ma50  = float(ma50.dropna().iloc[-2])

    if not (today_close > today_ma50 and yesterday_close <= yesterday_ma50):
        return False
    if rs_pct < params["rs_early_th"]:
        return False
    if slope_pct <= 0:
        return False
    return True


def check_bounce(
    close: pd.Series,
    low: pd.Series,
    ma50: pd.Series,
    ma200: pd.Series,
    slope_pct: float,
    params: dict,
) -> bool:
    """
    추세: MA50>MA200 AND slope>0 AND 최근 20일 close>MA50 다수(>50%)
    근접: min(low[0..k]) ≤ MA50*(1+proximity_pct)
    지지: min(close[0..k]) ≥ MA50*(1-break_tol)
    반등: close[0]>close[-1] AND close[0]>MA50
    """
    ma50_clean  = ma50.dropna()
    ma200_clean = ma200.dropna()
    if ma50_clean.empty or len(close) < 2:
        return False

    today_ma50  = float(ma50_clean.iloc[-1])
    today_ma200 = float(ma200_clean.iloc[-1]) if not ma200_clean.empty else 0.0
    today_close = float(close.iloc[-1])
    yesterday_close = float(close.iloc[-2])

    if slope_pct <= 0:
        return False
    if today_ma200 > 0 and not (today_ma50 > today_ma200):
        return False

    recent20_c = close.iloc[-20:]
    recent20_m = ma50.iloc[-20:]
    if len(recent20_c) < 10:
        return False
    above_ratio = (recent20_c.values > recent20_m.values).mean()
    if above_ratio < 0.5:
        return False

    k = params.get("bounce_lookback", 5)
    recent_low   = low.iloc[-(k + 1):]
    recent_close = close.iloc[-(k + 1):]
    min_low   = float(recent_low.min())
    min_close = float(recent_close.min())
    if min_low > today_ma50 * (1 + params["proximity_pct"]):
        return False
    if min_close < today_ma50 * (1 - params["break_tol"]):
        return False

    return today_close > yesterday_close and today_close > today_ma50


def get_buy_signal(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    ma50: pd.Series,
    ma200: pd.Series,
    vol_ratio: float,
    gap50: float,
    slope_pct: float,
    rs_pct: float,
    regime: str,
    params: dict,
) -> Optional[str]:
    """
    공통 게이트 통과 후 Track B → A → Bounce 순으로 체크.
    Returns: "STRONG_BREAKOUT" | "EARLY_TREND" | "BOUNCE" | None
    """
    if not check_common_gate(vol_ratio, gap50, regime, params):
        return None
    if check_strong_breakout(close, ma50, high, params):
        return "STRONG_BREAKOUT"
    if params.get("early_trend_enabled", False):
        if check_early_trend(close, ma50, slope_pct, rs_pct, params):
            return "EARLY_TREND"
    if check_bounce(close, low, ma50, ma200, slope_pct, params):
        return "BOUNCE"
    return None


# ── 매도 시그널 ────────────────────────────────────────────────


def check_breakdown(
    close: pd.Series,
    ma50: pd.Series,
    params: dict,
) -> bool:
    """
    hard: close[0] < MA50*(1-sell_tol)
    soft: close[0]<MA50 AND close[-1]<MA50
    """
    if len(close) < 2 or len(ma50) < 2:
        return False
    today_close     = float(close.iloc[-1])
    today_ma50      = float(ma50.iloc[-1])
    yesterday_close = float(close.iloc[-2])
    yesterday_ma50  = float(ma50.iloc[-2])
    sell_tol = params["sell_tol"]
    hard = today_close < today_ma50 * (1 - sell_tol)
    soft = today_close < today_ma50 and yesterday_close < yesterday_ma50
    return bool(hard or soft)


def get_sell_signal(
    state: str,
    close: pd.Series,
    ma50: pd.Series,
    ma200: pd.Series,
    rs_pct: float,
    days_in_state: int,
    regime: str,
    params: dict,
) -> Optional[str]:
    """
    우선순위순 매도 판단. Returns "SELL" | "HOLD_WATCH" | None
    1. close >= MA50 → None (OK)
    2. 연속 consec_below_sell일 → SELL
    3. SELL_WATCH + days > max_hold_watch_days → SELL
    4. breakdown AND close < MA200 → SELL
    5. breakdown AND close > MA200 AND RS > 50 → HOLD_WATCH
    6. breakdown (그 외) → SELL
    """
    today_close = float(close.iloc[-1])
    today_ma50  = float(ma50.iloc[-1])
    today_ma200 = float(ma200.iloc[-1])

    consec = params["consec_below_sell"]
    max_watch = params["max_hold_watch_days"]
    if regime == "RISK_OFF":
        consec = 1
        max_watch = 3

    # 우선순위 1
    if today_close >= today_ma50:
        return None

    # 우선순위 2
    if len(close) >= consec and len(ma50) >= consec:
        recent_c = close.iloc[-consec:]
        recent_m = ma50.iloc[-consec:]
        if bool((recent_c.values < recent_m.values).all()):
            return "SELL"

    # 우선순위 3
    if state == "SELL_WATCH" and days_in_state > max_watch:
        return "SELL"

    bd = check_breakdown(close, ma50, params)
    if bd:
        if today_close < today_ma200:
            return "SELL"
        if today_close > today_ma200 and rs_pct > 50:
            return "HOLD_WATCH"
        return "SELL"

    return None


# ── 상태머신 전이 ─────────────────────────────────────────────


def transition_state(
    current_state: str,
    buy_signal: Optional[str],
    sell_signal: Optional[str],
) -> str:
    """
    WATCH → BUY → HOLDING → SELL_WATCH → SELL → WATCH
    """
    if current_state == "WATCH":
        return "BUY" if buy_signal is not None else "WATCH"
    if current_state == "BUY":
        return "HOLDING"
    if current_state == "HOLDING":
        if sell_signal == "SELL":
            return "SELL"
        if sell_signal == "HOLD_WATCH":
            return "SELL_WATCH"
        return "HOLDING"
    if current_state == "SELL_WATCH":
        if sell_signal == "SELL":
            return "SELL"
        if sell_signal is None:  # 회복
            return "HOLDING"
        return "SELL_WATCH"
    if current_state == "SELL":
        return "WATCH"
    return current_state


# ── 스코어 ────────────────────────────────────────────────────


def calc_score(
    vol_ratio: float,
    gap50: float,
    rs_pct: float,
    slope_pct: float,
    ma50_last: float,
    ma200_last: float,
    params: dict,
) -> float:
    """0~100 점수. 가중합 공식."""
    w1, w2, w3, w4 = params.get("score_weights", (0.25, 0.25, 0.25, 0.25))
    vol_cap   = params.get("vol_cap", 3.0)
    overshoot = params.get("overshoot_max", 0.07)
    slope_cap = params.get("slope_cap", 0.05)

    vol_score      = min(vol_ratio / vol_cap, 1.0) if vol_cap > 0 else 0.0
    breakout_score = min(gap50 / overshoot, 1.0) if overshoot > 0 else 0.0
    rs_score       = rs_pct / 100.0
    trend_score    = (
        0.5 * min(slope_pct / slope_cap, 1.0) if slope_cap > 0 else 0.0
    ) + 0.5 * (1.0 if ma50_last > ma200_last else 0.0)

    raw = 100.0 * (w1 * vol_score + w2 * breakout_score + w3 * rs_score + w4 * trend_score)
    return round(max(0.0, min(100.0, raw)), 1)
