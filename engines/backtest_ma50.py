"""MA50 백테스트 엔진 — 순수 함수, I/O 없음."""
from __future__ import annotations
import math


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
