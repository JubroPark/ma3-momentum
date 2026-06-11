import pytest
import pandas as pd
import numpy as np
from datetime import date


def make_series(values: list, start: str = "2025-01-02") -> pd.Series:
    dates = pd.bdate_range(start, periods=len(values))
    return pd.Series(values, index=dates)


def _default_params():
    from engines.ma50_signals import MA50_DEFAULT_PARAMS
    return dict(MA50_DEFAULT_PARAMS)


# ── check_common_gate ────────────────────────────────────────


def test_common_gate_passes():
    from engines.ma50_signals import check_common_gate
    p = _default_params()
    assert check_common_gate(vol_ratio=2.0, gap50=0.03, regime="RISK_ON", params=p) is True


def test_common_gate_fails_risk_off_strict():
    from engines.ma50_signals import check_common_gate
    p = _default_params()
    p["regime_mode"] = "strict"
    assert check_common_gate(vol_ratio=2.0, gap50=0.03, regime="RISK_OFF", params=p) is False


def test_common_gate_fails_overshoot():
    from engines.ma50_signals import check_common_gate
    p = _default_params()
    # gap50=0.08 > overshoot_max=0.07
    assert check_common_gate(vol_ratio=2.0, gap50=0.08, regime="RISK_ON", params=p) is False


def test_common_gate_fails_low_volume():
    from engines.ma50_signals import check_common_gate
    p = _default_params()
    # vol_ratio=1.2 < vol_mult=1.5
    assert check_common_gate(vol_ratio=1.2, gap50=0.03, regime="RISK_ON", params=p) is False


# ── check_strong_breakout ─────────────────────────────────────


def test_strong_breakout_fires():
    from engines.ma50_signals import check_strong_breakout
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    # 55일 정상가(100) + 24일 하락(95) + 1일 돌파(102)
    closes = [100.0] * 55 + [95.0] * 24 + [102.0]
    highs  = [100.0] * 55 + [96.0] * 24 + [105.0]
    close = make_series(closes)
    high  = make_series(highs)
    ma50  = calc_ma(close, 50)
    result = check_strong_breakout(close, ma50, high, p)
    assert result is True


def test_strong_breakout_fails_if_yesterday_above_ma50():
    from engines.ma50_signals import check_strong_breakout
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    # 최근 2일 모두 MA50 위 → 선행 조건 미충족
    closes = [100.0] * 50 + [102.0, 104.0]
    close = make_series(closes)
    high  = make_series([c * 1.01 for c in closes])
    ma50  = calc_ma(close, 50)
    result = check_strong_breakout(close, ma50, high, p)
    assert result is False


# ── check_early_trend ─────────────────────────────────────────


def test_early_trend_fires():
    from engines.ma50_signals import check_early_trend
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [95.0] * 55 + [99.0, 101.0]
    close = make_series(closes)
    ma50  = calc_ma(close, 50)
    assert check_early_trend(close, ma50, slope_pct=0.01, rs_pct=85.0, params=p) is True


def test_early_trend_fails_low_rs():
    from engines.ma50_signals import check_early_trend
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [95.0] * 55 + [99.0, 101.0]
    close = make_series(closes)
    ma50  = calc_ma(close, 50)
    # rs_pct=70 < rs_early_th=80
    assert check_early_trend(close, ma50, slope_pct=0.01, rs_pct=70.0, params=p) is False


def test_early_trend_fails_negative_slope():
    from engines.ma50_signals import check_early_trend
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [95.0] * 55 + [99.0, 101.0]
    close = make_series(closes)
    ma50  = calc_ma(close, 50)
    assert check_early_trend(close, ma50, slope_pct=-0.01, rs_pct=85.0, params=p) is False


# ── check_bounce ─────────────────────────────────────────────


def test_bounce_fails_negative_slope():
    from engines.ma50_signals import check_bounce
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [100.0] * 75
    lows   = [99.0] * 75
    close  = make_series(closes)
    low    = make_series(lows)
    ma50   = calc_ma(close, 50)
    ma200  = calc_ma(close, 200)
    assert check_bounce(close, low, ma50, ma200, slope_pct=-0.01, params=p) is False


def test_bounce_returns_bool():
    from engines.ma50_signals import check_bounce
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    uptrend = [90.0 + i * 0.5 for i in range(70)]
    dip     = [124.0, 123.5, 124.0, 123.8, 125.0]
    closes  = uptrend + dip
    lows    = [c * 0.995 for c in uptrend] + [122.5, 122.0, 123.0, 122.8, 124.0]
    close   = make_series(closes)
    low     = make_series(lows)
    ma50    = calc_ma(close, 50)
    ma200   = calc_ma(close, 200)
    result  = check_bounce(close, low, ma50, ma200, slope_pct=0.01, params=p)
    assert isinstance(result, bool)
