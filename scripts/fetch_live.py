"""
장중 준실시간 배치 — 5~15분 주기 실행
출력: live.json (현재가·등락률·거리 — 표시 전용, 신호 변경 없음)
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yfinance as yf

DATA = Path(__file__).parent.parent / "app/public/data"
LIVE = DATA / "live.json"

HEDGE_TICKERS = ["TLT", "IAU", "GLD", "TIP"]


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_quote(ticker: str) -> Optional[dict]:
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        price = getattr(fi, "last_price", None)
        prev  = getattr(fi, "previous_close", None)
        if price is None or prev is None:
            return None
        chg = (price - prev) / prev * 100
        return {"price": round(price, 2), "change_pct": round(chg, 2)}
    except Exception:
        return None


def fetch_ohlc_ath(ticker: str) -> dict:
    """당일 고가/저가 + 52주 최고점"""
    try:
        t = yf.Ticker(ticker)
        hist_1d = t.history(period="1d", interval="1d", auto_adjust=True)
        hist_1y = t.history(period="1y", auto_adjust=True)
        day_high = float(hist_1d["High"].iloc[-1]) if not hist_1d.empty else 0
        day_low  = float(hist_1d["Low"].iloc[-1])  if not hist_1d.empty else 0
        ath      = float(hist_1y["Close"].max())    if not hist_1y.empty else 0
        prev_high = float(hist_1y["Close"].iloc[:-1].max()) if len(hist_1y) > 1 else ath
        return {"ath": round(ath, 2), "prev_high": round(prev_high, 2),
                "day_high": round(day_high, 2), "day_low": round(day_low, 2)}
    except Exception:
        return {}


def masam_distance(ixic_price: float, existing_live: dict) -> float:
    """현재가 기준 마삼(-3%) 거리"""
    prev = existing_live.get("nasdaq", {}).get("price", 0)
    if prev <= 0:
        return 0.0
    # 오늘 open 기준이 없으면 live의 직전 종가로 근사
    threshold = prev * 0.97
    dist = (ixic_price - threshold) / threshold * 100
    return round(dist, 2)


def main():
    now_utc = datetime.now(timezone.utc)
    update_kst = now_utc.strftime("%H:%M") + " KST"  # 표시용 (실제 KST = UTC+9 아님, 근사)

    print(f"[Live 배치] {now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}")

    existing_live = load_json(LIVE)
    masam_json = load_json(DATA / "masam.json")

    # 1등주
    rank1_ticker = masam_json.get("leader_status", {}).get("rank1_ticker", "NVDA")

    # 지수 조회
    ixic_q  = fetch_quote("^IXIC")
    gspc_q  = fetch_quote("^GSPC")
    dji_q   = fetch_quote("^DJI")
    rank1_q = fetch_quote(rank1_ticker)
    rank1_extra = fetch_ohlc_ath(rank1_ticker)

    # 마삼까지 거리
    ixic_price = ixic_q["price"] if ixic_q else 0
    dist_masam = masam_distance(ixic_price, existing_live) if ixic_q else 0

    # ATH 대비 %
    rank1_ath = rank1_extra.get("ath", 0)
    from_ath_pct = round((ixic_price - rank1_ath) / rank1_ath * 100, 1) if rank1_ath > 0 else 0

    # 헤지
    hedge_prices = {}
    for tk in HEDGE_TICKERS:
        q = fetch_quote(tk)
        hedge_prices[tk] = q["price"] if q else existing_live.get("hedges", {}).get(tk)

    # 1등주 메타 (기존 값 유지)
    prev_rank1 = existing_live.get("rank1", {})
    rank1_info = {
        "ticker": rank1_ticker,
        "name": prev_rank1.get("name", rank1_ticker),
        "domain": prev_rank1.get("domain", ""),
        "si": prev_rank1.get("si", ""),
        "price": rank1_q["price"] if rank1_q else prev_rank1.get("price"),
        "change_pct": rank1_q["change_pct"] if rank1_q else prev_rank1.get("change_pct"),
        "ath": rank1_extra.get("ath", prev_rank1.get("ath")),
        "prev_high": rank1_extra.get("prev_high", prev_rank1.get("prev_high")),
        "day_high": rank1_extra.get("day_high"),
        "day_low": rank1_extra.get("day_low"),
    }

    live_out = {
        "as_of": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "update_time": update_kst,
        "nasdaq": {
            "price": ixic_q["price"] if ixic_q else existing_live.get("nasdaq", {}).get("price"),
            "change_pct": ixic_q["change_pct"] if ixic_q else None,
            "dist_to_masam_pct": dist_masam,
            "from_ath_pct": from_ath_pct,
            "last_masam_date": masam_json.get("masam", {}).get("last_masam_date", ""),
        },
        "sp500": {
            "price": gspc_q["price"] if gspc_q else existing_live.get("sp500", {}).get("price"),
            "change_pct": gspc_q["change_pct"] if gspc_q else None,
        },
        "dow": {
            "price": dji_q["price"] if dji_q else existing_live.get("dow", {}).get("price"),
            "change_pct": dji_q["change_pct"] if dji_q else None,
        },
        "rank1": rank1_info,
        "hedges": hedge_prices,
    }

    save_json(LIVE, live_out)
    print(f"  IXIC: {ixic_q}  1등주: {rank1_q}")
    print(f"  저장 완료: {LIVE.name}")


if __name__ == "__main__":
    main()
