"""
EOD 배치 스크립트 — 미 장마감 후 1일 1회 실행
출력: masam.json, mcap_daily.json, momentum_market.json, masam_market.json(VIX)
"""
import json
import sys
import re
import calendar
import urllib.request
from datetime import date, timedelta
from pathlib import Path
import yfinance as yf

DATA = Path(__file__).parent.parent / "app/public/data"

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
            prices[ticker] = round(float(hist["Close"].iloc[-1]), 2)
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
    vix  = fetch_history("^VIX", period="5d")

    ixic_close = latest_close(ixic)
    ixic_chg   = daily_change_pct(ixic)
    ixic_ath   = float(yf.Ticker("^IXIC").history(period="max", auto_adjust=False)["Close"].max())
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

    # 5. 1등주 가격
    rank1_hist = fetch_history(rank1_ticker)
    rank1_close = latest_close(rank1_hist)
    rank1_ath   = float(yf.Ticker(rank1_ticker).history(period="max", auto_adjust=False)["Close"].max())

    # 5b. 올인 기준가: 위기→평상시 전환 시 기준일 종가 저장
    # ponytail: 전환일 당일 종가만 사용. 스크립트가 당일을 놓쳤다면 masam.json을 수동 패치
    last_allin_price = existing_masam.get("last_allin_price")
    if _is_crisis_release:
        qqq_close = latest_close(qqq)
        last_allin_price = {
            "nvda": round(rank1_close, 2),
            "qqq":  round(qqq_close, 2),
            "date": today.isoformat(),
        }
        print(f"  올인 기준가: NVDA={last_allin_price['nvda']} QQQ={last_allin_price['qqq']} ({today})")

    # NORMAL 모드에서 매 실행 시 올인 이후 최고 종가(직전 고점) 갱신
    if new_mode == "NORMAL" and isinstance(last_allin_price, dict) and last_allin_price.get("date"):
        allin_date_str = last_allin_price["date"]
        try:
            r1_since = rank1_hist.loc[allin_date_str:, "Close"]
            last_allin_price["nvda_prev_high"] = round(float(r1_since.max()), 2) if not r1_since.empty else last_allin_price["nvda"]
        except Exception:
            last_allin_price["nvda_prev_high"] = last_allin_price.get("nvda_prev_high", last_allin_price["nvda"])
        try:
            qqq_since = qqq.loc[allin_date_str:, "Close"]
            last_allin_price["qqq_prev_high"] = round(float(qqq_since.max()), 2) if not qqq_since.empty else last_allin_price["qqq"]
        except Exception:
            last_allin_price["qqq_prev_high"] = last_allin_price.get("qqq_prev_high", last_allin_price["qqq"])
        print(f"  직전 고점: NVDA={last_allin_price['nvda_prev_high']} QQQ={last_allin_price['qqq_prev_high']}")

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
        },
        "target_allocation": target_alloc,
        "hedge_allocation": hedge_alloc,
        "all_in_conditions": all_in,
        "released_date": released_date,
        "last_allin_price": last_allin_price,
        "recommended_action": _recommended_action(new_mode, rank1_ticker),
    }
    save_json(DATA / "masam.json", masam_out)

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
    save_json(DATA / "masam_market.json", {
        **existing_fm,
        "vix": vix_val,
        "market_sentiment": market_sentiment,
        "spy_ma200_label": spy_ma200_label,
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
