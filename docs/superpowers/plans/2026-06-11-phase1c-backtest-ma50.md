# Phase 1C: MA50 백테스트 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MA50 스크리너 엔진의 과거 성과를 검증하는 단일-종목 백테스트 엔진을 구현하여 `outputs/backtest_results.json`을 산출한다.

**Architecture:** `engines/backtest_ma50.py`(순수 함수 — 포지션 사이징·성과 계산·날짜별 루프)가 Phase 1B의 `ma50_signals.py`를 재사용하며 I/O 없이 거래 내역을 반환한다. `scripts/run_backtest_ma50.py`가 데이터를 수집하고 JSON을 저장한다.

**Tech Stack:** Python 3.9+, pandas, yfinance, pytest

---

## 설계 제약 (모든 Task 공통 인식)

| 항목 | 결정 |
|---|---|
| 체결 기준 | 시그널 EOD 산출 → **익일 시가 체결** (look-ahead 방지) |
| 포지션 사이징 | fixed-fractional: `shares = (capital × risk_per_trade) / (entry − stop)` |
| stop_level | `max(entry − ATR14×atr_mult, MA50×0.99)` — 더 보수적(높은 쪽) |
| RS percentile | 단일-종목 루프에서 20일 수익률 vs SPY 비교로 60/40 근사 (Phase 2에서 유니버스 확장) |
| 생존편향 | Phase 1C에서 고정 워치리스트 사용; point-in-time 유니버스는 Phase 2 |
| 초기 자본 | 기본 100,000달러, 트레이드 간 capital 고정 (각 트레이드 독립 사이징) |
| 단위 | gap50·stop_tol 등 분수(0.01=1%), rs_pct 0~100 |

---

## 파일 맵

| 파일 | 역할 | 신규/기존 |
|---|---|---|
| `engines/backtest_ma50.py` | calc_stop_level·calc_position_size·calc_performance·backtest_ticker | 신규 |
| `scripts/run_backtest_ma50.py` | 데이터 수집 + 루프 + JSON 저장 | 신규 |
| `tests/test_backtest_ma50.py` | 단위 테스트 | 신규 |
| `outputs/backtest_results.json` | 산출물 | 신규 |

---

## Task 1: engines/backtest_ma50.py — 순수 함수 (사이징·성과)

**Files:**
- Create: `engines/backtest_ma50.py`
- Create: `tests/test_backtest_ma50.py`

- [ ] **Step 1: 테스트 작성 (RED)**

Create `/Users/jubro/Claude Project/ma3 momentum/tests/test_backtest_ma50.py`:

```python
import pytest
import pandas as pd


# ── calc_stop_level ────────────────────────────────────────────

def test_stop_level_ma50_dominates():
    """MA50 stop보다 ATR stop이 낮을 때 → MA50 stop 사용."""
    from engines.backtest_ma50 import calc_stop_level
    # atr_stop = 100 - 5*2 = 90
    # ma50_stop = 95 * 0.99 = 94.05
    # max(90, 94.05) = 94.05 → MA50 dominates
    result = calc_stop_level(entry_price=100.0, ma50_val=95.0, atr14=5.0, atr_mult=2.0)
    assert result == pytest.approx(94.05)


def test_stop_level_atr_dominates():
    """ATR stop이 MA50 stop보다 높을 때 → ATR stop 사용."""
    from engines.backtest_ma50 import calc_stop_level
    # atr_stop = 100 - 1*2 = 98
    # ma50_stop = 95 * 0.99 = 94.05
    # max(98, 94.05) = 98 → ATR dominates
    result = calc_stop_level(entry_price=100.0, ma50_val=95.0, atr14=1.0, atr_mult=2.0)
    assert result == pytest.approx(98.0)


def test_stop_level_never_above_entry():
    """stop_level은 항상 entry_price 미만이어야 한다 (정상 케이스)."""
    from engines.backtest_ma50 import calc_stop_level
    result = calc_stop_level(entry_price=100.0, ma50_val=98.0, atr14=2.0, atr_mult=2.0)
    assert result < 100.0


# ── calc_position_size ─────────────────────────────────────────

def test_position_size_basic():
    """capital=100000, entry=100, stop=90, risk=0.10 → shares=1000."""
    from engines.backtest_ma50 import calc_position_size
    # dollar_risk = 10000, risk_per_share = 10 → shares = 1000
    result = calc_position_size(100_000.0, 100.0, 90.0, 0.10)
    assert result == pytest.approx(1000.0)


def test_position_size_zero_when_stop_at_or_above_entry():
    """stop ≥ entry → 0 반환 (가드)."""
    from engines.backtest_ma50 import calc_position_size
    assert calc_position_size(100_000.0, 100.0, 100.0, 0.10) == 0.0
    assert calc_position_size(100_000.0, 100.0, 105.0, 0.10) == 0.0


def test_position_size_zero_when_entry_zero():
    from engines.backtest_ma50 import calc_position_size
    assert calc_position_size(100_000.0, 0.0, -10.0, 0.10) == 0.0


def test_position_size_proportional_to_risk():
    """risk_per_trade=0.05 → shares는 0.10의 절반."""
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
    # pnl = (110-100)*100 = 1000, total_return = 1000/100000 = 1%
    trades = [{"entry_price": 100.0, "exit_price": 110.0, "shares": 100.0, "hold_days": 20}]
    p = calc_performance(trades, 100_000.0, 1.0)
    assert p["num_trades"] == 1
    assert p["total_return_pct"] == pytest.approx(1.0)
    assert p["win_rate_pct"] == pytest.approx(100.0)
    assert p["avg_hold_days"] == pytest.approx(20.0)


def test_calc_performance_mix_win_loss():
    from engines.backtest_ma50 import calc_performance
    trades = [
        {"entry_price": 100.0, "exit_price": 110.0, "shares": 100.0, "hold_days": 10},  # +1000
        {"entry_price": 100.0, "exit_price":  90.0, "shares": 100.0, "hold_days": 5},   # -1000
    ]
    p = calc_performance(trades, 100_000.0, 1.0)
    assert p["num_trades"] == 2
    assert p["total_return_pct"] == pytest.approx(0.0)
    assert p["win_rate_pct"] == pytest.approx(50.0)


def test_calc_performance_max_drawdown():
    from engines.backtest_ma50 import calc_performance
    # 10000 gain then 5000 loss → max_dd = -5000/110000 ≈ -4.55%
    trades = [
        {"entry_price": 100.0, "exit_price": 200.0, "shares": 100.0, "hold_days": 30},  # +10000
        {"entry_price": 100.0, "exit_price":  50.0, "shares": 100.0, "hold_days": 10},  # -5000
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_backtest_ma50.py -v 2>&1 | head -10
```
Expected: `ImportError: cannot import name 'calc_stop_level'`

- [ ] **Step 3: 구현**

Create `/Users/jubro/Claude Project/ma3 momentum/engines/backtest_ma50.py`:

```python
"""MA50 백테스트 엔진 — 순수 함수, I/O 없음."""
from __future__ import annotations
from typing import Optional
import math
import pandas as pd


def calc_stop_level(
    entry_price: float,
    ma50_val: float,
    atr14: float,
    atr_mult: float = 2.0,
) -> float:
    """더 보수적(높은) stop 사용: max(entry-ATR×mult, MA50×0.99)."""
    atr_stop  = entry_price - atr14 * atr_mult
    ma50_stop = ma50_val * 0.99
    return max(atr_stop, ma50_stop)


def calc_position_size(
    capital: float,
    entry_price: float,
    stop_level: float,
    risk_per_trade: float = 0.10,
) -> float:
    """fixed-fractional 포지션 사이징. shares = dollar_risk / risk_per_share."""
    risk_per_share = entry_price - stop_level
    if risk_per_share <= 0 or entry_price <= 0:
        return 0.0
    return float(capital * risk_per_trade / risk_per_share)


def calc_performance(
    trades: list,
    initial_capital: float,
    period_years: float,
) -> dict:
    """trades: list of {entry_price, exit_price, shares, hold_days}."""
    if not trades:
        return {
            "total_return_pct": 0.0, "cagr_pct": 0.0,
            "max_drawdown_pct": 0.0, "sharpe": 0.0,
            "win_rate_pct": 0.0, "num_trades": 0, "avg_hold_days": 0.0,
        }

    pnls = [
        (t["exit_price"] - t["entry_price"]) * t["shares"]
        for t in trades
    ]
    total_pnl = sum(pnls)
    total_return_pct = total_pnl / initial_capital * 100.0

    if period_years > 0:
        cagr_pct = ((1 + total_return_pct / 100) ** (1.0 / period_years) - 1) * 100
    else:
        cagr_pct = 0.0

    # 최대 낙폭 (누적 equity curve 기준)
    equity = initial_capital
    peak   = initial_capital
    max_dd = 0.0
    for p in pnls:
        equity += p
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak * 100.0
        if dd < max_dd:
            max_dd = dd

    wins = [p for p in pnls if p > 0]
    win_rate_pct = len(wins) / len(pnls) * 100.0

    avg_hold = sum(t["hold_days"] for t in trades) / len(trades)

    # Sharpe (trade-level — per-trade return vs initial_capital)
    if len(pnls) > 1:
        rets = [p / initial_capital for p in pnls]
        mu   = sum(rets) / len(rets)
        var  = sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)
        std  = math.sqrt(var) if var > 0 else 0.0
        sharpe = (mu / std) * math.sqrt(252.0) if std > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct":         round(cagr_pct, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe":           round(sharpe, 2),
        "win_rate_pct":     round(win_rate_pct, 1),
        "num_trades":       len(trades),
        "avg_hold_days":    round(avg_hold, 1),
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_backtest_ma50.py -v
```
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add engines/backtest_ma50.py tests/test_backtest_ma50.py && git commit -m "feat: backtest_ma50 — stop_level·position_size·performance 순수 함수"
```

---

## Task 2: engines/backtest_ma50.py — backtest_ticker 루프

**Files:**
- Modify: `engines/backtest_ma50.py` (append `backtest_ticker`)
- Modify: `tests/test_backtest_ma50.py` (append tests)

- [ ] **Step 1: 테스트 추가 (RED)**

`tests/test_backtest_ma50.py` 끝에 추가:

```python
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
    """entry_date는 항상 exit_date보다 앞이어야 한다."""
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
    """각 거래의 pnl = (exit_price - entry_price) * shares."""
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
    """데이터 60일 미만 → 거래 없음."""
    from engines.backtest_ma50 import backtest_ticker
    from engines.ma50_signals import MA50_DEFAULT_PARAMS
    close, open_, high, low, volume, spy = _make_data(n=40)
    result = backtest_ticker(
        close=close, open_=open_, high=high, low=low, volume=volume,
        spy_close=spy, ticker="SHORT",
        params=dict(MA50_DEFAULT_PARAMS),
    )
    assert result["trades"] == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_backtest_ma50.py::test_backtest_ticker_returns_required_keys -v 2>&1 | head -5
```
Expected: `ImportError: cannot import name 'backtest_ticker'`

- [ ] **Step 3: backtest_ticker 구현 — engines/backtest_ma50.py에 추가**

`engines/backtest_ma50.py` 끝에 추가:

```python
def backtest_ticker(
    close: pd.Series,
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
    spy_close: pd.Series,
    ticker: str,
    params: dict,
    initial_capital: float = 100_000.0,
    risk_per_trade: float = 0.10,
    atr_mult: float = 2.0,
) -> dict:
    """
    날짜별 MA50 시그널 → 익일 시가 체결 백테스트.
    RS_pct: 20일 수익률 vs SPY 비교 (>0 → 60, ≤0 → 40) — 단일 종목 근사.
    """
    from engines.ma50_indicators import (
        calc_ma, calc_slope_pct, calc_gap, calc_atr14,
    )
    from engines.ma50_signals import get_buy_signal, get_sell_signal, transition_state

    # 공통 날짜 교집합
    idx = close.index.intersection(open_.index).intersection(spy_close.index)
    if len(idx) < 60:
        return {
            "ticker": ticker, "trades": [],
            "performance": calc_performance([], initial_capital, 0.0),
        }

    close  = close.reindex(idx)
    open_  = open_.reindex(idx)
    high   = high.reindex(idx)
    low    = low.reindex(idx)
    volume = volume.reindex(idx)
    spy_c  = spy_close.reindex(idx)

    # 룩어헤드 없는 롤링 지표 사전 계산
    ma50      = calc_ma(close, 50)
    ma200     = calc_ma(close, 200)
    vol20     = calc_ma(volume, 20)
    spy_ma200 = calc_ma(spy_c, 200)

    state         = "WATCH"
    days_in_state = 0
    entry_price   = 0.0
    entry_date    = None
    stop_level    = 0.0
    shares        = 0.0
    pending_order = ""
    trades: list  = []

    for i in range(50, len(idx)):
        dt         = idx[i]
        today_open = float(open_.iloc[i])

        # ── 전일 주문 체결 ──────────────────────────────────────
        if pending_order == "BUY" and state == "BUY":
            entry_price = today_open
            entry_date  = dt
            ma50_now    = float(ma50.iloc[i]) if not pd.isna(ma50.iloc[i]) else entry_price
            atr14_now   = calc_atr14(high.iloc[:i+1], low.iloc[:i+1], close.iloc[:i+1])
            stop_level  = calc_stop_level(entry_price, ma50_now, atr14_now, atr_mult)
            shares      = calc_position_size(initial_capital, entry_price, stop_level, risk_per_trade)
            state       = "HOLDING"
            days_in_state = 0
            pending_order = ""

        elif pending_order == "SELL" and state == "SELL":
            if entry_date is not None and shares > 0:
                trades.append({
                    "ticker":      ticker,
                    "entry_date":  str(entry_date.date()),
                    "exit_date":   str(dt.date()),
                    "entry_price": round(entry_price, 2),
                    "exit_price":  round(today_open, 2),
                    "shares":      round(shares, 4),
                    "pnl":         round((today_open - entry_price) * shares, 2),
                    "hold_days":   (dt - entry_date).days,
                })
            state = "WATCH"
            days_in_state = 0
            entry_date = None
            shares = 0.0
            pending_order = ""

        # ── 손절 체크 (일중 저가 기준) ──────────────────────────
        if state == "HOLDING" and shares > 0:
            if float(low.iloc[i]) <= stop_level:
                exit_px = stop_level
                if entry_date is not None:
                    trades.append({
                        "ticker":          ticker,
                        "entry_date":      str(entry_date.date()),
                        "exit_date":       str(dt.date()),
                        "entry_price":     round(entry_price, 2),
                        "exit_price":      round(exit_px, 2),
                        "shares":          round(shares, 4),
                        "pnl":             round((exit_px - entry_price) * shares, 2),
                        "hold_days":       (dt - entry_date).days,
                        "stop_triggered":  True,
                    })
                state = "WATCH"
                days_in_state = 0
                entry_date = None
                shares = 0.0
                continue

        # ── EOD 시그널 산출 ─────────────────────────────────────
        c_s  = close.iloc[:i+1]
        h_s  = high.iloc[:i+1]
        l_s  = low.iloc[:i+1]
        m50  = ma50.iloc[:i+1]
        m200 = ma200.iloc[:i+1]

        ma50_clean = m50.dropna()
        if ma50_clean.empty:
            days_in_state += 1
            continue

        ma50_last  = float(ma50_clean.iloc[-1])
        ma200_c    = m200.dropna()
        ma200_last = float(ma200_c.iloc[-1]) if not ma200_c.empty else 0.0

        v20        = float(vol20.iloc[i]) if not pd.isna(vol20.iloc[i]) else 1.0
        vol_ratio  = float(volume.iloc[i]) / v20 if v20 > 0 else 0.0
        gap50      = calc_gap(float(c_s.iloc[-1]), ma50_last)
        slope_pct  = calc_slope_pct(m50)

        # 레짐
        spy_m200v = float(spy_ma200.iloc[i]) if not pd.isna(spy_ma200.iloc[i]) else 0.0
        regime    = "RISK_ON" if (spy_m200v > 0 and float(spy_c.iloc[i]) > spy_m200v) else "RISK_OFF"

        # RS_pct 근사 (단일 종목 vs SPY 20일 수익률)
        if i >= 20:
            r20_s   = float(c_s.iloc[-1]) / float(c_s.iloc[-21]) - 1
            r20_spy = float(spy_c.iloc[i]) / float(spy_c.iloc[i-20]) - 1
            rs_pct_val = 60.0 if r20_s > r20_spy else 40.0
        else:
            rs_pct_val = 50.0

        buy_sig  = None
        sell_sig = None

        if state == "WATCH":
            buy_sig = get_buy_signal(
                c_s, h_s, l_s, m50, m200,
                vol_ratio, gap50, slope_pct, rs_pct_val, regime, params,
            )
        elif state in ("HOLDING", "SELL_WATCH"):
            sell_sig = get_sell_signal(
                state, c_s, m50, m200,
                rs_pct_val, days_in_state, regime, params,
            )

        new_state = transition_state(state, buy_sig, sell_sig)

        if new_state != state:
            days_in_state = 0
            if new_state == "BUY":
                pending_order = "BUY"
            elif new_state == "SELL":
                pending_order = "SELL"
        else:
            days_in_state += 1

        state = new_state

    # 미청산 포지션 → 마지막 종가로 강제 청산
    if state == "HOLDING" and entry_date is not None and shares > 0:
        last_px = float(close.iloc[-1])
        last_dt = idx[-1]
        trades.append({
            "ticker":         ticker,
            "entry_date":     str(entry_date.date()),
            "exit_date":      str(last_dt.date()),
            "entry_price":    round(entry_price, 2),
            "exit_price":     round(last_px, 2),
            "shares":         round(shares, 4),
            "pnl":            round((last_px - entry_price) * shares, 2),
            "hold_days":      (last_dt - entry_date).days,
            "open_position":  True,
        })

    period_years = (idx[-1] - idx[50]).days / 365.25 if len(idx) > 51 else 0.0
    perf = calc_performance(trades, initial_capital, period_years)
    return {"ticker": ticker, "trades": trades, "performance": perf}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_backtest_ma50.py -v && pytest tests/ -q 2>&1 | tail -3
```
Expected: 17 passed (test_backtest_ma50.py), full suite 130 passed

- [ ] **Step 5: Commit**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add engines/backtest_ma50.py tests/test_backtest_ma50.py && git commit -m "feat: backtest_ticker — MA50 익일시가 체결 백테스트 루프"
```

---

## Task 3: scripts/run_backtest_ma50.py — 실행 진입점

**Files:**
- Create: `scripts/run_backtest_ma50.py`

- [ ] **Step 1: 구현**

Create `/Users/jubro/Claude Project/ma3 momentum/scripts/run_backtest_ma50.py`:

```python
"""MA50 백테스트 실행 진입점."""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.backtest_ma50 import backtest_ticker
from engines.ma50_signals import MA50_DEFAULT_PARAMS

_OUTPUT = Path(__file__).parent.parent / "outputs" / "backtest_results.json"

_SECTOR_MAP: dict = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AVGO": "XLK",
    "AMZN": "XLY", "TSLA": "XLY",
    "GOOGL": "XLC", "META": "XLC",
    "JPM": "XLF",
    "LLY": "XLV",
    "XOM": "XLE",
    "COST": "XLP",
}

_DEFAULT_WATCHLIST = list(_SECTOR_MAP.keys())


def run(watchlist: list = None, period: str = "3y") -> dict:
    print("=" * 50)
    print("MA50 백테스트 실행")
    print("=" * 50)

    tickers = watchlist or _DEFAULT_WATCHLIST
    params  = dict(MA50_DEFAULT_PARAMS)

    print(f"SPY + {len(tickers)}종목 다운로드 중... (기간: {period})")
    all_tickers = ["SPY"] + [t for t in tickers if t != "SPY"]
    raw = yf.download(
        all_tickers, period=period, auto_adjust=True,
        progress=False, group_by="ticker",
    )

    def get_series(ticker, col):
        try:
            s = raw[ticker][col].squeeze().dropna()
            return s if len(s) > 60 else None
        except Exception:
            return None

    spy_close = get_series("SPY", "Close")
    if spy_close is None:
        raise RuntimeError("SPY 데이터 수집 실패")

    results = []
    for ticker in tickers:
        close_s  = get_series(ticker, "Close")
        open_s   = get_series(ticker, "Open")
        high_s   = get_series(ticker, "High")
        low_s    = get_series(ticker, "Low")
        volume_s = get_series(ticker, "Volume")

        if any(s is None for s in (close_s, open_s, high_s, low_s, volume_s)):
            print(f"  {ticker}: 데이터 부족 — 스킵")
            continue

        print(f"  {ticker}: {len(close_s)}일 백테스트 중...", end=" ")
        result = backtest_ticker(
            close=close_s, open_=open_s, high=high_s,
            low=low_s, volume=volume_s,
            spy_close=spy_close, ticker=ticker,
            params=params,
        )
        n = result["performance"]["num_trades"]
        ret = result["performance"]["total_return_pct"]
        print(f"{n}건 거래 | 총수익 {ret:+.1f}%")
        results.append(result)

    # 집계
    all_trades  = sum(r["performance"]["num_trades"] for r in results)
    win_rates   = [r["performance"]["win_rate_pct"] for r in results
                   if r["performance"]["num_trades"] > 0]
    avg_win_rate = round(sum(win_rates) / len(win_rates), 1) if win_rates else 0.0

    output = {
        "as_of":     str(date.today()),
        "period":    period,
        "params":    {k: v for k, v in params.items() if not isinstance(v, tuple)},
        "tickers":   results,
        "aggregate": {
            "num_tickers":    len(results),
            "total_trades":   all_trades,
            "avg_win_rate_pct": avg_win_rate,
        },
    }

    _OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str)
    )
    print(f"\n백테스트 결과 저장: {_OUTPUT}")
    print(f"총 {len(results)}종목 | 거래 {all_trades}건 | 평균 승률 {avg_win_rate:.1f}%")
    return output


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: 기존 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/ -q 2>&1 | tail -3
```
Expected: 전체 통과 (130 passed)

- [ ] **Step 3: 실제 실행**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && python scripts/run_backtest_ma50.py
```
Expected 출력:
```
==================================================
MA50 백테스트 실행
==================================================
SPY + 12종목 다운로드 중... (기간: 3y)
  AAPL: 756일 백테스트 중... N건 거래 | 총수익 +X.X%
  ...
백테스트 결과 저장: .../outputs/backtest_results.json
총 N종목 | 거래 N건 | 평균 승률 XX.X%
```

- [ ] **Step 4: 스키마 검증**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && python3 -c "
import json
from pathlib import Path
data = json.loads(Path('outputs/backtest_results.json').read_text())
assert 'as_of' in data
assert 'tickers' in data
assert isinstance(data['tickers'], list)
assert len(data['tickers']) > 0
t0 = data['tickers'][0]
assert 'ticker' in t0
assert 'trades' in t0
assert 'performance' in t0
p = t0['performance']
for k in ('total_return_pct','cagr_pct','max_drawdown_pct','sharpe','win_rate_pct','num_trades','avg_hold_days'):
    assert k in p, f'missing: {k}'
print('backtest_results.json 스키마 검증 통과')
print(f\"종목수: {len(data['tickers'])} | 총거래: {data['aggregate']['total_trades']}\")
"
```
Expected: `backtest_results.json 스키마 검증 통과`

- [ ] **Step 5: Commit**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add scripts/run_backtest_ma50.py outputs/backtest_results.json && git commit -m "feat: run_backtest_ma50 — MA50 백테스트 실행 진입점 + results.json 산출"
```

---

## 자기 검토 (Self-Review)

### 스펙 커버리지

| CLAUDE.md §10 요구사항 | 구현 Task |
|---|---|
| 체결 기준: 종가 시그널 → **익일 시가 체결** | Task 2 (pending_order 로직) |
| 포지션 사이징: fixed-fractional (risk_per_trade) | Task 1 calc_position_size |
| ATR 기반 stop | Task 1 calc_stop_level |
| 성과 지표: total return, CAGR, max drawdown, Sharpe, win rate | Task 1 calc_performance |
| look-ahead 방지 | Task 2 (close.iloc[:i+1] 슬라이싱) |
| 미청산 포지션 강제 청산 | Task 2 (루프 후 open_position 처리) |
| 손절 (stop_level) | Task 2 (intraday low 체크) |
| 실행 진입점 + JSON 산출 | Task 3 |

### 의도적 미포함

- **생존편향 제거 (point-in-time universe)**: Phase 2에서 고정 워치리스트 → 역대 S&P500 구성 종목으로 교체
- **RS_pct 유니버스 전체 계산**: Phase 1C에서 SPY 단일 비교 근사. Phase 2에서 S&P500+NDX 유니버스 사용
- **마삼 전략 백테스트**: Phase 1C는 MA50만 대상. 마삼 백테스트는 Phase 1C 완료 후 별도 계획
- **포트폴리오 레벨 capital 관리**: 각 종목 독립 사이징 (initial_capital 고정). 실제 포트폴리오 배분은 Phase 2
