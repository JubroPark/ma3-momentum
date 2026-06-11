import pytest
import pandas as pd


# ── calc_stop_level ────────────────────────────────────────────

def test_stop_level_ma50_dominates():
    from engines.backtest_ma50 import calc_stop_level
    # atr_stop = 100 - 5*2 = 90
    # ma50_stop = 95 * 0.99 = 94.05
    # max(90, 94.05) = 94.05
    result = calc_stop_level(entry_price=100.0, ma50_val=95.0, atr14=5.0, atr_mult=2.0)
    assert result == pytest.approx(94.05)


def test_stop_level_atr_dominates():
    from engines.backtest_ma50 import calc_stop_level
    # atr_stop = 100 - 1*2 = 98
    # ma50_stop = 95 * 0.99 = 94.05
    # max(98, 94.05) = 98
    result = calc_stop_level(entry_price=100.0, ma50_val=95.0, atr14=1.0, atr_mult=2.0)
    assert result == pytest.approx(98.0)


def test_stop_level_never_above_entry():
    from engines.backtest_ma50 import calc_stop_level
    result = calc_stop_level(entry_price=100.0, ma50_val=98.0, atr14=2.0, atr_mult=2.0)
    assert result < 100.0


# ── calc_position_size ─────────────────────────────────────────

def test_position_size_basic():
    from engines.backtest_ma50 import calc_position_size
    # dollar_risk=10000, risk_per_share=10 → shares=1000
    result = calc_position_size(100_000.0, 100.0, 90.0, 0.10)
    assert result == pytest.approx(1000.0)


def test_position_size_zero_when_stop_at_or_above_entry():
    from engines.backtest_ma50 import calc_position_size
    assert calc_position_size(100_000.0, 100.0, 100.0, 0.10) == 0.0
    assert calc_position_size(100_000.0, 100.0, 105.0, 0.10) == 0.0


def test_position_size_zero_when_entry_zero():
    from engines.backtest_ma50 import calc_position_size
    assert calc_position_size(100_000.0, 0.0, -10.0, 0.10) == 0.0


def test_position_size_proportional_to_risk():
    from engines.backtest_ma50 import calc_position_size
    full = calc_position_size(100_000.0, 100.0, 90.0, 0.10)
    half = calc_position_size(100_000.0, 100.0, 90.0, 0.05)
    assert half == pytest.approx(full / 2)


# ── calc_performance ───────────────────────────────────────────

def test_calc_performance_empty_trades():
    from engines.backtest_ma50 import calc_performance
    p = calc_performance([], 100_000.0, 1.0)
    assert p["num_trades"] == 0
    assert p["total_return_pct"] == 0.0
    assert p["win_rate_pct"] == 0.0


def test_calc_performance_single_win():
    from engines.backtest_ma50 import calc_performance
    # pnl = (110-100)*100 = 1000, return = 1000/100000 = 1%
    trades = [{"entry_price": 100.0, "exit_price": 110.0, "shares": 100.0, "hold_days": 20}]
    p = calc_performance(trades, 100_000.0, 1.0)
    assert p["num_trades"] == 1
    assert p["total_return_pct"] == pytest.approx(1.0)
    assert p["win_rate_pct"] == pytest.approx(100.0)
    assert p["avg_hold_days"] == pytest.approx(20.0)


def test_calc_performance_mix_win_loss():
    from engines.backtest_ma50 import calc_performance
    trades = [
        {"entry_price": 100.0, "exit_price": 110.0, "shares": 100.0, "hold_days": 10},
        {"entry_price": 100.0, "exit_price":  90.0, "shares": 100.0, "hold_days": 5},
    ]
    p = calc_performance(trades, 100_000.0, 1.0)
    assert p["num_trades"] == 2
    assert p["total_return_pct"] == pytest.approx(0.0)
    assert p["win_rate_pct"] == pytest.approx(50.0)


def test_calc_performance_max_drawdown_negative():
    from engines.backtest_ma50 import calc_performance
    trades = [
        {"entry_price": 100.0, "exit_price": 200.0, "shares": 100.0, "hold_days": 30},
        {"entry_price": 100.0, "exit_price":  50.0, "shares": 100.0, "hold_days": 10},
    ]
    p = calc_performance(trades, 100_000.0, 1.0)
    assert p["max_drawdown_pct"] < 0


def test_calc_performance_returns_all_keys():
    from engines.backtest_ma50 import calc_performance
    trades = [{"entry_price": 100.0, "exit_price": 105.0, "shares": 10.0, "hold_days": 5}]
    p = calc_performance(trades, 100_000.0, 0.5)
    for key in ("total_return_pct", "cagr_pct", "max_drawdown_pct",
                "sharpe", "win_rate_pct", "num_trades", "avg_hold_days"):
        assert key in p, f"Missing key: {key}"


# ── backtest_ticker ────────────────────────────────────────────

def _make_data(n: int = 300, trend: float = 0.15, seed: int = 42):
    """합성 OHLCV + SPY 데이터 생성."""
    import numpy as np
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-03", periods=n)
    prices = [100.0]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + trend / 252 + rng.normal(0, 0.012)))
    close  = pd.Series(prices, index=dates)
    open_  = close.shift(1).bfill()
    high   = close * 1.006
    low    = close * 0.994
    volume = pd.Series(
        [1_500_000.0 if i % 7 != 0 else 3_000_000.0 for i in range(n)],
        index=dates,
    )
    spy = pd.Series(
        [p * (0.92 + rng.normal(0, 0.01)) for p in prices],
        index=dates,
    )
    return close, open_, high, low, volume, spy


def test_backtest_ticker_returns_required_keys():
    from engines.backtest_ma50 import backtest_ticker
    from engines.ma50_signals import MA50_DEFAULT_PARAMS
    close, open_, high, low, volume, spy = _make_data()
    result = backtest_ticker(
        close=close, open_=open_, high=high, low=low, volume=volume,
        spy_close=spy, ticker="TEST",
        params=dict(MA50_DEFAULT_PARAMS),
    )
    assert "ticker" in result
    assert "trades" in result
    assert "performance" in result
    assert result["ticker"] == "TEST"
    assert isinstance(result["trades"], list)


def test_backtest_ticker_no_lookahead():
    """entry_date < exit_date for every trade."""
    from engines.backtest_ma50 import backtest_ticker
    from engines.ma50_signals import MA50_DEFAULT_PARAMS
    close, open_, high, low, volume, spy = _make_data(n=300)
    result = backtest_ticker(
        close=close, open_=open_, high=high, low=low, volume=volume,
        spy_close=spy, ticker="TEST",
        params=dict(MA50_DEFAULT_PARAMS),
    )
    for trade in result["trades"]:
        assert trade["entry_date"] < trade["exit_date"], (
            f"look-ahead: entry={trade['entry_date']} >= exit={trade['exit_date']}"
        )


def test_backtest_ticker_pnl_matches_prices():
    """pnl = (exit_price - entry_price) * shares for every trade."""
    from engines.backtest_ma50 import backtest_ticker
    from engines.ma50_signals import MA50_DEFAULT_PARAMS
    close, open_, high, low, volume, spy = _make_data(n=300)
    result = backtest_ticker(
        close=close, open_=open_, high=high, low=low, volume=volume,
        spy_close=spy, ticker="TEST",
        params=dict(MA50_DEFAULT_PARAMS),
    )
    for trade in result["trades"]:
        expected = (trade["exit_price"] - trade["entry_price"]) * trade["shares"]
        assert abs(trade["pnl"] - expected) < 0.02, (
            f"pnl mismatch: stored={trade['pnl']:.2f} expected={expected:.2f}"
        )


def test_backtest_ticker_performance_consistent():
    """performance.num_trades == len(trades)."""
    from engines.backtest_ma50 import backtest_ticker
    from engines.ma50_signals import MA50_DEFAULT_PARAMS
    close, open_, high, low, volume, spy = _make_data(n=300)
    result = backtest_ticker(
        close=close, open_=open_, high=high, low=low, volume=volume,
        spy_close=spy, ticker="TEST",
        params=dict(MA50_DEFAULT_PARAMS),
    )
    assert result["performance"]["num_trades"] == len(result["trades"])


def test_backtest_ticker_short_data_returns_empty():
    """데이터 60일 미만 → trades=[], performance zeros."""
    from engines.backtest_ma50 import backtest_ticker
    from engines.ma50_signals import MA50_DEFAULT_PARAMS
    close, open_, high, low, volume, spy = _make_data(n=40)
    result = backtest_ticker(
        close=close, open_=open_, high=high, low=low, volume=volume,
        spy_close=spy, ticker="SHORT",
        params=dict(MA50_DEFAULT_PARAMS),
    )
    assert result["trades"] == []
