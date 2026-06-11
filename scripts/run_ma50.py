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
    calc_horizontal_support, calc_recent_high,
)
from engines.ma50_signals import (
    MA50_DEFAULT_PARAMS, get_buy_signal, get_sell_signal,
    transition_state, calc_score,
)
from engines.ma50_engine import build_signal_item, build_signals_json
from scripts.state_manager import load_positions, save_positions, get_position, update_position
from engines.backtest_ma50 import calc_stop_level

_OUTPUT_SIGNALS = Path(__file__).parent.parent / "outputs" / "signals.json"
_STATE_PATH = Path(__file__).parent.parent / "state" / "positions.json"

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


def run(watchlist: list = None, state_path: str = None) -> dict:
    print("=" * 50)
    print("MA50 스크리너 엔진 실행")
    print("=" * 50)

    tickers = watchlist or _DEFAULT_WATCHLIST
    _path = Path(state_path) if state_path else _STATE_PATH
    positions = load_positions(str(_path))
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
        volume_s   = get_series(raw, ticker, "Volume")
        open_s     = get_series(raw, ticker, "Open")

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
        today_open  = float(open_s.iloc[-1]) if open_s is not None else close_last
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

        # 저장된 state 로드
        saved      = get_position(positions, ticker)
        prev_state = saved["state"]
        prev_days  = saved["days_in_state"]

        # 수평 지지선 계산
        horiz_support = (
            calc_horizontal_support(low_s)
            if low_s is not None else 0.0
        )

        # recent_high: 포지션 보유 중이면 먼저 오늘 high로 갱신 (sell 판단 기준)
        saved_recent_high = float(saved.get("recent_high", 0.0) or 0.0)
        today_high_val = float(high_s.iloc[-1])
        if prev_state in ("BUY", "HOLDING", "SELL_WATCH"):
            running_recent_high = calc_recent_high(close_last, today_high_val, saved_recent_high)
        else:
            running_recent_high = 0.0

        # 상태에 따라 시그널 산출
        buy_sig  = None
        sell_sig = None
        if prev_state == "WATCH":
            buy_sig = get_buy_signal(
                close_s, high_s, low_s if low_s is not None else high_s,
                ma50, ma200, vol_ratio, gap50, slope_pct, rs_pct_val, regime, params,
            )
        elif prev_state in ("HOLDING", "SELL_WATCH"):
            sell_sig = get_sell_signal(
                prev_state, close_s, ma50, ma200,
                rs_pct_val, prev_days, regime, params,
                recent_high=running_recent_high,
            )
        # BUY / SELL: 전일 보류 주문 → transition만 수행

        new_state = transition_state(prev_state, buy_sig, sell_sig)
        new_days  = 0 if new_state != prev_state else prev_days + 1

        # 포지션 필드 결정
        if new_state == "HOLDING" and prev_state == "BUY":
            new_entry   = round(today_open, 2)
            new_stop    = round(calc_stop_level(new_entry, ma50_last, atr14), 2)
            new_entered = str(as_of_dt)
            new_stype   = saved.get("signal_type")
        elif new_state == "WATCH" and prev_state == "SELL":
            new_entry   = None
            new_stop    = None
            new_entered = None
            new_stype   = None
        elif new_state == "BUY":
            new_entry   = None
            new_stop    = None
            new_entered = None
            new_stype   = buy_sig
        else:
            new_entry   = saved.get("entry_price")
            new_stop    = saved.get("stop_level")
            new_entered = saved.get("entered_at")
            new_stype   = saved.get("signal_type")

        # recent_high 최종값 (신규 진입 시 오늘부터 시작, 청산 시 초기화)
        if new_state in ("BUY", "HOLDING", "SELL_WATCH"):
            new_recent_high = running_recent_high if running_recent_high > 0 else max(close_last, today_high_val)
        else:
            new_recent_high = 0.0

        trailing_stop_pct = params.get("trailing_stop_pct", 0.20)
        new_trailing_stop = (
            round(new_recent_high * (1 - trailing_stop_pct), 2)
            if new_recent_high > 0 else None
        )

        # position_status: 1차(강돌파/초기추세) / 2차(지지반등)
        _STATUS_MAP = {"STRONG_BREAKOUT": "1차", "EARLY_TREND": "1차", "BOUNCE": "2차"}
        if new_state in ("WATCH", "SELL"):
            new_position_status = None
        elif new_state == "BUY":
            new_position_status = _STATUS_MAP.get(buy_sig or "", None)
        else:
            new_position_status = _STATUS_MAP.get(
                new_stype or "", saved.get("position_status")
            )

        metrics = build_metrics(
            close_last=close_last, ma50_last=ma50_last, ma200_last=ma200_last,
            vol_ratio=vol_ratio, rs_pct=rs_pct_val, rs_sector_pct=rs_pct_val,
            slope_pct=slope_pct, high_n=high_n, atr14=atr14, sector_etf=sector,
            trailing_stop=new_trailing_stop,
            recent_high=new_recent_high if new_recent_high > 0 else None,
            horizontal_support=horiz_support if horiz_support > 0 else None,
        )

        positions = update_position(
            positions, ticker, new_state, new_days,
            new_entered, new_entry, new_stop, new_stype,
            recent_high=new_recent_high,
            trailing_stop_line=new_trailing_stop,
            position_status=new_position_status,
            horizontal_support=round(horiz_support, 2) if horiz_support > 0 else None,
        )

        # signals.json 출력용
        signal_type  = buy_sig or sell_sig or "OK"
        state        = new_state
        trigger      = (
            f"MA50 {buy_sig.replace('_', ' ')}" if buy_sig
            else ("MA50 하향 이탈" if sell_sig else "")
        )

        score = calc_score(vol_ratio, gap50, rs_pct_val, slope_pct,
                           ma50_last, ma200_last, params)

        items.append(build_signal_item(
            ticker, signal_type, state, score, trigger, metrics,
            position_status=new_position_status,
        ))

    save_positions(positions, str(_path))
    print(f"state 저장: {_path}")

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
