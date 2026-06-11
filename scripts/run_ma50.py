"""MA50 스크리너 엔진 실행 진입점."""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.ma50_indicators import (
    calc_ma, calc_slope_pct, calc_gap, calc_highN,
    calc_atr14, calc_rs_raw, calc_rs_pct, calc_regime, build_metrics,
)
from engines.ma50_signals import (
    MA50_DEFAULT_PARAMS, get_buy_signal, get_sell_signal,
    transition_state, calc_score,
)
from engines.ma50_engine import build_signal_item, build_signals_json

_OUTPUT_SIGNALS = Path(__file__).parent.parent / "outputs" / "signals.json"

_SECTOR_MAP: dict = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AVGO": "XLK",
    "AMZN": "XLY", "TSLA": "XLY",
    "GOOGL": "XLC", "META": "XLC",
    "JPM": "XLF", "BRK-B": "XLF",
    "LLY": "XLV", "JNJ": "XLV",
    "XOM": "XLE", "CVX": "XLE",
    "COST": "XLP", "WMT": "XLP",
}

_DEFAULT_WATCHLIST = list(_SECTOR_MAP.keys())


def run(watchlist: list = None) -> dict:
    print("=" * 50)
    print("MA50 스크리너 엔진 실행")
    print("=" * 50)

    tickers = watchlist or _DEFAULT_WATCHLIST
    params  = dict(MA50_DEFAULT_PARAMS)

    print(f"SPY + {len(tickers)}종목 다운로드 중...")
    all_tickers = ["SPY"] + [t for t in tickers if t != "SPY"]
    raw = yf.download(all_tickers, period="2y", auto_adjust=True,
                      progress=False, group_by="ticker")

    def get_series(df, ticker, col):
        try:
            s = df[ticker][col].squeeze().dropna()
            return s if len(s) > 60 else None
        except Exception:
            return None

    close_spy = get_series(raw, "SPY", "Close")
    if close_spy is None:
        raise RuntimeError("SPY 데이터 수집 실패")

    regime   = calc_regime(close_spy)
    as_of_dt = close_spy.index[-1].date()
    print(f"레짐: {regime} | 기준일: {as_of_dt}")

    # RS_raw 계산 (유니버스 전체)
    rs_raw_map: dict = {}
    for t in tickers:
        c = get_series(raw, t, "Close")
        if c is not None:
            rs_raw_map[t] = calc_rs_raw(c, close_spy)

    items = []
    for ticker in tickers:
        close_s  = get_series(raw, ticker, "Close")
        high_s   = get_series(raw, ticker, "High")
        low_s    = get_series(raw, ticker, "Low")
        volume_s = get_series(raw, ticker, "Volume")

        if close_s is None or high_s is None or len(close_s) < 60:
            continue

        ma50  = calc_ma(close_s, 50)
        ma200 = calc_ma(close_s, 200)
        vol20 = calc_ma(volume_s, 20) if volume_s is not None else None

        ma50_valid  = ma50.dropna()
        ma200_valid = ma200.dropna()
        if ma50_valid.empty:
            continue

        close_last  = float(close_s.iloc[-1])
        ma50_last   = float(ma50_valid.iloc[-1])
        ma200_last  = float(ma200_valid.iloc[-1]) if not ma200_valid.empty else 0.0
        vol_last    = float(volume_s.iloc[-1]) if volume_s is not None else 0.0
        vol20_clean = vol20.dropna() if vol20 is not None else None
        vol20_last  = float(vol20_clean.iloc[-1]) if (vol20_clean is not None and not vol20_clean.empty) else 1.0
        vol_ratio   = vol_last / vol20_last if vol20_last > 0 else 0.0
        gap50       = calc_gap(close_last, ma50_last)
        slope_pct   = calc_slope_pct(ma50)
        high_n      = calc_highN(high_s, params["breakout_high_lookback"])
        atr14       = calc_atr14(high_s, low_s, close_s) if low_s is not None else 0.0
        rs_pct_val  = calc_rs_pct(ticker, rs_raw_map)
        sector      = _SECTOR_MAP.get(ticker, "SPY")

        metrics = build_metrics(
            close_last=close_last, ma50_last=ma50_last, ma200_last=ma200_last,
            vol_ratio=vol_ratio, rs_pct=rs_pct_val, rs_sector_pct=rs_pct_val,
            slope_pct=slope_pct, high_n=high_n, atr14=atr14, sector_etf=sector,
        )

        buy  = get_buy_signal(
            close_s, high_s, low_s if low_s is not None else high_s,
            ma50, ma200, vol_ratio, gap50, slope_pct, rs_pct_val, regime, params,
        )
        sell = get_sell_signal(
            "HOLDING", close_s, ma50, ma200, rs_pct_val, 0, regime, params,
        ) if close_last < ma50_last else None

        if buy:
            state       = "BUY"
            signal_type = buy
            trigger     = f"MA50 {buy.replace('_', ' ')}"
        elif sell:
            state       = "SELL" if sell == "SELL" else "SELL_WATCH"
            signal_type = sell
            trigger     = "MA50 하향 이탈"
        elif close_last >= ma50_last:
            state       = "HOLDING"
            signal_type = "OK"
            trigger     = ""
        else:
            state       = "WATCH"
            signal_type = "OK"
            trigger     = ""

        score = calc_score(vol_ratio, gap50, rs_pct_val, slope_pct,
                           ma50_last, ma200_last, params)

        items.append(build_signal_item(ticker, signal_type, state, score, trigger, metrics))

    items.sort(key=lambda x: x["score"], reverse=True)

    result = build_signals_json(as_of=as_of_dt, regime=regime, items=items)
    _OUTPUT_SIGNALS.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str)
    )
    print(f"\nsignals.json 저장: {_OUTPUT_SIGNALS}")
    print(f"총 {len(items)}종목 | 레짐: {regime}")
    buy_count  = sum(1 for i in items if i["state"] == "BUY")
    sell_count = sum(1 for i in items if i["state"] in ("SELL", "SELL_WATCH"))
    print(f"BUY: {buy_count}  SELL/WATCH: {sell_count}  기타: {len(items)-buy_count-sell_count}")
    return result


if __name__ == "__main__":
    run()
