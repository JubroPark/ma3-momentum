import pytest
import pandas as pd
import numpy as np


def make_ohlcv(
    closes: list,
    highs: list = None,
    lows: list = None,
    volumes: list = None,
    start: str = "2025-01-02",
) -> pd.DataFrame:
    n = len(closes)
    dates = pd.bdate_range(start, periods=n)
    return pd.DataFrame({
        "Close":  closes,
        "High":   highs   or [c * 1.01 for c in closes],
        "Low":    lows    or [c * 0.99 for c in closes],
        "Volume": volumes or [1_000_000.0] * n,
    }, index=dates)


def test_calc_slope_pct_uptrend():
    from engines.ma50_indicators import calc_slope_pct
    ma = pd.Series(list(range(100, 111)))
    assert calc_slope_pct(ma) == pytest.approx(0.10, rel=0.001)


def test_calc_slope_pct_flat():
    from engines.ma50_indicators import calc_slope_pct
    ma = pd.Series([100.0] * 11)
    assert calc_slope_pct(ma) == pytest.approx(0.0, abs=1e-6)


def test_calc_slope_pct_insufficient_data_returns_zero():
    from engines.ma50_indicators import calc_slope_pct
    ma = pd.Series([100.0] * 5)
    assert calc_slope_pct(ma) == 0.0


def test_calc_gap_above():
    from engines.ma50_indicators import calc_gap
    assert calc_gap(105.0, 100.0) == pytest.approx(0.05)


def test_calc_gap_below():
    from engines.ma50_indicators import calc_gap
    assert calc_gap(95.0, 100.0) == pytest.approx(-0.05)


def test_calc_gap_zero_ma_returns_zero():
    from engines.ma50_indicators import calc_gap
    assert calc_gap(100.0, 0.0) == 0.0


def test_calc_highN():
    from engines.ma50_indicators import calc_highN
    high = pd.Series([100.0, 102.0, 103.0, 98.0, 105.0, 101.0, 99.0, 104.0])
    assert calc_highN(high, lookback=5) == pytest.approx(105.0)


def test_calc_atr14_constant_range():
    from engines.ma50_indicators import calc_atr14
    n = 20
    closes = [100.0] * n
    highs  = [101.0] * n
    lows   = [99.0]  * n
    df = make_ohlcv(closes, highs, lows)
    result = calc_atr14(df["High"], df["Low"], df["Close"])
    assert result == pytest.approx(2.0, abs=0.1)


def test_calc_rs_raw_outperformer():
    from engines.ma50_indicators import calc_rs_raw
    n = 150
    stock = pd.Series([100.0 + i * 0.5 for i in range(n)])
    spy   = pd.Series([100.0 + i * 0.1 for i in range(n)])
    assert calc_rs_raw(stock, spy) > 0


def test_calc_rs_raw_underperformer():
    from engines.ma50_indicators import calc_rs_raw
    n = 150
    stock = pd.Series([100.0 - i * 0.3 for i in range(n)])
    spy   = pd.Series([100.0 + i * 0.1 for i in range(n)])
    assert calc_rs_raw(stock, spy) < 0


def test_calc_rs_pct_top():
    from engines.ma50_indicators import calc_rs_pct
    universe = {"A": 10.0, "B": 5.0, "C": 8.0, "D": 2.0, "E": 6.0}
    assert calc_rs_pct("A", universe) == pytest.approx(100.0)


def test_calc_rs_pct_bottom():
    from engines.ma50_indicators import calc_rs_pct
    universe = {"A": 10.0, "B": 5.0, "C": 8.0, "D": 2.0, "E": 6.0}
    assert calc_rs_pct("D", universe) == pytest.approx(20.0)


def test_calc_regime_risk_on():
    from engines.ma50_indicators import calc_regime
    closes = [100.0 + i * 0.2 for i in range(250)]
    assert calc_regime(pd.Series(closes)) == "RISK_ON"


def test_calc_regime_risk_off():
    from engines.ma50_indicators import calc_regime
    closes = [100.0 + i * 0.5 for i in range(200)] + [200.0 - i * 2.0 for i in range(50)]
    assert calc_regime(pd.Series(closes)) == "RISK_OFF"


def test_build_metrics_keys():
    from engines.ma50_indicators import build_metrics
    m = build_metrics(
        close_last=105.0, ma50_last=100.0, ma200_last=95.0,
        vol_ratio=2.0, rs_pct=75.0, rs_sector_pct=60.0,
        slope_pct=0.02, high_n=104.5, atr14=1.5, sector_etf="XLK",
    )
    for key in ("close", "ma50", "ma200", "gap50", "gap200",
                "vol_ratio", "rs_pct", "rs_sector_pct",
                "ma50_slope_pct", "high_n", "atr14", "sector_etf"):
        assert key in m, f"Missing key: {key}"
    assert m["gap50"] == pytest.approx(0.05)
    assert m["gap200"] == pytest.approx((100-95)/95, rel=0.01)
