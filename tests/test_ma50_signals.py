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
    # MA50[-2]=100.0, yesterday=99<100 ✓, today=101>100 ✓
    closes = [100.0] * 50 + [99.0, 101.0]
    close = make_series(closes)
    ma50  = calc_ma(close, 50)
    assert check_early_trend(close, ma50, slope_pct=0.01, rs_pct=85.0, params=p) is True


def test_early_trend_fails_low_rs():
    from engines.ma50_signals import check_early_trend
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [100.0] * 50 + [99.0, 101.0]
    close = make_series(closes)
    ma50  = calc_ma(close, 50)
    # rs_pct=70 < rs_early_th=80
    assert check_early_trend(close, ma50, slope_pct=0.01, rs_pct=70.0, params=p) is False


def test_early_trend_fails_negative_slope():
    from engines.ma50_signals import check_early_trend
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [100.0] * 50 + [99.0, 101.0]
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


# ── check_breakdown ──────────────────────────────────────────


def test_breakdown_hard():
    from engines.ma50_signals import check_breakdown
    p = _default_params()
    # close < MA50*(1-0.01) = 100*0.99 = 99 → hard breakdown
    close = make_series([100.0] * 10 + [98.5])
    ma50  = make_series([100.0] * 11)
    assert check_breakdown(close, ma50, p) is True


def test_breakdown_soft_two_days_below():
    from engines.ma50_signals import check_breakdown
    p = _default_params()
    # 오늘(99.5)과 어제(99.8) 모두 MA50(100) 미만 → soft breakdown
    close = make_series([100.0] * 9 + [99.8, 99.5])
    ma50  = make_series([100.0] * 11)
    assert check_breakdown(close, ma50, p) is True


def test_no_breakdown():
    from engines.ma50_signals import check_breakdown
    p = _default_params()
    # 오늘(99.8)만 약간 아래, 어제(101) 위 → soft 미충족, hard도 미충족
    close = make_series([100.0] * 9 + [101.0, 99.8])
    ma50  = make_series([100.0] * 11)
    assert check_breakdown(close, ma50, p) is False


# ── get_sell_signal ───────────────────────────────────────────


def _make_sell_data(close_vals, ma50_vals, ma200_val=90.0):
    close = make_series(close_vals)
    ma50  = make_series(ma50_vals)
    ma200 = make_series([ma200_val] * len(close_vals))
    return close, ma50, ma200


def test_sell_priority1_close_above_ma50_returns_none():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 5 + [101.0],
        [100.0] * 6,
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=60.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result is None


def test_sell_priority2_consec_below():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["consec_below_sell"] = 2
    # 마지막 2일 모두 MA50 아래, hard breakdown 없음
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 8 + [99.5, 99.2],
        [100.0] * 10,
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=60.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result == "SELL"


def test_sell_priority3_hold_watch_timeout():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["max_hold_watch_days"] = 5
    p["consec_below_sell"] = 3
    # 오늘 MA50 아래지만 1일만 → consec 미충족
    # SELL_WATCH 상태에서 days_in_state=6 > 5 → SELL
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 9 + [99.8],
        [100.0] * 10,
    )
    result = get_sell_signal("SELL_WATCH", close, ma50, ma200, rs_pct=60.0,
                              days_in_state=6, regime="RISK_ON", params=p)
    assert result == "SELL"


def test_sell_priority4_breakdown_below_ma200():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["consec_below_sell"] = 5  # consec 조건 실질적으로 제거
    # soft breakdown (2일 연속 < MA50) + close < MA200 → SELL
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 8 + [99.0, 98.5],
        [100.0] * 10,
        ma200_val=110.0,  # MA200 > close → close < MA200
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=60.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result == "SELL"


def test_sell_priority5_breakdown_above_ma200_high_rs():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["consec_below_sell"] = 5
    # soft breakdown + close > MA200 + RS > 50 → HOLD_WATCH
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 8 + [99.0, 98.5],
        [100.0] * 10,
        ma200_val=90.0,  # close > MA200
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=70.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result == "HOLD_WATCH"


def test_sell_priority6_breakdown_low_rs_sell():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["consec_below_sell"] = 5
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 8 + [99.0, 98.5],
        [100.0] * 10,
        ma200_val=90.0,
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=40.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result == "SELL"


# ── transition_state ─────────────────────────────────────────


def test_transition_watch_to_buy():
    from engines.ma50_signals import transition_state
    assert transition_state("WATCH", "STRONG_BREAKOUT", None) == "BUY"


def test_transition_watch_stays_watch():
    from engines.ma50_signals import transition_state
    assert transition_state("WATCH", None, None) == "WATCH"


def test_transition_buy_to_holding():
    from engines.ma50_signals import transition_state
    assert transition_state("BUY", None, None) == "HOLDING"


def test_transition_holding_to_sell_watch():
    from engines.ma50_signals import transition_state
    assert transition_state("HOLDING", None, "HOLD_WATCH") == "SELL_WATCH"


def test_transition_holding_to_sell():
    from engines.ma50_signals import transition_state
    assert transition_state("HOLDING", None, "SELL") == "SELL"


def test_transition_sell_watch_recovery():
    from engines.ma50_signals import transition_state
    # close >= MA50 recovery → HOLDING
    assert transition_state("SELL_WATCH", None, None) == "HOLDING"


def test_transition_sell_to_watch():
    from engines.ma50_signals import transition_state
    assert transition_state("SELL", None, None) == "WATCH"


# ── calc_score ────────────────────────────────────────────────


def test_calc_score_range_0_100():
    from engines.ma50_signals import calc_score
    p = _default_params()
    s = calc_score(
        vol_ratio=2.0, gap50=0.04, rs_pct=80.0,
        slope_pct=0.03, ma50_last=100.0, ma200_last=95.0, params=p,
    )
    assert 0 <= s <= 100


def test_calc_score_higher_for_better_metrics():
    from engines.ma50_signals import calc_score
    p = _default_params()
    high = calc_score(vol_ratio=3.0, gap50=0.06, rs_pct=95.0,
                      slope_pct=0.05, ma50_last=100.0, ma200_last=95.0, params=p)
    low  = calc_score(vol_ratio=1.5, gap50=0.01, rs_pct=30.0,
                      slope_pct=0.01, ma50_last=100.0, ma200_last=95.0, params=p)
    assert high > low


def test_calc_score_sum_invariant():
    from engines.ma50_signals import calc_score
    p = _default_params()
    s = calc_score(vol_ratio=1.5, gap50=0.03, rs_pct=50.0,
                   slope_pct=0.025, ma50_last=100.0, ma200_last=100.0, params=p)
    assert 0 <= s <= 100
