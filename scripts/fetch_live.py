"""
장중 준실시간 배치 — 5~15분 주기 실행
출력: live.json (현재가·등락률·거리 — 표시 전용, 신호 변경 없음)
      masam_market.json (VIX·공포탐욕·달러환율 실시간 갱신)
"""
import json
import urllib.request
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


def fetch_fear_greed() -> Optional[int]:
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Origin": "https://www.cnn.com",
            "Referer": "https://www.cnn.com/markets/fear-and-greed",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        score = data.get("fear_and_greed", {}).get("score")
        return int(round(score)) if score is not None else None
    except Exception:
        return None


def fetch_mcap_live() -> dict:
    """mcap_daily.json의 ticker 목록에서 change_pct만 수집. mcap_usd는 daily 기준."""
    mcap_daily = load_json(DATA / "mcap_daily.json")
    result = {}
    for item in mcap_daily.get("items", []):
        ticker = item["ticker"]
        try:
            fi = yf.Ticker(ticker).fast_info
            price = getattr(fi, "last_price", None)
            prev  = getattr(fi, "previous_close", None)
            change_pct = round((price - prev) / prev * 100, 2) if price and prev else None
            result[ticker] = {"change_pct": change_pct}
        except Exception:
            result[ticker] = {"change_pct": None}
    return result


def fetch_ohlc_ath(ticker: str, since_date: Optional[str] = None) -> dict:
    """사상최고점(종가) + 마삼 이후 장중 저가"""
    try:
        t = yf.Ticker(ticker)
        hist_1y = t.history(period="1y", auto_adjust=True)
        ath       = float(hist_1y["Close"].max())             if not hist_1y.empty else 0
        prev_high = float(hist_1y["Close"].iloc[:-1].max())   if len(hist_1y) > 1 else ath
        # 마삼 이후 장중 저가
        if since_date:
            hist_since = t.history(start=since_date, auto_adjust=True)
            intra_low = float(hist_since["Low"].min()) if not hist_since.empty else 0
        else:
            hist_1d = t.history(period="1d", interval="1d", auto_adjust=True)
            intra_low = float(hist_1d["Low"].iloc[-1]) if not hist_1d.empty else 0
        return {"ath": round(ath, 2), "prev_high": round(prev_high, 2),
                "intra_low": round(intra_low, 2)}
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
    from datetime import timedelta
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    update_kst = now_kst.strftime("%H:%M") + " KST"

    print(f"[Live 배치] {now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}")

    existing_live = load_json(LIVE)
    masam_json = load_json(DATA / "masam.json")

    # 1등주
    rank1_ticker = masam_json.get("leader_status", {}).get("rank1_ticker", "NVDA")

    # 지수 조회
    ixic_q  = fetch_quote("^IXIC")
    gspc_q  = fetch_quote("^GSPC")
    dji_q   = fetch_quote("^DJI")
    last_masam_date = masam_json.get("masam", {}).get("last_masam_date")
    rank1_q = fetch_quote(rank1_ticker)
    qqq_q   = fetch_quote("QQQ")
    rank1_extra = fetch_ohlc_ath(rank1_ticker, since_date=last_masam_date)
    qqq_extra   = fetch_ohlc_ath("QQQ", since_date=last_masam_date)
    ixic_extra  = fetch_ohlc_ath("^IXIC")

    # 마삼까지 거리
    ixic_price = ixic_q["price"] if ixic_q else 0
    dist_masam = masam_distance(ixic_price, existing_live) if ixic_q else 0

    # ATH 대비 % (IXIC 52주 고점 기준)
    ixic_ath = ixic_extra.get("ath", 0)
    from_ath_pct = round((ixic_price - ixic_ath) / ixic_ath * 100, 1) if ixic_ath > 0 else 0

    # 헤지
    hedge_prices = {}
    for tk in HEDGE_TICKERS:
        q = fetch_quote(tk)
        hedge_prices[tk] = q["price"] if q else existing_live.get("hedges", {}).get(tk)

    # VIX, 달러 환율, 공포탐욕, 시가총액 등락률
    vix_q     = fetch_quote("^VIX")
    usdkrw_q  = fetch_quote("USDKRW=X")
    fear_greed = fetch_fear_greed()
    mcap_live  = fetch_mcap_live()
    print(f"  VIX: {vix_q}  USD/KRW: {usdkrw_q}  F&G: {fear_greed}")

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
        "intra_low": rank1_extra.get("intra_low", prev_rank1.get("intra_low")),
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
        "qqq": {
            "price": qqq_q["price"] if qqq_q else existing_live.get("qqq", {}).get("price"),
            "change_pct": qqq_q["change_pct"] if qqq_q else existing_live.get("qqq", {}).get("change_pct"),
            "ath": qqq_extra.get("ath", existing_live.get("qqq", {}).get("ath")),
            "intra_low": qqq_extra.get("intra_low", existing_live.get("qqq", {}).get("intra_low")),
        },
        "hedges": hedge_prices,
        "mcap_live": mcap_live,
        "live_market": {
            "vix":         vix_q["price"] if vix_q else None,
            "vix_chg":     vix_q["change_pct"] if vix_q else None,
            "usd_krw":     round(usdkrw_q["price"], 1) if usdkrw_q else None,
            "usd_krw_chg": round(usdkrw_q["change_pct"], 2) if usdkrw_q else None,
            "fear_greed":  fear_greed,
        },
    }

    save_json(LIVE, live_out)
    print(f"  IXIC: {ixic_q}  1등주: {rank1_q}")
    print(f"  저장 완료: {LIVE.name}")


if __name__ == "__main__":
    main()
