"""
EOD 배치 스크립트 — 미 장마감 후 1일 1회 실행
출력: masam.json, mcap_daily.json, momentum_market.json, masam_market.json(VIX)
"""
import json
import math
import sys
import re
import calendar
import urllib.request
from datetime import date, timedelta
from pathlib import Path
import yfinance as yf

DATA = Path(__file__).parent.parent / "app/public/data"


def require_valid(label: str, value: float) -> float:
    """가격 조회 실패(NaN)가 masam.json 등에 그대로 저장되는 걸 막는 가드.
    NaN은 JSON 스펙상 유효하지 않아 브라우저 JSON.parse가 실패하므로, 여기서 즉시 중단."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        sys.exit(f"[오류] {label} 값이 NaN입니다 — 데이터 소스 조회 실패로 배치를 중단합니다 (기존 데이터 보존)")
    return value

HEDGE_TICKERS = ["TLT", "IAU", "GLD", "TIP"]

# companiesmarketcap.com ticker → yfinance ticker (다른 경우만 명시)
YFINANCE_OVERRIDE = {
    "GOOG": "GOOGL",
}

# 투자 가능 여부: ticker에 점(.)이 없으면 미국 상장으로 간주
def _is_investable(ticker: str) -> bool:
    return "." not in ticker


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장: {path.name}")


def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


# ── 가격 데이터 ───────────────────────────────────────────────────────────────

def fetch_history(ticker: str, period: str = "1y"):
    t = yf.Ticker(ticker)
    hist = t.history(period=period, auto_adjust=True)
    if hist.empty:
        sys.exit(f"[오류] {ticker} 가격 조회 실패")
    return hist


def latest_close(hist) -> float:
    return float(hist["Close"].iloc[-1])


def ma(hist, n: int) -> float:
    closes = hist["Close"]
    if len(closes) < n:
        return float(closes.mean())
    return float(closes.iloc[-n:].mean())


def daily_change_pct(hist) -> float:
    closes = hist["Close"]
    if len(closes) < 2:
        return 0.0
    return float((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2] * 100)


def consecutive_up_days(hist) -> int:
    closes = list(hist["Close"])
    count = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] > closes[i - 1]:
            count += 1
        else:
            break
    return count


# ── 마삼 상태 머신 ─────────────────────────────────────────────────────────────

def update_masam_state(existing: dict, today: date, ixic_chg: float) -> dict:
    m = existing.get("masam", {})
    mode = existing.get("mode", "NORMAL")

    last_str = m.get("last_masam_date")
    last_masam = date.fromisoformat(last_str) if last_str else None
    month_count = m.get("month_count", 0)

    # 달력 월 바뀌면 카운트 리셋
    if last_masam is None or (last_masam.year, last_masam.month) != (today.year, today.month):
        month_count = 0

    # 종료 조건 체크 (새 마삼 발생 전에 먼저)
    crisis_end_str = m.get("crisis_end_dday")
    panic_end_str = m.get("panic_end_dday")

    # 모드가 NORMAL이지만 최근 마삼이 위기 기간 내라면 모드 복구
    if mode == "NORMAL" and last_masam:
        implied_crisis_end = add_months(last_masam, 1) + timedelta(days=1)
        if today < implied_crisis_end:
            mode = "CRISIS"
            crisis_end_str = implied_crisis_end.isoformat()

    if mode == "PANIC" and panic_end_str:
        if today >= date.fromisoformat(panic_end_str):
            mode = "NORMAL"
    elif mode == "CRISIS" and crisis_end_str:
        if today >= date.fromisoformat(crisis_end_str):
            mode = "NORMAL"

    # 오늘 마삼 여부
    is_masam = ixic_chg <= -3.0
    if is_masam:
        if last_masam and (last_masam.year, last_masam.month) == (today.year, today.month):
            month_count += 1
        else:
            month_count = 1
        last_masam = today
        if month_count >= 4:
            mode = "PANIC"
        elif mode == "NORMAL":
            mode = "CRISIS"

    # 종료 예정일 계산
    crisis_end = (add_months(last_masam, 1) + timedelta(days=1)).isoformat() if last_masam else None
    panic_end = (add_months(last_masam, 2) + timedelta(days=1)).isoformat() if (mode == "PANIC" and last_masam) else None

    return {
        "month_count": month_count,
        "last_masam_date": last_masam.isoformat() if last_masam else None,
        "crisis_end_dday": crisis_end if mode in ("CRISIS", "PANIC") else None,
        "panic_end_dday": panic_end,
    }, mode


# ── 목표 비중 계산 ─────────────────────────────────────────────────────────────

def calc_target_allocation(mode: str, rate_env: str) -> dict:
    if mode == "NORMAL":
        return {"stock_pct": 100, "hedge_pct": 0, "cash_pct": 0, "label": "1등주 집중"}
    elif mode == "CRISIS":
        if rate_env == "NON_ZERO":
            return {"stock_pct": 50, "hedge_pct": 50, "cash_pct": 0, "label": "말뚝 50% + 헤지 50%"}
        else:
            return {"stock_pct": 25, "hedge_pct": 25, "cash_pct": 50, "label": "말뚝 25% + IAU 25%"}
    else:  # PANIC
        return {"stock_pct": 0, "hedge_pct": 0, "cash_pct": 100, "label": "현금 100% 대기"}


def calc_hedge_type(rate_env: str, qe_active: bool, t10_trend: str, dff_trend: str = "UNKNOWN") -> dict:
    if rate_env == "ZERO":
        return {"type": "IAU_GLD_TIP", "rationale": "제로금리", "exit_trigger": "금리 인상"}
    if qe_active:
        if dff_trend == "DOWN":
            # QE + 금리 인하 경로 → 전통적 QE 환경
            return {"type": "IAU_GLD_TIP", "rationale": "비제로 + QE + DFF 하락(인하 경로)", "exit_trigger": "QE 종료 또는 금리 인상"}
        else:
            # QE + 금리 인상/불명확 → 보수적으로 달러 보유
            return {"type": "DOLLAR", "rationale": "비제로 + QE + DFF 상승 또는 불명확 (인상 리스크)", "exit_trigger": "DFF 하락 전환 또는 QE 종료"}
    if t10_trend == "DOWN":
        return {"type": "TLT", "rationale": "비제로 + QE_OFF + 10Y 하락추세", "exit_trigger": "QE 시작 또는 10Y 상승 전환"}
    return {"type": "DOLLAR", "rationale": "비제로 + QE_OFF + 10Y 상승 또는 불명확", "exit_trigger": "10Y 하락 전환 또는 QE 시작"}


# ── 올인 체크리스트 ────────────────────────────────────────────────────────────

def calc_all_in_conditions(
    mode: str, last_masam, today: date,
    consec_up: int, ixic_close: float, ixic_ath: float,
    rank1_close: float, rank1_ath: float,
    ixic_crisis_low: float, rate_env: str,
) -> list:
    trigger_pct = -30.0 if rate_env == "NON_ZERO" else -15.0
    v_pct = 10.0 if rate_env == "NON_ZERO" else 5.0
    from_ath_pct = (ixic_close - ixic_ath) / ixic_ath * 100

    cond1_met, cond1_detail = False, ""
    if last_masam:
        end = add_months(last_masam, 2 if mode == "PANIC" else 1) + timedelta(days=1)
        days_left = (end - today).days
        if today >= end:
            cond1_met = True
            cond1_detail = "충족"
        else:
            cond1_detail = f"D-{days_left}"

    cond2_met = consec_up >= 8

    cond3_met = rank1_close >= rank1_ath
    cond3_detail = f"{(rank1_close - rank1_ath) / rank1_ath * 100:+.1f}%"

    cond4_met = ixic_close >= ixic_ath
    cond4_detail = f"{from_ath_pct:+.1f}%"

    low_pct = (ixic_close - ixic_crisis_low) / ixic_crisis_low * 100 if ixic_crisis_low > 0 else 0
    cond5_met = low_pct >= v_pct
    cond5_detail = f"+{low_pct:.1f}% (필요: +{v_pct:.0f}%)" if not cond5_met else "충족"

    cond6_met = from_ath_pct <= trigger_pct
    cond6_detail = f"{from_ath_pct:.1f}% (기준: {trigger_pct:.0f}%)" if not cond6_met else "충족"

    return [
        {"id": 1, "label": "한달+1일 무마삼", "met": cond1_met, "grade": "약", "detail": cond1_detail},
        {"id": 2, "label": "8거래일 연속 상승", "met": cond2_met, "grade": "중", "detail": f"{consec_up}일 연속"},
        {"id": 3, "label": "1등주 전고 돌파", "met": cond3_met, "grade": "강", "detail": cond3_detail},
        {"id": 4, "label": "나스닥 전고 돌파", "met": cond4_met, "grade": "강", "detail": cond4_detail},
        {"id": 5, "label": f"2구간 V자(+{v_pct:.0f}%)", "met": cond5_met, "grade": "중", "detail": cond5_detail},
        {"id": 6, "label": f"긴급 올인({trigger_pct:.0f}%)", "met": cond6_met, "grade": "강", "detail": cond6_detail},
    ]


# ── 모멘텀 국면 ────────────────────────────────────────────────────────────────

def calc_regime(spx_hist, ndx_hist) -> dict:
    spx_close = latest_close(spx_hist)
    spx_ma50 = ma(spx_hist, 50)
    spx_ma200 = ma(spx_hist, 200)

    ndx_close = latest_close(ndx_hist)
    ndx_ma50 = ma(ndx_hist, 50)
    ndx_ma200 = ma(ndx_hist, 200)

    spx_above = spx_close > spx_ma200 and spx_ma50 > spx_ma200
    ndx_above = ndx_close > ndx_ma200 and ndx_ma50 > ndx_ma200
    spx_break = spx_close < spx_ma200
    ndx_break = ndx_close < ndx_ma200

    if spx_above and ndx_above:
        regime = "GREEN"
    elif spx_break or ndx_break:
        regime = "RED"
    else:
        regime = "YELLOW"

    return {
        "regime": regime,
        "spx": {"close": round(spx_close, 2), "ma50": round(spx_ma50, 2), "ma200": round(spx_ma200, 2)},
        "ndx": {"close": round(ndx_close, 2), "ma50": round(ndx_ma50, 2), "ma200": round(ndx_ma200, 2)},
        "buy_gate": "OPEN" if regime != "RED" else "BLOCKED",
    }


# ── mcap 순위 (companiesmarketcap.com 스크래핑) ───────────────────────────────

def scrape_top_companies(n: int = 30) -> list:
    """companiesmarketcap.com 메인 페이지에서 상위 n개 기업 스크래핑."""
    url = "https://companiesmarketcap.com/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="replace")
    pattern = (
        r'company-logo[^>]+src="/img/company-logos/64/([^"]+?)\.png"'
        r'.*?company-name">([^<]+)</div>'
        r'<div class="company-code"><span[^>]+></span>([^<]+)</div>'
        r'.*?data-sort="(\d+)"'
    )
    matches = re.findall(pattern, html, re.DOTALL)
    result = []
    for slug, name, ticker_display, mcap_str in matches[:n]:
        ticker_display = ticker_display.strip()
        yf_ticker = YFINANCE_OVERRIDE.get(ticker_display, ticker_display)
        result.append({
            "slug": slug.strip(),
            "name": name.strip(),
            "ticker": yf_ticker,
            "ticker_display": ticker_display,
            "mcap_usd": int(mcap_str),
        })
    return result


def fetch_mcap_rankings() -> tuple:
    """(전체 순위 리스트, 투자가능 1등주 yf_ticker) 반환"""
    scraped = scrape_top_companies(30)
    if not scraped:
        raise RuntimeError("companiesmarketcap.com 스크래핑 실패")

    rank1_mcap = scraped[0]["mcap_usd"] if scraped else 1
    investable = [r for r in scraped if _is_investable(r["ticker"])]
    rank1_investable = investable[0]["ticker"] if investable else scraped[0]["ticker"]

    results = []
    for i, item in enumerate(scraped):
        gap = (rank1_mcap - item["mcap_usd"]) / rank1_mcap * 100 if rank1_mcap > 0 else 0
        results.append({
            "rank": i + 1,
            "ticker": item["ticker"],
            "ticker_display": item["ticker_display"],
            "slug": item["slug"],
            "name": item["name"],
            "mcap_usd": item["mcap_usd"],
            "is_leader": item["ticker"] == rank1_investable,
            "gap_pct_from_rank1": round(gap, 1),
        })

    return results, rank1_investable


# ── 헤지 가격 ─────────────────────────────────────────────────────────────────

def fetch_hedge_prices() -> dict:
    prices = {}
    for ticker in HEDGE_TICKERS:
        try:
            hist = yf.Ticker(ticker).history(period="5d", auto_adjust=True)
            price = float(hist["Close"].iloc[-1])
            prices[ticker] = round(price, 2) if not math.isnan(price) else None
        except Exception:
            prices[ticker] = None
    return prices


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    today = date.today()
    print(f"\n[EOD 배치] {today}")

    # 1. 시장 가격 조회
    print("▶ 시장 가격 조회 중...")
    ixic = fetch_history("^IXIC")
    gspc = fetch_history("^GSPC")
    ndx  = fetch_history("^NDX")
    qqq  = fetch_history("QQQ")
    vix  = fetch_history("^VIX", period="30d")

    ixic_close = require_valid("IXIC 종가", latest_close(ixic))
    ixic_chg   = require_valid("IXIC 등락률", daily_change_pct(ixic))
    ixic_ath   = require_valid("IXIC ATH", float(yf.Ticker("^IXIC").history(period="max", auto_adjust=False)["Close"].max()))
    ixic_ma200 = ma(ixic, 200)
    consec_up  = consecutive_up_days(ixic)
    vix_val    = round(latest_close(vix), 2)

    print(f"  IXIC: {ixic_close:.2f} ({ixic_chg:+.2f}%)")
    print(f"  VIX:  {vix_val}")

    # 2. 기존 masam.json 로드 + FRED 값은 masam_market.json에서 읽음 (fetch_fred.py가 먼저 실행)
    existing_masam = load_json(DATA / "masam.json")
    fred = load_json(DATA / "masam_market.json")
    rate_env  = fred.get("rate_env",           existing_masam.get("rate_env", "NON_ZERO"))
    qe_active = fred.get("qe_active",          existing_masam.get("qe_active", False))
    t10_trend = fred.get("treasury_10y_trend", existing_masam.get("treasury_10y_trend", "UNKNOWN"))
    dff_trend = fred.get("dff_trend",          "UNKNOWN")

    # 3. 마삼 상태 업데이트
    prev_mode = existing_masam.get("mode", "NORMAL")
    new_masam_state, new_mode = update_masam_state(existing_masam, today, ixic_chg)
    print(f"  모드: {prev_mode} → {new_mode}  (이번 달 마삼 {new_masam_state['month_count']}회)")

    # 위기/공황 → 평상시 전환 당일 기록
    released_date = existing_masam.get("released_date")
    _is_crisis_release = prev_mode in ("CRISIS", "PANIC") and new_mode == "NORMAL"
    if _is_crisis_release:
        released_date = today.isoformat()

    # 4. mcap 순위 (투자가능 + 비USD 표시용)
    print("▶ 시가총액 순위 조회 중...")
    rankings, rank1_investable = fetch_mcap_rankings()
    # 전략 기준 1·2등주: 투자 가능 종목 중에서
    investable_ranked = [r for r in rankings if _is_investable(r["ticker"])]
    rank1_ticker = investable_ranked[0]["ticker"] if investable_ranked else "NVDA"
    rank2_ticker = investable_ranked[1]["ticker"] if len(investable_ranked) > 1 else "MSFT"
    gap_pct = investable_ranked[1].get("gap_pct_from_rank1", 0.0) if len(investable_ranked) > 1 else 0.0
    print(f"  1등: {rank1_ticker}  2등: {rank2_ticker}  격차: {gap_pct:.1f}%")

    # 5. 1등주·2등주 가격
    rank1_hist = fetch_history(rank1_ticker)
    rank2_hist = fetch_history(rank2_ticker)
    rank1_close = require_valid(f"{rank1_ticker} 종가", latest_close(rank1_hist))
    rank2_close = require_valid(f"{rank2_ticker} 종가", latest_close(rank2_hist))
    rank1_ath   = require_valid(f"{rank1_ticker} ATH", float(yf.Ticker(rank1_ticker).history(period="max", auto_adjust=False)["Close"].max()))
    qqq_eod_close = require_valid("QQQ 종가", latest_close(qqq))

    # 5b/5c. 올인 기준가·직전 고점·리밸런싱 저점: "슬롯"(1등주/2등주)이 아니라
    # 티커 심볼(by_ticker) 단위로 추적한다.
    # ponytail: 슬롯 기준으로 저장하면 순위가 바뀔 때마다 새로 들어온 티커에 이전 점유자의
    # 값이 잘못 매칭되는 사고가 반복됨(2026-07-28, 2026-08-01 확인) — 종목 자신의 이력을
    # 순위 이동과 무관하게 이어가도록 by_ticker로 저장하고, nvda/qqq/rank2 필드는 매 배치
    # 현재 순위 기준으로 파생만 함(프론트 호환용).
    last_allin_price = existing_masam.get("last_allin_price")
    existing_reb = existing_masam.get("rebalancing", {})
    # 재매수 리셋 판정 그리드: 티커별 독립(25→2.5%, 50→5%). 프론트의 max_pct_{target}
    # localStorage 토글과 별개(서버는 기기별 설정을 알 수 없음) — masam.json을 소스로 삼아
    # 필요 시 수동 조정. 과거엔 단일 rebalancing.max_pct 하나로 전 종목을 판정해서, 종목별로
    # 프론트 그리드를 다르게 설정해도 리셋 시점이 안 맞는 문제가 있었음(2026-08-04 확인).
    _max_pct_by_ticker = existing_reb.get("max_pct_by_ticker", {})
    # 신규 티커 기본 그리드: 프론트(initMaxPctUI)와 동일하게 금리환경 기반(제로=25%/비제로=50%).
    # max_pct_by_ticker에 명시적으로 저장된 값이 있으면 그게 우선(수동 조정 반영).
    _default_max_pct = 25 if rate_env == "ZERO" else 50

    def _step_of(ticker: str) -> float:
        return _max_pct_by_ticker.get(ticker, _default_max_pct) / 1000

    if _is_crisis_release:
        _t = today.isoformat()
        last_allin_price = {
            "date": _t,
            "by_ticker": {
                rank1_ticker: {"allin": round(rank1_close, 2),     "prev_high": round(rank1_close, 2),     "lowest_close": round(rank1_close, 2),   "since": _t},
                rank2_ticker: {"allin": round(rank2_close, 2),     "prev_high": round(rank2_close, 2),     "lowest_close": round(rank2_close, 2),   "since": _t},
                "QQQ":        {"allin": round(qqq_eod_close, 2),   "prev_high": round(qqq_eod_close, 2),   "lowest_close": round(qqq_eod_close, 2), "since": _t},
            },
        }
        print(f"  올인 기준가: {rank1_ticker}={rank1_close:.2f} QQQ={qqq_eod_close:.2f} {rank2_ticker}={rank2_close:.2f} ({today})")

    def _base_of(cur, allin, prev_high):
        return prev_high if (allin > 0 and cur >= allin) else allin

    def _zone_idx(cur, base, step):
        if not cur or not base: return 0
        z = 0
        for i in range(1, 11):
            if cur <= base * (1 - step * i): z = i
        return z

    def _update_ticker(by_ticker: dict, ticker: str, close: float, hist, today_iso: str):
        """티커별 진입가/직전고점/저점 스티키를 자기 자신의 이력으로만 갱신(순위 무관).
        직전고점은 매 배치 해당 티커 자신의 전체 히스토리(자기 since일 이후)로 재계산해
        배치가 하루 이틀 빠지더라도 스스로 정정됨.
        구간 그리드는 티커별 독립(max_pct_by_ticker) — 종목마다 리셋 시점이 달라짐.
        반환값: (entry, zone_reach, reset_from_zone, step_pct) — zone_reach는 오늘 새로 도달한
        최심 구간(신기록일 때만 정수, 아니면 None). reset_from_zone은 오늘 실제 재매수
        (reached_recovery)로 리셋되면서 벗어난 구간(0구간에서의 리셋은 알림 의미 없어 제외)"""
        step = _step_of(ticker)
        close = round(close, 2)
        entry = by_ticker.get(ticker)
        if not entry:
            # 처음 추적하는 종목(신규 1·2등 진입) — 오늘 종가로 새로 시작
            entry = {"allin": close, "prev_high": close, "lowest_close": close, "since": today_iso}
            by_ticker[ticker] = entry
            return entry, None, None, step * 100
        since_date = entry.get("since") or today_iso
        old_high = entry.get("prev_high", entry.get("allin", close))
        try:
            since_series = hist.loc[since_date:, "Close"]
            new_high = round(float(since_series.max()), 2) if not since_series.empty else max(old_high, close)
        except Exception:
            new_high = max(old_high, close)
        new_peak = new_high > old_high
        base = _base_of(close, entry.get("allin", 0), new_high)
        prev_low = entry.get("lowest_close", 0)
        prev_zone = _zone_idx(prev_low, base, step)
        # 저점 리셋 조건: (1) 막바지 2구간 상승 → 전량 재매수, (2) 오늘 전고점을 새로 경신
        # (2)가 없으면 전고점 갱신 후에도 그 전고점에 도달하기 전의 옛 저점이 그대로 남아
        # "전고점 대비 N구간 하락"으로 잘못 계산되는 버그가 생김 — 2026-07-31 확인
        # (1)의 "2구간 상승"은 구간 번호(new_zone <= prev_zone-2) 비교가 아니라 표에 적힌
        # 목표 구간의 실제 가격에 도달했는지로 판정해야 함 — zone_idx는 "zone1 문턱만 넘으면
        # 전부 0구간"으로 뭉뚱그려서, 기준가(전고점) 자체엔 못 미쳤는데도 리셋되는 버그가
        # 있었음(2026-08-04 확인). 목표 구간 가격 = base*(1-step*(prev_zone-2))
        target_zone = prev_zone - 2
        recovery_price = base * (1 - step * target_zone)
        reached_recovery = prev_zone >= 2 and close >= recovery_price
        # new_peak만으로 저점을 리셋하는 건 prev_zone==0(추적 중인 하락이 아예 없던 경우)일
        # 때만 안전함 — 무해한 리셋(잃을 정보가 없음). prev_zone>=2일 땐 새 고점이 서면
        # recovery_price(=새 고점 자체)를 항상 자명하게 만족해 reached_recovery도 함께
        # True가 되므로 이 분기는 실질적으로 관여하지 않음(기존 문서화된 정상 동작).
        # 문제는 prev_zone==1: 2구간 하락에 못 미쳐 reached_recovery는 구조적으로 항상
        # False인데, 그 상태에서 직전 고점(prev_high, since-윈도우 국지적 최고가)을 살짝만
        # 넘는 신고가가 나와도 new_peak이 발동해 "1구간 하락 → 완전 회복"으로 잘못
        # 리셋됨(매뉴얼상 재매수는 "막바지 2구간 상승"만이 트리거, 신고가 경신이 아님 —
        # 2026-08-29 확인). 이 경우엔 저점을 건드리지 않고 prev_high만 갱신(무조건 실행,
        # 아래 506행)해서 구간이 1로 유지되도록 함.
        is_reset = reached_recovery or (new_peak and prev_zone == 0)
        if is_reset:
            new_low = close
            # allin(올인 지점 기준가) 갱신은 reached_recovery(2구간 하락 후 실제 재매수)일 때만.
            # new_peak(단순 신고가 경신)까지 여기 묶으면 prev_high도 매 신고가마다 같이
            # 갱신되는 필드라서, 신고가를 찍을 때마다 올인 지점=직전 고점이 같은 값으로
            # 붕괴해 두 탭이 항상 동일하게 표시되는 버그가 생김(2026-08-06 확인).
            if reached_recovery:
                entry["allin"] = close
                # since도 같이 리셋. 안 그러면 prev_high가 이번 재매수 이전(붕괴 전 옛
                # 전고점) 히스토리를 계속 포함해서, 재매수 직후에도 prevHigh가 새 allin
                # 보다 훨씬 높게 남아있게 되고, 프론트 자동전환(prevHigh > allin)이 재매수
                # 직후부터 곧장 "직전 고점"으로 넘어가버려 사실상 매 사이클 무력화됨
                # (2026-08-10 확인 — 이래서 프론트가 대신 eodClose > allin으로 비교하도록
                # 바뀌어 있었는데, 그건 "신고가 찍고 눌림" 케이스에서 직전고점 유지가 안 되는
                # 또 다른 버그였음. since를 재매수 시점으로 리셋하면 두 요구사항이 동시에
                # 성립해서 프론트도 prevHigh > allin으로 되돌릴 수 있음)
                entry["since"] = today_iso
                new_high = close
        else:
            new_low = min(prev_low, close) if prev_low else close
        # 구간 도달 알림: 리셋이 아니면서 이전보다 더 깊은 구간에 새로 도달했을 때만 기록
        zone_reach = None
        if not is_reset and new_low < prev_low:
            deepest_zone = _zone_idx(new_low, base, step)
            if deepest_zone > prev_zone:
                zone_reach = deepest_zone
        # 구간 회복(전량 재매수) 알림: 실제 재매수(reached_recovery)로 리셋되면서 현금을
        # 확보하고 있던 구간(>0)을 벗어났을 때만 기록. 권장 비중 %는 기기별 portfolio_ratio에
        # 의존해 서버가 계산 못 하지만, "구간이 회복됐다"는 사실 자체는 서버가 계산 가능한데도
        # 기존엔 zone_reach(하락 방향)만 기록하고 회복 방향 이벤트가 없어서, 이 이벤트를 놓친
        # 기기(특히 이 전환을 직접 겪지 못하고 이미 회복된 뒤에 처음 접속한 기기)는 권장 비중
        # 변경 히스토리에서 이 전환을 영영 볼 수 없었음 (2026-08-06 확인)
        reset_from_zone = prev_zone if (reached_recovery and prev_zone > 0) else None
        entry["prev_high"] = new_high
        entry["lowest_close"] = new_low
        return entry, zone_reach, reset_from_zone, step * 100

    # 알림 히스토리 이벤트(마삼 전환·순위 역전·구간 도달) — 최근 30일 보관
    # ponytail: 서버가 계산 가능한 이벤트만 기록. 권장 비중은 기기별 localStorage
    # 설정에 의존해 서버가 재현 불가 → 프론트(app.html)가 클라이언트에서 별도 기록.
    notif_events = []

    if new_mode == "NORMAL" and isinstance(last_allin_price, dict) and "by_ticker" in last_allin_price:
        by_ticker = last_allin_price["by_ticker"]
        _today_iso = today.isoformat()
        nvda_entry,  nvda_zone,  nvda_reset,  nvda_step_pct  = _update_ticker(by_ticker, rank1_ticker, rank1_close,   rank1_hist, _today_iso)
        rank2_entry, rank2_zone, rank2_reset, rank2_step_pct = _update_ticker(by_ticker, rank2_ticker, rank2_close,   rank2_hist, _today_iso)
        qqq_entry,   qqq_zone,   qqq_reset,   qqq_step_pct   = _update_ticker(by_ticker, "QQQ",        qqq_eod_close, qqq,        _today_iso)
        # 오늘 1등인 티커는 "1등 해본 적 있음"으로 마킹 — 격차 10% 이내라는 이유만으로
        # 한 번도 1등을 탈환한 적 없는 2등주가 권장 비중(1:1 배분)에 잡히는 걸 막기 위함
        # (2026-08-04 확인: gap_within_10pct만으로는 부족, 실제 추월 이력이 있어야 함)
        nvda_entry["ever_rank1"] = True
        # (2026-08-27 확인) 이 마킹은 영구가 아니라 "직전 역전 이후" 한정이어야 함 —
        # 격차가 10%를 다시 넘어서면 2등주의 1등 이력은 리셋된다(사용자 확인). 안 그러면
        # 예전에 잠깐 1등이었던 종목이 한참 뒤 격차만 우연히 좁혀져도 1:1 배분에 잡힘.
        if gap_pct > 10.0:
            rank2_entry["ever_rank1"] = False
        # 레거시 슬롯 필드는 현재 순위 기준으로 매 배치 파생(프론트가 nvda/qqq/rank2 키를 그대로 씀)
        last_allin_price["nvda"]             = nvda_entry["allin"]
        last_allin_price["nvda_prev_high"]   = nvda_entry["prev_high"]
        last_allin_price["rank2"]            = rank2_entry["allin"]
        last_allin_price["rank2_prev_high"]  = rank2_entry["prev_high"]
        last_allin_price["qqq"]              = qqq_entry["allin"]
        last_allin_price["qqq_prev_high"]    = qqq_entry["prev_high"]
        new_nvda_low  = nvda_entry["lowest_close"]
        new_rank2_low = rank2_entry["lowest_close"]
        new_qqq_low   = qqq_entry["lowest_close"]
        print(f"  직전 고점: {rank1_ticker}={nvda_entry['prev_high']} QQQ={qqq_entry['prev_high']} {rank2_ticker}={rank2_entry['prev_high']}")
        print(f"  리밸런싱 저점: {rank1_ticker}={new_nvda_low}  QQQ={new_qqq_low}  {rank2_ticker}={new_rank2_low}")
        for _label, _zone, _reset, _step_pct in (
            (rank1_ticker, nvda_zone, nvda_reset, nvda_step_pct),
            ("QQQ", qqq_zone, qqq_reset, qqq_step_pct),
            (rank2_ticker, rank2_zone, rank2_reset, rank2_step_pct),
        ):
            if _zone:
                notif_events.append({
                    "date": today.isoformat(),
                    "type": "zone_reach",
                    "text": f"{_label} 직전고점 대비 {_zone}구간({_step_pct * _zone:.1f}%) 하락 도달",
                })
            if _reset:
                notif_events.append({
                    "date": today.isoformat(),
                    "type": "zone_reset",
                    "text": f"{_label} 구간 회복 — {_reset}구간→0구간 (전량 재매수)",
                })
    else:
        new_nvda_low = 0
        new_qqq_low = 0
        new_rank2_low = 0

    # 위기 저점: 마지막 마삼일 이후 최저 종가 (V자 반등 기준점)
    last_masam_str = new_masam_state.get("last_masam_date")
    if last_masam_str:
        ixic_since = ixic.loc[last_masam_str:, "Close"]
        ixic_crisis_low = float(ixic_since.min()) if not ixic_since.empty else ixic_close
    else:
        ixic_crisis_low = ixic_close

    # 6. 헤지
    print("▶ 헤지 가격 조회 중...")
    hedge_prices = fetch_hedge_prices()
    print(f"  {hedge_prices}")

    # 7. 모멘텀 국면
    print("▶ 모멘텀 국면 계산 중...")
    regime_data = calc_regime(gspc, ndx)
    print(f"  국면: {regime_data['regime']}")

    # 7b. 시장 심리 (NDX vs MA200)
    ndx_close  = regime_data["ndx"]["close"]
    ndx_ma200  = regime_data["ndx"]["ma200"]
    ndx_pct    = round((ndx_close - ndx_ma200) / ndx_ma200 * 100, 1) if ndx_ma200 else 0
    market_sentiment = "위험선호" if ndx_pct > 2 else ("위험회피" if ndx_pct < -2 else "중립")
    spy_ma200_label  = f"MA200 ({ndx_pct:+.1f}%)"

    # 8. 비중 / 헤지 타입
    target_alloc = calc_target_allocation(new_mode, rate_env)
    hedge_alloc  = calc_hedge_type(rate_env, qe_active, t10_trend, dff_trend)
    if new_mode == "NORMAL":
        hedge_alloc = {"type": "NONE", "rationale": "평상시 — 헤지 불필요", "exit_trigger": ""}

    # 9. 올인 체크리스트
    all_in = calc_all_in_conditions(
        mode=new_mode,
        last_masam=date.fromisoformat(new_masam_state["last_masam_date"]) if new_masam_state.get("last_masam_date") else None,
        today=today,
        consec_up=consec_up,
        ixic_close=ixic_close,
        ixic_ath=ixic_ath,
        rank1_close=rank1_close,
        rank1_ath=rank1_ath,
        ixic_crisis_low=ixic_crisis_low,
        rate_env=rate_env,
    )


    # ── 파일 저장 ──────────────────────────────────────────────────────────────

    # masam.json
    masam_out = {
        **existing_masam,
        "as_of": today.isoformat(),
        "mode": new_mode,
        "rate_env": rate_env,
        "qe_active": qe_active,
        "treasury_10y_trend": t10_trend,
        "masam": new_masam_state,
        "leader_status": {
            "rank1_ticker": rank1_ticker,
            "rank2_ticker": rank2_ticker,
            "gap_pct": gap_pct,
            "overtake_detected": existing_masam.get("leader_status", {}).get("rank1_ticker") != rank1_ticker,
            "gap_within_10pct": gap_pct <= 10.0,
            # 2등주가 격차 10% 이내로 들어와도, 실제로 1등을 해본 적 없으면 권장 비중
            # 1:1 배분 대상이 아님(프론트에서 dualLeader 판정에 사용)
            "rank2_ever_rank1": bool((last_allin_price or {}).get("by_ticker", {}).get(rank2_ticker, {}).get("ever_rank1", False)),
        },
        "target_allocation": target_alloc,
        "hedge_allocation": hedge_alloc,
        "all_in_conditions": all_in,
        "rebalancing": {
            "cash_raised_pct":    existing_reb.get("cash_raised_pct", 0),
            "max_pct":            existing_reb.get("max_pct", 25),  # 신규 티커 기본값(폴백)으로만 사용
            "max_pct_by_ticker":  {
                **_max_pct_by_ticker,
                rank1_ticker: _max_pct_by_ticker.get(rank1_ticker, _default_max_pct),
                rank2_ticker: _max_pct_by_ticker.get(rank2_ticker, _default_max_pct),
                "QQQ":        _max_pct_by_ticker.get("QQQ", _default_max_pct),
            },
            "qqq_pct":            existing_reb.get("qqq_pct", 0),
            "nvda_lowest_close":  round(new_nvda_low, 2) if new_nvda_low else 0,
            "qqq_lowest_close":   round(new_qqq_low, 2) if new_qqq_low else 0,
            "rank2_lowest_close": round(new_rank2_low, 2) if new_rank2_low else 0,
        },
        "eod_close": {
            "nvda":  round(rank1_close, 2),
            "qqq":   round(qqq_eod_close, 2),
            "rank2": round(rank2_close, 2),
        },
        "released_date": released_date,
        "last_allin_price": last_allin_price,
        "recommended_action": _recommended_action(new_mode, rank1_ticker),
    }
    save_json(DATA / "masam.json", masam_out)

    # 10. 알림 히스토리: 마삼 모드 전환·시총 순위 역전 기록 (최근 30일 유지)
    if prev_mode != new_mode:
        notif_events.append({
            "date": today.isoformat(),
            "type": "masam_mode",
            "text": f"{prev_mode} → {new_mode} 전환",
        })
    prev_rank1 = existing_masam.get("leader_status", {}).get("rank1_ticker")
    if prev_rank1 and prev_rank1 != rank1_ticker:
        notif_events.append({
            "date": today.isoformat(),
            "type": "leader_swap",
            "text": f"1등주가 {prev_rank1} → {rank1_ticker}로 바뀌었습니다",
        })
    prev_rank2 = existing_masam.get("leader_status", {}).get("rank2_ticker")
    if prev_rank2 and prev_rank2 != rank2_ticker:
        notif_events.append({
            "date": today.isoformat(),
            "type": "rank2_swap",
            "text": f"2등주가 {prev_rank2} → {rank2_ticker}로 바뀌었습니다",
        })
    if notif_events:
        notifications = load_json(DATA / "notifications.json")
        if not isinstance(notifications, list):
            notifications = []
        notifications.extend(notif_events)
        cutoff = (today - timedelta(days=30)).isoformat()
        notifications = [n for n in notifications if n.get("date", "") >= cutoff]
        save_json(DATA / "notifications.json", notifications)
        print(f"  알림 기록: {len(notif_events)}건 추가 (보관 {len(notifications)}건)")

    # mcap_daily.json — 상위 25개 저장 (표시는 20개, 버퍼 5개)
    save_json(DATA / "mcap_daily.json", {
        "as_of": today.isoformat(),
        "rank1_ticker": rank1_ticker,
        "items": rankings[:25],
    })

    # momentum_market.json (VIX 추가, FRED 필드 유지)
    existing_mm = load_json(DATA / "momentum_market.json")
    save_json(DATA / "momentum_market.json", {
        **existing_mm,
        "as_of": today.isoformat(),
        **regime_data,
        "vix": vix_val,
    })

    # masam_market.json — FRED 필드는 fetch_fred.py가 담당, VIX·시장심리만 갱신
    existing_fm = load_json(DATA / "masam_market.json")
    vix_closes = vix["Close"].tail(60).tolist()
    vix_history = [round(float(v), 2) for v in vix_closes]
    # 3단계(2026-08-21): 다른 매크로 카드와 동일하게 VIX도 20영업일 변화량 추가
    vix_chg_20d = round(vix_closes[-1] - vix_closes[-21], 2) if len(vix_closes) >= 21 else None
    vix_chg_dir = None
    if vix_chg_20d is not None:
        vix_chg_dir = "UP" if vix_chg_20d > 0 else "DOWN" if vix_chg_20d < 0 else "FLAT"
    save_json(DATA / "masam_market.json", {
        **existing_fm,
        "vix": vix_val,
        "vix_chg_20d": vix_chg_20d,
        "vix_chg_dir": vix_chg_dir,
        "market_sentiment": market_sentiment,
        "spy_ma200_label": spy_ma200_label,
        "history": {**existing_fm.get("history", {}), "vix": vix_history},
    })

    # hedge_prices.json
    save_json(DATA / "hedge_prices.json", {
        "as_of": today.isoformat(),
        **hedge_prices,
    })

    print(f"\n✓ EOD 배치 완료 ({today})")


def _recommended_action(mode: str, rank1: str) -> str:
    if mode == "NORMAL":
        return f"리밸런싱 유지 — 1등주({rank1}) 집중"
    elif mode == "CRISIS":
        return f"말뚝박기 유지 — 하락 시 분할 매수"
    else:
        return "현금 100% 대기 — 올인 트리거 모니터링"


if __name__ == "__main__":
    main()
