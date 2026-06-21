"""
유니버스 스크리닝 — 주 1회 실행 (매주 토요일 00:00 UTC)
S&P500 + NASDAQ100 → 시총 $30B+ 필터 → toppick_score 계산 → universe.json

출력: app/public/data/universe.json
  - 상위 50개 (score ≥ 60) 저장
  - EOD 배치(fetch_momentum.py)가 이 파일을 읽어 positions.json 자동 sync
"""
import json
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; universe-screener/1.0)"}

def website_to_domain(url: str) -> str:
    if not url:
        return ""
    host = url.split("//")[-1].split("/")[0]
    return host.lstrip("www.")


def get_ko_name(symbol: str, *_) -> str:
    """네이버 금융 내부 API로 한국어 종목명 조회.
    .O(NASDAQ) → .K(NYSE 일부) → 접미사 없음 순으로 시도."""
    for naver_sym in (f"{symbol}.O", f"{symbol}.K", symbol):
        try:
            url = f"https://api.stock.naver.com/stock/{naver_sym}/basic"
            r = requests.get(url, headers=_HEADERS, timeout=5)
            if r.status_code == 200:
                name = r.json().get("stockName") or ""
                if name:
                    return name
        except Exception:
            pass
    return ""

DATA    = Path(__file__).parent.parent / "app/public/data"
OUT     = DATA / "universe.json"
MCAP_MIN   = 30_000_000_000   # $30B 이상
SCORE_MIN  = 60               # 저장 최소 점수
TOP_N      = 50               # universe.json 저장 상한
RATE_DELAY = 0.5              # 종목 간 딜레이(초) — yfinance rate limit 회피


# ── 유니버스 소싱 ──────────────────────────────────────────────────────────────

def _html_tables(url: str) -> list:
    html = requests.get(url, headers=_HEADERS, timeout=15).text
    return pd.read_html(html)


def get_sp500() -> list:
    try:
        df = _html_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        col = next(c for c in df.columns if c in ("Symbol", "Ticker"))
        return [s.replace(".", "-") for s in df[col].tolist()]
    except Exception as e:
        print(f"[경고] S&P500 조회 실패: {e}")
        return []


def get_nasdaq100() -> list:
    try:
        for df in _html_tables("https://en.wikipedia.org/wiki/Nasdaq-100"):
            col = next((c for c in df.columns if c in ("Ticker", "Symbol")), None)
            if col and len(df) > 50:
                return [s.replace(".", "-") for s in df[col].tolist()]
    except Exception as e:
        print(f"[경고] NASDAQ100 조회 실패: {e}")
    return []


# ── 정량 해자 프록시 (moat_score 자동, 0~5) ──────────────────────────────────

def calc_moat_score_auto(info: dict) -> float:
    """
    해자 정량 프록시:
      매출총이익률(pricing power)  → 0~1.5
      영업이익률(구조적 우위)       → 0~1.5
      ROE(자본효율)                → 0~1.5
      매출성장 일관성(고객 충성도)  → 0~0.5
    """
    score = 0.0

    gm = info.get("grossMargins") or 0
    if gm >= 0.60:   score += 1.5
    elif gm >= 0.40: score += 1.0
    elif gm >= 0.20: score += 0.5

    om = info.get("operatingMargins") or 0
    if om >= 0.25:   score += 1.5
    elif om >= 0.15: score += 1.0
    elif om >= 0.08: score += 0.5

    roe = info.get("returnOnEquity") or 0
    if roe >= 0.30:   score += 1.5
    elif roe >= 0.20: score += 1.0
    elif roe >= 0.10: score += 0.5

    rg = info.get("revenueGrowth") or 0
    if rg >= 0.10:   score += 0.5
    elif rg >= 0.05: score += 0.25

    return round(min(5.0, score), 2)


# ── toppick 스코어링 (fetch_momentum.py와 동일 로직) ──────────────────────────

def calc_growth_score(info: dict) -> float:
    rev  = info.get("revenueGrowth") or 0.0
    earn = info.get("earningsGrowth") or 0.0

    def sr(r):
        if r > 0.50: return 5.0
        if r > 0.30: return 4.0
        if r > 0.15: return 3.0
        if r > 0.05: return 2.0
        if r > 0.00: return 1.0
        return 0.0

    def se(e):
        if e > 1.00: return 5.0
        if e > 0.50: return 4.0
        if e > 0.20: return 3.0
        if e > 0.05: return 2.0
        if e > 0.00: return 1.0
        return 0.0

    return round((sr(rev) + se(earn)) / 2, 2)


def calc_financial_health(info: dict) -> float:
    fcf = info.get("freeCashflow") or 0
    rev = info.get("totalRevenue") or 1
    opm = info.get("operatingMargins") or 0.0
    roe = info.get("returnOnEquity") or 0.0
    fcf_margin = fcf / rev if rev > 0 else 0.0

    def sf(m):
        if m > 0.30: return 2.0
        if m > 0.15: return 1.5
        if m > 0.05: return 1.0
        if m > 0.00: return 0.5
        return 0.0

    def so(m):
        if m > 0.40: return 1.5
        if m > 0.25: return 1.0
        if m > 0.15: return 0.7
        if m > 0.00: return 0.3
        return 0.0

    def sr(r):
        if r > 0.50: return 1.0
        if r > 0.30: return 0.8
        if r > 0.15: return 0.5
        if r > 0.00: return 0.2
        return 0.0

    return round(min(5.0, sf(fcf_margin) + so(opm) + sr(roe)), 2)


def calc_earnings_momentum(info: dict) -> float:
    trailing_eps = info.get("trailingEps") or 0.0
    forward_eps  = info.get("forwardEps")  or 0.0
    qtr_growth   = info.get("earningsQuarterlyGrowth") or 0.0

    if trailing_eps > 0 and forward_eps:
        r = forward_eps / trailing_eps
        eps_score = 2.0 if r > 1.30 else 1.5 if r > 1.10 else 1.0 if r > 1.00 else 0.0
    else:
        eps_score = 0.0

    qtr_score = 3.0 if qtr_growth > 0.50 else 2.0 if qtr_growth > 0.20 else 1.0 if qtr_growth > 0.00 else 0.0

    return round(min(5.0, eps_score + qtr_score), 2)


def calc_toppick_score(growth: float, moat: float, earnings: float, health: float) -> int:
    raw = (growth * 0.30 + moat * 0.30 + earnings * 0.20 + health * 0.20) / 5.0
    return min(100, max(0, round(raw * 100)))


# ── 종목 스크리닝 ──────────────────────────────────────────────────────────────

def screen(symbol: str):
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception as e:
        print(f"  [{symbol}] 조회 실패: {e}")
        return None

    mcap = info.get("marketCap") or 0
    if mcap < MCAP_MIN:
        return None

    # MA50 위 종목만 (모멘텀 확인) — info에 이미 포함된 값 사용
    price  = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    ma50   = info.get("fiftyDayAverage") or 0
    if price <= 0 or ma50 <= 0 or price < ma50:
        return None

    moat     = calc_moat_score_auto(info)
    growth   = calc_growth_score(info)
    health   = calc_financial_health(info)
    earnings = calc_earnings_momentum(info)
    score    = calc_toppick_score(growth, moat, earnings, health)

    if score < SCORE_MIN:
        return None

    name    = info.get("shortName") or info.get("longName") or symbol
    name_ko = get_ko_name(symbol, info.get("exchange", ""))
    domain  = website_to_domain(info.get("website", ""))
    return {
        "symbol":         symbol,
        "name":           name,
        "name_ko":        name_ko,
        "domain":         domain,
        "toppick_score":  score,
        "moat_score":     moat,
        "growth_score":   growth,
        "earnings_score": earnings,
        "health_score":   health,
        "market_cap":     mcap,
        "sector":         info.get("sector", ""),
    }


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    today = date.today()
    print(f"\n[유니버스 스크리닝] {today}")

    sp500   = get_sp500()
    ndq100  = get_nasdaq100()
    tickers = list(dict.fromkeys(sp500 + ndq100))  # 순서 유지 중복 제거
    print(f"  후보 풀: {len(tickers)}개 (S&P500 {len(sp500)} + NASDAQ100 {len(ndq100)}, 중복 제거)")

    results = []
    for i, sym in enumerate(tickers):
        print(f"  [{i+1}/{len(tickers)}] {sym}", end=" ")
        item = screen(sym)
        if item:
            print(f"→ {item['toppick_score']}점 ✓")
            results.append(item)
        else:
            print("→ skip")
        time.sleep(RATE_DELAY)

    results.sort(key=lambda x: x["toppick_score"], reverse=True)
    top = results[:TOP_N]

    OUT.write_text(json.dumps({
        "as_of": today.isoformat(),
        "total_screened": len(tickers),
        "qualified": len(results),
        "items": top,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✓ 유니버스 스크리닝 완료 — {len(top)}개 저장 ({OUT.name})")
    for r in top[:10]:
        print(f"  {r['symbol']:6s} {r['toppick_score']:3d}점  (M={r['moat_score']} G={r['growth_score']} E={r['earnings_score']} H={r['health_score']})")
    if len(top) > 10:
        print(f"  ... 외 {len(top)-10}개")


if __name__ == "__main__":
    main()
