"""1등주 판정 — 대형주 상위 10개 시총 비교."""
from __future__ import annotations
import yfinance as yf

# 분기 1회 수동 갱신 (CLAUDE.md §5-3)
_DEFAULT_LARGE_CAP_LIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AVGO", "BRK-B", "JPM",
]


def get_leader_status(tickers: list[str] | None = None) -> dict:
    """
    시총 기준 1위·2위 판정 + 격차 계산.

    Returns dict with keys:
        rank1_ticker: str | None
        rank1_mcap: int | None
        rank2_ticker: str | None
        rank2_mcap: int | None
        gap_pct: float | None   — (rank1_mcap - rank2_mcap) / rank1_mcap * 100
        overtake_detected: bool — always False (rank1 is already the largest)
        gap_below_10pct: bool   — True if gap_pct < 10.0
    """
    if tickers is None:
        tickers = _DEFAULT_LARGE_CAP_LIST

    mcaps: dict[str, int] = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            mcap = info.get("marketCap") or 0
            if mcap > 0:
                mcaps[t] = mcap
        except Exception:
            continue

    if len(mcaps) < 2:
        return {
            "rank1_ticker": None, "rank1_mcap": None,
            "rank2_ticker": None, "rank2_mcap": None,
            "gap_pct": None, "overtake_detected": False, "gap_below_10pct": False,
        }

    sorted_mcaps = sorted(mcaps.items(), key=lambda x: x[1], reverse=True)
    r1_ticker, r1_mcap = sorted_mcaps[0]
    r2_ticker, r2_mcap = sorted_mcaps[1]
    gap_pct = round((r1_mcap - r2_mcap) / r1_mcap * 100, 1)

    return {
        "rank1_ticker": r1_ticker,
        "rank1_mcap": r1_mcap,
        "rank2_ticker": r2_ticker,
        "rank2_mcap": r2_mcap,
        "gap_pct": gap_pct,
        "overtake_detected": False,  # rank1 is always the current leader by definition
        "gap_below_10pct": gap_pct < 10.0,
    }
