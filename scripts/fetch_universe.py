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
MCAP_MIN   = 1_000_000_000    # $1B 이상 (중소형 포함)
SCORE_MIN  = 60               # 저장 최소 점수
TOP_N      = 60               # universe.json 저장 상한
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


def get_nasdaq_all() -> list:
    """NASDAQ 스크리너 API로 미국 전체 상장 종목 티커 추출 (NASDAQ + NYSE).
    API 응답의 marketCap으로 MCAP_MIN 이상만 반환 — yfinance 호출 수 대폭 절감."""
    tickers = []
    api_headers = {**_HEADERS, "Accept": "application/json"}
    for exchange in ("NASDAQ", "NYSE"):
        try:
            url = (
                f"https://api.nasdaq.com/api/screener/stocks"
                f"?tableonly=true&limit=6000&exchange={exchange}"
            )
            r = requests.get(url, headers=api_headers, timeout=20)
            r.raise_for_status()
            rows = r.json().get("data", {}).get("table", {}).get("rows", [])
            qualified = []
            for row in rows:
                sym = row.get("symbol", "").strip()
                if not sym:
                    continue
                # API mcap: "$1,234,567,890" 형식
                mcap_str = row.get("marketCap", "").replace("$", "").replace(",", "")
                try:
                    mcap = float(mcap_str)
                except ValueError:
                    mcap = 0
                if mcap >= MCAP_MIN:
                    qualified.append(sym)
            tickers.extend(qualified)
            print(f"  {exchange}: {len(rows)}개 → 시총 필터 후 {len(qualified)}개")
        except Exception as e:
            print(f"[경고] {exchange} 조회 실패: {e}")
    return tickers


# ── 정량 해자 프록시 (moat_score 자동, 0~5) ──────────────────────────────────

def calc_moat_score_auto(info: dict, income_stmt=None) -> float:
    """
    해자 자동 프록시 (0~5):
      Pricing Power  (grossMargins)       → 브랜드·전환비용  0~1.5
      Scale Efficiency (OPM + ROE)        → 규모의 경제      0~1.5
      Innovation     (R&D / Revenue)      → 무형자산·IP      0~1.0
      Market Premium (P/B)                → 시장 인정 해자   0~1.0
    """
    score = 0.0

    gm = info.get("grossMargins") or 0
    if gm >= 0.70:   score += 1.5
    elif gm >= 0.50: score += 1.2
    elif gm >= 0.35: score += 0.8
    elif gm >= 0.20: score += 0.4

    om  = info.get("operatingMargins") or 0
    roe = info.get("returnOnEquity")   or 0
    scale = 0.0
    if om  >= 0.30:  scale += 0.75
    elif om  >= 0.20: scale += 0.50
    elif om  >= 0.10: scale += 0.25
    if roe >= 0.30:  scale += 0.75
    elif roe >= 0.20: scale += 0.50
    elif roe >= 0.10: scale += 0.25
    score += min(1.5, scale)

    # R&D는 income_stmt에서 가져옴 (info에 없음)
    rd_ratio = 0.0
    if income_stmt is not None and not income_stmt.empty:
        try:
            rd  = float(income_stmt.loc["Research And Development"].iloc[0]) if "Research And Development" in income_stmt.index else 0
            rev_row = "Total Revenue" if "Total Revenue" in income_stmt.index else None
            rev = float(income_stmt.loc[rev_row].iloc[0]) if rev_row else (info.get("totalRevenue") or 1)
            rd_ratio = rd / rev if rev > 0 else 0
        except Exception:
            pass
    if rd_ratio >= 0.15:   score += 1.0
    elif rd_ratio >= 0.08: score += 0.6
    elif rd_ratio >= 0.03: score += 0.3

    pb = info.get("priceToBook") or 0
    if pb > 0:  # 음수 PBR(자본잠식) 제외
        if pb >= 15:    score += 1.0
        elif pb >= 8:   score += 0.7
        elif pb >= 3:   score += 0.4
        elif pb >= 1.5: score += 0.2

    return round(min(5.0, score), 2)


def calc_eps_consistency(income_stmt) -> float:
    """연간 Diluted EPS 꾸준한 상승 여부 → 0~1.0"""
    if income_stmt is None or income_stmt.empty:
        return 0.0
    try:
        for label in ("Diluted EPS", "Basic EPS"):
            if label in income_stmt.index:
                vals = (
                    income_stmt.loc[label]
                    .dropna()
                    .sort_index(ascending=True)
                    .values.astype(float)
                )
                if len(vals) < 2 or vals[-1] <= 0:
                    return 0.0
                n = len(vals) - 1
                increases = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
                ratio = increases / n
                if ratio >= 1.00:   return 1.0
                elif ratio >= 0.75: return 0.7
                elif ratio >= 0.50: return 0.4
                return 0.0
    except Exception:
        pass
    return 0.0


# ── toppick 스코어링 (fetch_momentum.py와 동일 로직) ──────────────────────────

def calc_growth_score(info: dict) -> float:
    rev  = info.get("revenueGrowth") or 0.0
    earn = info.get("earningsGrowth") or 0.0

    # GAAP 일회성 비용·SBC·상각으로 earningsGrowth가 왜곡되는 경우 방어:
    # trailing EPS가 양수이고 forward EPS가 크게 높으면 forward 성장률로 대체
    trailing_eps = info.get("trailingEps") or 0.0
    forward_eps  = info.get("forwardEps")  or 0.0
    if earn <= -0.5 and trailing_eps > 0 and forward_eps > trailing_eps:
        earn = (forward_eps - trailing_eps) / trailing_eps
    elif (info.get('earningsGrowth') is None) and abs(trailing_eps) < 0.5 and forward_eps > 1.0:
        earn = forward_eps

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


def calc_earnings_momentum(info: dict, eps_consistency: float = 0.0) -> float:
    """
    EPS 방향 + 분기 가속도 + EPS 꾸준한 상승 → 0~5
      EPS 방향 (forward/trailing):   0~1.5
      분기 성장 가속도:               0~1.5
      EPS 일관성 (연간 추세):         0~2.0
    """
    trailing_eps = info.get("trailingEps") or 0.0
    forward_eps  = info.get("forwardEps")  or 0.0
    qtr_growth   = info.get("earningsQuarterlyGrowth") or 0.0

    if trailing_eps > 0 and forward_eps:
        ratio = forward_eps / trailing_eps
        if ratio > 1.30:   eps_dir = 1.5
        elif ratio > 1.10: eps_dir = 1.0
        elif ratio > 1.00: eps_dir = 0.5
        else:              eps_dir = 0.0
    else:
        if abs(trailing_eps) < 0.5 and forward_eps > 1.0:
            eps_dir = 1.5
        else:
            eps_dir = 0.0

    if qtr_growth > 0.50:   qtr = 1.5
    elif qtr_growth > 0.20: qtr = 1.0
    elif qtr_growth > 0.00: qtr = 0.5
    else:                   qtr = 0.0

    return round(min(5.0, eps_dir + qtr + eps_consistency * 2.0), 2)


def calc_toppick_score(growth: float, moat: float, earnings: float, health: float) -> int:
    raw = (growth * 0.30 + moat * 0.30 + earnings * 0.30 + health * 0.10) / 5.0
    return min(100, max(0, round(raw * 100)))


# ── 종목 스크리닝 ──────────────────────────────────────────────────────────────

def screen(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
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

    try:
        income_stmt = ticker.income_stmt
    except Exception:
        income_stmt = None

    eps_cons = calc_eps_consistency(income_stmt)
    moat     = calc_moat_score_auto(info, income_stmt)
    growth   = calc_growth_score(info)
    health   = calc_financial_health(info)
    earnings = calc_earnings_momentum(info, eps_cons)
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

    sp500      = get_sp500()
    ndq100     = get_nasdaq100()
    nasdaq_all = get_nasdaq_all()
    tickers = list(dict.fromkeys(sp500 + ndq100 + nasdaq_all))  # 순서 유지 중복 제거
    print(f"  후보 풀: {len(tickers)}개 (S&P500 {len(sp500)} + NASDAQ100 {len(ndq100)} + NASDAQ/NYSE {len(nasdaq_all)}, 중복 제거)")

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
