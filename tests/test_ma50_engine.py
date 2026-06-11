import pytest
from datetime import date


def _sample_metrics():
    return {
        "close": 201.3, "ma50": 195.0, "ma200": 180.0,
        "gap50": 0.032, "gap200": 0.083,
        "vol_ratio": 2.1, "rs_pct": 78.0, "rs_sector_pct": 65.0,
        "ma50_slope_pct": 0.018, "high_n": 199.5, "atr14": 3.2, "sector_etf": "XLK",
    }


def test_build_signal_item_structure():
    from engines.ma50_engine import build_signal_item
    item = build_signal_item(
        ticker="AAPL",
        signal_type="STRONG_BREAKOUT",
        state="BUY",
        score=82.5,
        trigger_reason="MA50 상향 돌파 + 거래량 급증",
        metrics=_sample_metrics(),
    )
    for key in ("ticker", "signal_type", "state", "score", "trigger_reason", "metrics"):
        assert key in item
    assert item["ticker"] == "AAPL"
    assert item["signal_type"] == "STRONG_BREAKOUT"
    assert item["score"] == 82.5


def test_build_signals_json_structure():
    from engines.ma50_engine import build_signals_json, build_signal_item
    item = build_signal_item("NVDA", "BOUNCE", "BUY", 75.0, "반등", _sample_metrics())
    result = build_signals_json(
        as_of=date(2026, 6, 11),
        regime="RISK_ON",
        items=[item],
    )
    assert result["as_of"] == "2026-06-11"
    assert result["regime"] == "RISK_ON"
    assert len(result["items"]) == 1
    assert result["items"][0]["ticker"] == "NVDA"


def test_build_signals_json_empty_items():
    from engines.ma50_engine import build_signals_json
    result = build_signals_json(date(2026, 6, 11), "RISK_OFF", [])
    assert result["items"] == []
    assert result["regime"] == "RISK_OFF"


def test_build_signals_json_metrics_keys():
    from engines.ma50_engine import build_signals_json, build_signal_item
    item = build_signal_item("MSFT", "SELL", "SELL", 0.0, "breakdown", _sample_metrics())
    result = build_signals_json(date(2026, 6, 11), "RISK_ON", [item])
    m = result["items"][0]["metrics"]
    for key in ("close", "ma50", "ma200", "gap50", "gap200",
                "vol_ratio", "rs_pct", "rs_sector_pct",
                "ma50_slope_pct", "high_n", "atr14", "sector_etf"):
        assert key in m
