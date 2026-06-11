"""MA50 백테스트 실행 스크립트 — yfinance 데이터 → outputs/backtest_results.json."""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

import yfinance as yf
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engines.backtest_ma50 import backtest_ticker
from engines.ma50_signals import MA50_DEFAULT_PARAMS

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "LLY",  "UNH",  "JNJ",
    "JPM",  "V",    "XOM",  "WMT",  "PG",
    "MA",
]

PERIOD = "5y"
INITIAL_CAPITAL = 100_000.0
RISK_PER_TRADE  = 0.10


def fetch_ohlcv(ticker: str) -> dict | None:
    """yfinance에서 OHLCV 를 다운로드하고 NaN을 제거해 반환."""
    try:
        df = yf.download(ticker, period=PERIOD, auto_adjust=True, progress=False)
        df = df.dropna()
        if len(df) < 60:
            return None
        # MultiIndex 처리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return {
            "close":  df["Close"],
            "open_":  df["Open"],
            "high":   df["High"],
            "low":    df["Low"],
            "volume": df["Volume"],
        }
    except Exception as e:
        print(f"  [WARN] {ticker} 다운로드 실패: {e}")
        return None


def main() -> None:
    print(f"MA50 백테스트 실행 — 기간: {PERIOD}, 종목 수: {len(TICKERS)}")

    # SPY 다운로드
    print("SPY 다운로드 중...")
    spy_raw = yf.download("SPY", period=PERIOD, auto_adjust=True, progress=False)
    spy_raw = spy_raw.dropna()
    if isinstance(spy_raw.columns, pd.MultiIndex):
        spy_raw.columns = spy_raw.columns.get_level_values(0)
    spy_close = spy_raw["Close"]

    params = dict(MA50_DEFAULT_PARAMS)
    results = []

    for ticker in TICKERS:
        print(f"  {ticker} ...", end=" ", flush=True)
        data = fetch_ohlcv(ticker)
        if data is None:
            print("SKIP")
            continue
        result = backtest_ticker(
            close=data["close"],
            open_=data["open_"],
            high=data["high"],
            low=data["low"],
            volume=data["volume"],
            spy_close=spy_close,
            ticker=ticker,
            params=params,
            initial_capital=INITIAL_CAPITAL,
            risk_per_trade=RISK_PER_TRADE,
        )
        results.append(result)
        perf = result["performance"]
        print(
            f"trades={perf['num_trades']:3d}  "
            f"ret={perf['total_return_pct']:+7.1f}%  "
            f"cagr={perf['cagr_pct']:+6.1f}%  "
            f"dd={perf['max_drawdown_pct']:+6.1f}%  "
            f"wr={perf['win_rate_pct']:5.1f}%  "
            f"sharpe={perf['sharpe']:5.2f}"
        )

    # 집계
    all_trades = [t for r in results for t in r["trades"]]
    output = {
        "as_of":   str(date.today()),
        "period":  PERIOD,
        "tickers": TICKERS,
        "params":  {k: v for k, v in params.items() if not isinstance(v, tuple)},
        "results": results,
        "summary": {
            "total_tickers_run": len(results),
            "total_trades":      len(all_trades),
        },
    }

    out_path = ROOT / "outputs" / "backtest_results.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n저장 완료: {out_path}")
    print(f"총 거래: {len(all_trades)}건 / 종목: {len(results)}개")


if __name__ == "__main__":
    main()
