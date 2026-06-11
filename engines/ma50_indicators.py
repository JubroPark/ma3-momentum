"""MA50 스크리너 — 지표 계산 순수 함수."""
from __future__ import annotations
import pandas as pd
import numpy as np


def calc_ma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def calc_slope_pct(ma: pd.Series) -> float:
    """(MA[-1] - MA[-11]) / MA[-11] — 분수 반환 (0.02 = 2%)."""
    valid = ma.dropna()
    if len(valid) < 11:
        return 0.0
    return float((valid.iloc[-1] - valid.iloc[-11]) / valid.iloc[-11])


def calc_gap(close_val: float, ma_val: float) -> float:
    """(close - MA) / MA — 분수 반환."""
    if ma_val == 0:
        return 0.0
    return float((close_val - ma_val) / ma_val)


def calc_highN(high: pd.Series, lookback: int) -> float:
    """max(high[1..lookback]) — 오늘 제외, 어제부터 lookback일 전까지."""
    window = high.iloc[-(lookback + 1):-1]
    return float(window.max()) if not window.empty else 0.0


def calc_atr14(high: pd.Series, low: pd.Series, close: pd.Series) -> float:
    """ATR14."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().dropna()
    return float(atr.iloc[-1]) if not atr.empty else 0.0


def _period_return(close: pd.Series, n: int) -> float:
    if len(close) <= n:
        return 0.0
    return float((close.iloc[-1] / close.iloc[-n - 1] - 1) * 100)


def calc_rs_raw(
    close_stock: pd.Series,
    close_spy: pd.Series,
    weights: tuple = (0.5, 0.3, 0.2),
) -> float:
    """RS_raw = 0.5*(r20s-r20m) + 0.3*(r60s-r60m) + 0.2*(r120s-r120m)."""
    w20, w60, w120 = weights
    return (
        w20  * (_period_return(close_stock, 20)  - _period_return(close_spy, 20))
        + w60  * (_period_return(close_stock, 60)  - _period_return(close_spy, 60))
        + w120 * (_period_return(close_stock, 120) - _period_return(close_spy, 120))
    )


def calc_rs_pct(ticker: str, rs_raw_map: dict) -> float:
    """RS 퍼센타일 (0~100). ticker의 RS_raw가 universe 내 몇 %ile인지."""
    values = list(rs_raw_map.values())
    if not values:
        return 50.0
    ticker_val = rs_raw_map.get(ticker, 0.0)
    rank = sum(1 for v in values if v <= ticker_val)
    return float(rank / len(values) * 100)


def calc_regime(close_spy: pd.Series) -> str:
    """SPY 종가 vs MA200 — RISK_ON | RISK_OFF."""
    ma200 = close_spy.rolling(200).mean().dropna()
    if ma200.empty:
        return "RISK_ON"
    return "RISK_ON" if float(close_spy.iloc[-1]) > float(ma200.iloc[-1]) else "RISK_OFF"


def build_metrics(
    close_last: float,
    ma50_last: float,
    ma200_last: float,
    vol_ratio: float,
    rs_pct: float,
    rs_sector_pct: float,
    slope_pct: float,
    high_n: float,
    atr14: float,
    sector_etf: str,
) -> dict:
    """signals.json metrics 필드용 직렬화 가능 dict."""
    return {
        "close":          round(close_last, 2),
        "ma50":           round(ma50_last, 2),
        "ma200":          round(ma200_last, 2),
        "gap50":          round(calc_gap(close_last, ma50_last), 4),
        "gap200":         round(calc_gap(ma50_last, ma200_last), 4),
        "vol_ratio":      round(vol_ratio, 2),
        "rs_pct":         round(rs_pct, 1),
        "rs_sector_pct":  round(rs_sector_pct, 1),
        "ma50_slope_pct": round(slope_pct, 4),
        "high_n":         round(high_n, 2),
        "atr14":          round(atr14, 2),
        "sector_etf":     sector_etf,
    }
