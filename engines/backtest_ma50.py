"""MA50 백테스트 엔진 — 순수 함수, I/O 없음."""
from __future__ import annotations
import math
from typing import Optional

import pandas as pd


def calc_stop_level(
    entry_price: float,
    ma50_val: float,
    atr14: float,
    atr_mult: float = 2.0,
) -> float:
    """더 보수적(높은) stop: max(entry-ATR×mult, MA50×0.99)."""
    atr_stop  = entry_price - atr14 * atr_mult
    ma50_stop = ma50_val * 0.99
    return max(atr_stop, ma50_stop)


def calc_position_size(
    capital: float,
    entry_price: float,
    stop_level: float,
    risk_per_trade: float = 0.10,
) -> float:
    """fixed-fractional: shares = (capital × risk_per_trade) / (entry - stop)."""
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

    pnls = [(t["exit_price"] - t["entry_price"]) * t["shares"] for t in trades]
    total_pnl = sum(pnls)
    total_return_pct = total_pnl / initial_capital * 100.0

    if period_years > 0:
        cagr_pct = ((1 + total_return_pct / 100) ** (1.0 / period_years) - 1) * 100
    else:
        cagr_pct = 0.0

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
    RS_pct: 20일 수익률 vs SPY 비교 (>0→60, ≤0→40) — 단일 종목 근사.
    """
    from engines.ma50_indicators import calc_ma, calc_slope_pct, calc_gap, calc_atr14
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
    entry_date: Optional[pd.Timestamp] = None
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
                ep  = round(entry_price, 2)
                xp  = round(today_open, 2)
                sh  = round(shares, 4)
                trades.append({
                    "ticker":      ticker,
                    "entry_date":  str(entry_date.date()),
                    "exit_date":   str(dt.date()),
                    "entry_price": ep,
                    "exit_price":  xp,
                    "shares":      sh,
                    "pnl":         round((xp - ep) * sh, 2),
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
                    ep  = round(entry_price, 2)
                    xp  = round(exit_px, 2)
                    sh  = round(shares, 4)
                    trades.append({
                        "ticker":         ticker,
                        "entry_date":     str(entry_date.date()),
                        "exit_date":      str(dt.date()),
                        "entry_price":    ep,
                        "exit_price":     xp,
                        "shares":         sh,
                        "pnl":            round((xp - ep) * sh, 2),
                        "hold_days":      (dt - entry_date).days,
                        "stop_triggered": True,
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

        v20       = float(vol20.iloc[i]) if not pd.isna(vol20.iloc[i]) else 1.0
        vol_ratio = float(volume.iloc[i]) / v20 if v20 > 0 else 0.0
        gap50     = calc_gap(float(c_s.iloc[-1]), ma50_last)
        slope_pct = calc_slope_pct(m50)

        # 레짐
        spy_m200v = float(spy_ma200.iloc[i]) if not pd.isna(spy_ma200.iloc[i]) else 0.0
        regime    = "RISK_ON" if (spy_m200v > 0 and float(spy_c.iloc[i]) > spy_m200v) else "RISK_OFF"

        # RS_pct 근사
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
        last_dt = idx[-1]
        ep  = round(entry_price, 2)
        xp  = round(float(close.iloc[-1]), 2)
        sh  = round(shares, 4)
        trades.append({
            "ticker":        ticker,
            "entry_date":    str(entry_date.date()),
            "exit_date":     str(last_dt.date()),
            "entry_price":   ep,
            "exit_price":    xp,
            "shares":        sh,
            "pnl":           round((xp - ep) * sh, 2),
            "hold_days":     (last_dt - entry_date).days,
            "open_position": True,
        })

    period_years = (idx[-1] - idx[50]).days / 365.25 if len(idx) > 51 else 0.0
    perf = calc_performance(trades, initial_capital, period_years)
    return {"ticker": ticker, "trades": trades, "performance": perf}
