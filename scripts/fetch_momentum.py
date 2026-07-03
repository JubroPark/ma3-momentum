"""
모멘텀 종목 데이터 배치 — EOD 후 실행
출력: indicators.json, positions.json (지표 갱신)

자동 계산:
  - MA50 / MA200 / ATR14
  - vol20ma / vol_ratio (당일 거래량 / 20일 평균)
  - recent_high (보유 중 비감소 최고가)
  - trailing_stop_line (hybrid: clamp(max(0.20, ATR×5), 0.15, 0.30))
  - gap50_pct / dist_to_stop_pct
  - next_action (HOLD / BUY_2 / BUY_3 / TRIM_HALF / EXIT)
  - toppick_score (growth×0.30 + moat×0.30 + earnings×0.20 + health×0.20)
    - growth_score     : revenueGrowth + earningsGrowth (yfinance)
    - earnings_score   : EPS방향(forwardEps/trailingEps) + 분기이익성장
    - health_score     : FCF마진 + 영업이익률 + ROE
    - moat_score       : 수동 유지 (positions.json의 moat_score 필드)

수동 유지:
  - avg_price / weight / deployed_tranches / cooldown_until
  - horizontal_support (자동 탐색 fallback: 52주 저점)
  - status (매수 판단은 사용자 확정 원칙)

universe.json 연동 (fetch_universe.py 실행 후):
  - score ≥ 70 신규 종목 → WATCH 자동 편입 (최대 30개)
  - WATCH 종목이 score < 60으로 하락 → REMOVED
  - ENTRY_1/2/3, TRIM, EXIT 종목은 절대 건드리지 않음
"""
import json
import requests
from datetime import date
from pathlib import Path
from typing import Optional

import yfinance as yf

_NAVER_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; universe-screener/1.0)"}


def website_to_domain(url: str) -> str:
    if not url:
        return ""
    host = url.split("//")[-1].split("/")[0]
    return host.lstrip("www.")


def get_ko_name(symbol: str) -> str:
    """네이버 금융 내부 API로 한국어 종목명 조회.
    .O(NASDAQ) → .K(NYSE 일부) → 접미사 없음 순으로 시도."""
    for naver_sym in (f"{symbol}.O", f"{symbol}.K", symbol):
        try:
            r = requests.get(
                f"https://api.stock.naver.com/stock/{naver_sym}/basic",
                headers=_NAVER_HEADERS, timeout=5,
            )
            if r.status_code == 200:
                name = r.json().get("stockName") or ""
                if name:
                    return name
        except Exception:
            pass
    return ""

DATA = Path(__file__).parent.parent / "app/public/data"

TRAIL_MIN = 0.15
TRAIL_MAX = 0.30
TRAIL_DEFAULT = 0.20
ATR_MULT = 5.0
ENTRY2_BAND = 0.03   # MA50 ±3% = 2차 줍줍 구간
SUPPORT_BAND = 0.03  # 지지선 ±3% 근접 판단

# 3분할 줍줍 비중 (전략 문서 기본값)
TRANCHE_WEIGHTS = {1: 0.30, 2: 0.40, 3: 0.20}

# 과열 판단 기준 (MA50 이격)
OVERHEAT_WARN  = 50.0   # +50% 이상 → 일부 현금화 검토
OVERHEAT_STRONG = 80.0  # +80% 이상 → 차익 실현 권장


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장: {path.name}")


# ── toppick 스코어링 ──────────────────────────────────────────────────────────

def _safe(info: dict, key: str, default=None):
    v = info.get(key)
    return default if v is None else v


def calc_growth_score(info: dict) -> float:
    """매출성장률 + 이익성장률 평균 → 0~5"""
    rev = _safe(info, "revenueGrowth", 0.0)
    earn = _safe(info, "earningsGrowth", 0.0)

    # GAAP 일회성 비용·SBC·상각으로 earningsGrowth가 왜곡되는 경우 방어:
    # trailing EPS가 양수이고 forward EPS가 크게 높으면 forward 성장률로 대체
    trailing_eps = _safe(info, "trailingEps", 0.0)
    forward_eps  = _safe(info, "forwardEps",  0.0)
    if earn <= -0.5 and trailing_eps > 0 and forward_eps > trailing_eps:
        earn = (forward_eps - trailing_eps) / trailing_eps
    elif (info.get('earningsGrowth') is None) and abs(trailing_eps) < 0.5 and forward_eps > 1.0:
        earn = forward_eps

    def score_rev(r):
        if r > 0.50: return 5.0
        if r > 0.30: return 4.0
        if r > 0.15: return 3.0
        if r > 0.05: return 2.0
        if r > 0.00: return 1.0
        return 0.0

    def score_earn(e):
        if e > 1.00: return 5.0
        if e > 0.50: return 4.0
        if e > 0.20: return 3.0
        if e > 0.05: return 2.0
        if e > 0.00: return 1.0
        return 0.0

    return round((score_rev(rev) + score_earn(earn)) / 2, 2)


def calc_financial_health(info: dict) -> float:
    """FCF마진 + 영업이익률 + ROE → 0~5 (미주은 핵심: FCF·가격결정력·ROE 지속성)"""
    fcf = _safe(info, "freeCashflow", 0)
    rev = _safe(info, "totalRevenue", 1)
    opm = _safe(info, "operatingMargins", 0.0)
    roe = _safe(info, "returnOnEquity", 0.0)

    fcf_margin = fcf / rev if rev > 0 else 0.0

    def score_fcf(m):
        if m > 0.30: return 2.0
        if m > 0.15: return 1.5
        if m > 0.05: return 1.0
        if m > 0.00: return 0.5
        return 0.0

    def score_opm(m):
        if m > 0.40: return 1.5
        if m > 0.25: return 1.0
        if m > 0.15: return 0.7
        if m > 0.00: return 0.3
        return 0.0

    def score_roe(r):
        if r > 0.50: return 1.0
        if r > 0.30: return 0.8
        if r > 0.15: return 0.5
        if r > 0.00: return 0.2
        return 0.0

    return round(min(5.0, score_fcf(fcf_margin) + score_opm(opm) + score_roe(roe)), 2)


def calc_moat_score_auto(info: dict, income_stmt=None) -> float:
    """
    해자 자동 프록시 (0~5):
      Pricing Power  (grossMargins)       → 브랜드·전환비용  0~1.5
      Scale Efficiency (OPM + ROE)        → 규모의 경제      0~1.5
      Innovation     (R&D / Revenue)      → 무형자산·IP      0~1.0
      Market Premium (P/B)                → 시장 인정 해자   0~1.0
    """
    score = 0.0

    gm = _safe(info, "grossMargins", 0)
    if gm >= 0.70:   score += 1.5
    elif gm >= 0.50: score += 1.2
    elif gm >= 0.35: score += 0.8
    elif gm >= 0.20: score += 0.4

    om  = _safe(info, "operatingMargins", 0)
    roe = _safe(info, "returnOnEquity",   0)
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
            rev = float(income_stmt.loc[rev_row].iloc[0]) if rev_row else (_safe(info, "totalRevenue", 1) or 1)
            rd_ratio = rd / rev if rev > 0 else 0
        except Exception:
            pass
    if rd_ratio >= 0.15:   score += 1.0
    elif rd_ratio >= 0.08: score += 0.6
    elif rd_ratio >= 0.03: score += 0.3

    pb = _safe(info, "priceToBook", 0) or 0
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


def calc_earnings_momentum(info: dict, eps_consistency: float = 0.0) -> float:
    """
    EPS 방향 + 분기 가속도 + EPS 꾸준한 상승 → 0~5
      EPS 방향 (forward/trailing):   0~1.5
      분기 성장 가속도:               0~1.5
      EPS 일관성 (연간 추세):         0~2.0
    """
    trailing_eps = _safe(info, "trailingEps", 0.0)
    forward_eps  = _safe(info, "forwardEps",  0.0)
    qtr_growth   = _safe(info, "earningsQuarterlyGrowth", 0.0)

    if trailing_eps and trailing_eps > 0 and forward_eps:
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


def calc_eps_revision_label(info: dict) -> str:
    """EPS 전망치 방향 → 'UP_STRONG' | 'UP' | 'NEUTRAL' | 'DOWN'"""
    trailing = _safe(info, "trailingEps", 0.0)
    forward  = _safe(info, "forwardEps",  0.0)
    qtr      = _safe(info, "earningsQuarterlyGrowth", 0.0)
    if trailing and trailing > 0 and forward:
        ratio = forward / trailing
        if ratio > 1.30 or (ratio > 1.10 and qtr > 0.20):
            return "UP_STRONG"
        elif ratio > 1.00:
            return "UP"
        else:
            return "DOWN"
    return "NEUTRAL"


def calc_peg(info: dict) -> Optional[float]:
    """PEG = trailingPE / (earningsGrowth * 100). 계산 불가 시 None."""
    pe     = _safe(info, "trailingPE", None) or _safe(info, "forwardPE", None)
    growth = _safe(info, "earningsGrowth", None)
    if pe and growth and growth > 0:
        return round(float(pe) / (float(growth) * 100), 2)
    return None


def calc_criteria_count(
    growth_score: float,
    moat_score: float,
    eps_revision: str,
    gap50_pct: float,
    vol_ratio: float,
    peg: Optional[float],
    revenue_growth: float,
) -> tuple[int, list[bool]]:
    """6단계 충족 여부 → (충족 수, [bool×6])

    ① 침투율: 매출 성장률 20%+ (초기 TAM 신호)
    ② 점유율: 해자 점수 3.5+ (시장 리더십 proxy)
    ③ 성장률·해자: growth 3.0+ AND moat 3.0+
    ④ PEG: < 2.0 (데이터 없으면 통과 가정)
    ⑤ EPS revision: UP 또는 UP_STRONG
    ⑥ 모멘텀: MA50 위(-5% 이내) AND vol_ratio 0.3+
    """
    c = [
        revenue_growth >= 0.20,
        moat_score >= 3.5,
        growth_score >= 3.0 and moat_score >= 3.0,
        peg is None or (peg > 0 and peg < 2.0),
        eps_revision in ("UP", "UP_STRONG"),
        gap50_pct > -5 and vol_ratio >= 0.3,
    ]
    return sum(c), c


def calc_toppick_score(growth: float, moat: float, earnings: float, health: float) -> int:
    """미주은 v2 가중치: growth 30% · moat 30% · earnings 30% · health 10%"""
    raw = (growth * 0.30 + moat * 0.30 + earnings * 0.30 + health * 0.10) / 5.0
    return min(100, max(0, round(raw * 100)))


# ── 지표 계산 ─────────────────────────────────────────────────────────────────

def calc_atr14(hist) -> float:
    highs  = hist["High"].values
    lows   = hist["Low"].values
    closes = hist["Close"].values
    trs = []
    for i in range(1, len(hist)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if not trs:
        return 0.0
    return float(sum(trs[-14:]) / min(len(trs[-14:]), 14))


def calc_trailing_pct(atr14: float, price: float) -> float:
    atr_pct = atr14 / price if price > 0 else 0
    raw = max(TRAIL_DEFAULT, atr_pct * ATR_MULT)
    return max(TRAIL_MIN, min(TRAIL_MAX, raw))


def detect_support(hist, current_price: float, existing: Optional[float]) -> float:
    """
    간단한 지지선 탐색:
    1. 기존 값이 유효하면 유지 (수동 입력 존중)
    2. 없으면 최근 6개월 스윙 저점 클러스터링으로 탐색
    3. Fallback: 52주 저점
    """
    if existing and existing > 0:
        return existing

    lows = hist["Low"].values
    n = min(len(lows), 126)  # 약 6개월
    recent_lows = lows[-n:]

    # 로컬 미니마 탐색 (window=5)
    swing_lows = []
    for i in range(5, len(recent_lows) - 5):
        if recent_lows[i] == min(recent_lows[i - 5:i + 6]):
            swing_lows.append(float(recent_lows[i]))

    # 현재가 아래 스윙 저점 중 가장 가까운 것
    below = [s for s in swing_lows if s < current_price * 0.99]
    if below:
        return round(max(below), 2)

    # fallback: 52주 저점
    return round(float(hist["Low"].min()), 2)


def calc_next_action(
    status: str,
    price: float,
    ma50: float,
    trailing_stop_line: Optional[float],
    horizontal_support: Optional[float],
    vol_ratio: float,
    regime: str,
    toppick_score: int,
) -> tuple:
    """(next_action, reason) 반환"""
    # RED 국면: 신규 매수 차단
    if regime == "RED" and status in ("WATCH",):
        return "HOLD", "RED 국면 — 신규 매수 차단"

    if status == "WATCH":
        if price >= ma50 and vol_ratio >= 1.30:
            return "BUY_1", f"50MA 위 돌파 + 거래량 확인 (vol_ratio {vol_ratio:.2f})"
        elif price >= ma50:
            return "HOLD", f"50MA 위이나 거래량 미확인 (vol_ratio {vol_ratio:.2f})"
        else:
            return "HOLD", f"50MA 하회 — 1차 진입 대기"

    if status == "ENTRY_1":
        gap50 = (price - ma50) / ma50
        if abs(gap50) <= ENTRY2_BAND:
            return "BUY_2", f"50MA 지지 근접 ({gap50*100:+.1f}%) — 2차 진입"
        if trailing_stop_line and price <= trailing_stop_line:
            return "TRIM_HALF", f"트레일링 스탑 터치 ({price:.2f} ≤ {trailing_stop_line:.2f})"
        return "HOLD", "1차 보유 중"

    if status == "ENTRY_2":
        if price < ma50 and horizontal_support:
            dist_support = (price - horizontal_support) / horizontal_support
            if abs(dist_support) <= SUPPORT_BAND and toppick_score >= 70:
                return "BUY_3", f"지지선 근접({dist_support*100:+.1f}%) + 탑픽점수 {toppick_score}"
        if trailing_stop_line and price <= trailing_stop_line:
            return "TRIM_HALF", f"트레일링 스탑 터치 ({price:.2f} ≤ {trailing_stop_line:.2f})"
        return "HOLD", "2차 보유 중"

    if status == "ENTRY_3":
        if trailing_stop_line and price <= trailing_stop_line:
            if horizontal_support and price < horizontal_support:
                return "EXIT", f"지지선 이탈 ({price:.2f} < {horizontal_support:.2f})"
            return "TRIM_HALF", f"트레일링 스탑 터치"
        return "HOLD", "3차 보유 중"

    if status == "TRIM":
        if trailing_stop_line and price <= trailing_stop_line:
            return "EXIT", f"2차 스탑 터치 — 청산"
        return "HOLD", "절반 축소 후 보유 중"

    return "HOLD", f"{status} 상태 유지"


# status → 기본 집행 트랜치 (명시적 deployed_tranches 없을 때 fallback)
_STATUS_TRANCHES: dict = {
    "WATCH":   [],
    "ENTRY_1": [1],
    "ENTRY_2": [1, 2],
    "ENTRY_3": [1, 2, 3],
    "TRIM":    [1, 2, 3],  # 절반 축소 전 기준; calc_weight에서 0.5 적용
    "EXIT":    [],
    "REMOVED": [],
}


def calc_weight(
    status: str,
    deployed_tranches: list,
    gap50_pct: float,
    next_action: str,
    dist_to_stop: Optional[float],
) -> tuple:
    """
    추천 비중(0~1)과 상태 메모 반환.
    deployed_tranches가 비어 있으면 status로 fallback.
    """
    tranches = deployed_tranches if deployed_tranches else _STATUS_TRANCHES.get(status, [])
    base = sum(TRANCHE_WEIGHTS.get(t, 0) for t in tranches)

    if status in ("EXIT", "REMOVED", "WATCH"):
        return 0.0, ""

    if status == "TRIM":
        base = round(base * 0.5, 3)

    # 매도/축소 신호 우선
    if next_action == "EXIT":
        return 0.0, "청산 신호 — 전량 매도"
    if next_action == "TRIM_HALF":
        note = f"트레일링 스탑 근접 — 비중 절반 축소 (dist {dist_to_stop:.1f}%)" if dist_to_stop is not None else "트레일링 스탑 근접 — 비중 절반 축소"
        return round(base * 0.5, 3), note

    # 과열 구간 조정
    if gap50_pct >= OVERHEAT_STRONG:
        return round(base * 0.4, 3), f"강한 과열 (MA50 +{gap50_pct:.0f}%) — 차익 실현 권장"
    if gap50_pct >= OVERHEAT_WARN:
        return round(base * 0.7, 3), f"과열 구간 (MA50 +{gap50_pct:.0f}%) — 일부 현금화 검토"

    return round(base, 3), ""


# next_action → status 자동 전이 테이블
_TRANSITIONS: dict = {
    # (현재 status, next_action) → (새 status, deployed_tranches 갱신)
    ("WATCH",   "BUY_1"):     ("ENTRY_1", [1]),
    ("ENTRY_1", "BUY_2"):     ("ENTRY_2", [1, 2]),
    ("ENTRY_2", "BUY_3"):     ("ENTRY_3", [1, 2, 3]),
    ("ENTRY_1", "TRIM_HALF"): ("TRIM",    None),   # None = tranches 유지
    ("ENTRY_2", "TRIM_HALF"): ("TRIM",    None),
    ("ENTRY_3", "TRIM_HALF"): ("TRIM",    None),
    ("TRIM",    "EXIT"):      ("EXIT",    []),
    ("ENTRY_1", "EXIT"):      ("EXIT",    []),
    ("ENTRY_2", "EXIT"):      ("EXIT",    []),
    ("ENTRY_3", "EXIT"):      ("EXIT",    []),
}


def auto_transition(status: str, deployed_tranches: list, next_action: str) -> tuple:
    """(new_status, new_deployed_tranches) 반환. 전이 없으면 원본 그대로."""
    key = (status, next_action)
    if key not in _TRANSITIONS:
        return status, deployed_tranches
    new_status, new_tranches = _TRANSITIONS[key]
    return new_status, (deployed_tranches if new_tranches is None else new_tranches)


# ── 메인 처리 ─────────────────────────────────────────────────────────────────

def process_symbol(item: dict, regime: str) -> tuple:
    """(updated_item, indicator_row) 반환"""
    symbol = item["symbol"]
    status = item.get("status", "WATCH")
    existing_support = item.get("horizontal_support")
    existing_recent_high = item.get("recent_high")

    print(f"  {symbol} 조회 중...")
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y", auto_adjust=True)
        if hist.empty:
            print(f"  [경고] {symbol} 데이터 없음 — 스킵")
            return item, None
    except Exception as e:
        print(f"  [경고] {symbol} 조회 실패: {e}")
        return item, None

    # 재무 데이터로 toppick_score 자동 계산
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    try:
        income_stmt = ticker.income_stmt
    except Exception:
        income_stmt = None

    # 수동 설정된 moat_score가 있으면 우선, 없으면 자동 계산
    manual_moat = item.get("moat_score")
    if manual_moat is not None and float(manual_moat) != 3.0:
        moat_score = float(manual_moat)
    else:
        moat_score = calc_moat_score_auto(info, income_stmt)

    eps_cons      = calc_eps_consistency(income_stmt)
    growth_score  = calc_growth_score(info)
    health_score  = calc_financial_health(info)
    earn_score    = calc_earnings_momentum(info, eps_cons)
    toppick_score = calc_toppick_score(growth_score, moat_score, earn_score, health_score)

    eps_revision  = calc_eps_revision_label(info)
    peg           = calc_peg(info)
    revenue_growth = _safe(info, "revenueGrowth", 0.0) or 0.0

    print(f"    탑픽: {toppick_score}점  (G={growth_score} M={moat_score} E={earn_score} H={health_score}) EPS={eps_revision} PEG={peg}")

    # REMOVED 복귀: 펀더멘털 점수가 SCORE_RECOVER 이상으로 회복되면 WATCH로 자동 복귀
    if status == "REMOVED" and toppick_score >= SCORE_RECOVER:
        print(f"    → REMOVED → WATCH 복귀 (score {toppick_score} ≥ {SCORE_RECOVER})")
        status = "WATCH"

    price   = float(hist["Close"].iloc[-1])
    closes  = hist["Close"]
    volumes = hist["Volume"]

    # MA
    ma50  = float(closes.iloc[-50:].mean()) if len(closes) >= 50 else float(closes.mean())
    ma200 = float(closes.iloc[-200:].mean()) if len(closes) >= 200 else float(closes.mean())

    # ATR14
    atr14   = calc_atr14(hist)
    atr_pct = round(atr14 / price, 4) if price > 0 else 0

    # 거래량
    vol20ma   = float(volumes.iloc[-20:].mean()) if len(volumes) >= 20 else float(volumes.mean())
    vol_today = float(volumes.iloc[-1])
    vol_ratio = round(vol_today / vol20ma, 2) if vol20ma > 0 else 0

    # recent_high: 진입 후 누적 최고가 (전략 원칙 — 진입 전 고점 미포함)
    year_high = float(closes.max())
    if status in ("ENTRY_1", "ENTRY_2", "ENTRY_3", "TRIM"):
        # 기존 기록 있으면 유지·갱신, 없으면 현재가로 시작
        recent_high = max(existing_recent_high or price, price)
    else:
        # 미보유: 52주 고점을 스탑라인 참고용으로 표시
        recent_high = year_high

    # 트레일링 스탑
    trail_pct = calc_trailing_pct(atr14, price)
    trailing_stop_line = round(recent_high * (1 - trail_pct), 2) if recent_high > 0 else None

    # 지지선
    horizontal_support = detect_support(hist, price, existing_support)

    # 파생 지표
    gap50_pct    = round((price - ma50) / ma50 * 100, 1)
    dist_to_stop = round((price - trailing_stop_line) / price * 100, 1) if trailing_stop_line else None

    # 6단계 충족
    steps_count, steps_list = calc_criteria_count(
        growth_score, moat_score, eps_revision,
        gap50_pct, vol_ratio, peg, revenue_growth,
    )

    # next_action
    next_action, reason = calc_next_action(
        status=status,
        price=price,
        ma50=ma50,
        trailing_stop_line=trailing_stop_line,
        horizontal_support=horizontal_support,
        vol_ratio=vol_ratio,
        regime=regime,
        toppick_score=toppick_score,
    )

    # 상태 자동 전이
    deployed_tranches = item.get("deployed_tranches") or []
    new_status, deployed_tranches = auto_transition(status, deployed_tranches, next_action)
    if new_status != status:
        print(f"    → 상태 전이: {status} → {new_status}  (tranches={deployed_tranches})")
        status = new_status

    # 추천 비중 자동 산출
    weight, weight_note = calc_weight(
        status=status,
        deployed_tranches=deployed_tranches,
        gap50_pct=gap50_pct,
        next_action=next_action,
        dist_to_stop=dist_to_stop,
    )

    yf_name = info.get("shortName") or info.get("longName") or item.get("name", symbol)
    name_ko = item.get("name_ko") or get_ko_name(symbol)
    domain  = item.get("domain") or website_to_domain(info.get("website", ""))

    updated_item = {
        **item,
        "name":    yf_name,
        "name_ko": name_ko,
        "domain":  domain,
        "status":  status,
        "deployed_tranches": deployed_tranches,
        "toppick_score": toppick_score,
        "recent_high": round(recent_high, 2),
        "trailing_stop_line": trailing_stop_line,
        "horizontal_support": round(horizontal_support, 2) if horizontal_support else None,
        "next_action": next_action,
        "reason": reason,
        "weight": weight,
        "weight_note": weight_note,
        "metrics": {
            "price": round(price, 2),
            "ma50": round(ma50, 2),
            "ma200": round(ma200, 2),
            "atr14": round(atr14, 2),
            "atr_pct": atr_pct,
            "gap50_pct": gap50_pct,
            "dist_to_stop_pct": dist_to_stop,
            "vol20ma": int(vol20ma),
            "vol_ratio": vol_ratio,
            "growth_score": growth_score,
            "earnings_score": earn_score,
            "health_score": health_score,
            "eps_revision": eps_revision,
            "peg": peg,
            "steps_count": steps_count,
            "steps_list": steps_list,
        },
    }

    indicator_row = {
        "symbol": symbol,
        "date": date.today().isoformat(),
        "price": round(price, 2),
        "ma50": round(ma50, 2),
        "ma200": round(ma200, 2),
        "atr14": round(atr14, 2),
        "atr_pct": atr_pct,
        "recent_high": round(recent_high, 2),
        "trailing_stop_line": trailing_stop_line,
        "horizontal_support": round(horizontal_support, 2) if horizontal_support else None,
        "vol20ma": int(vol20ma),
        "vol_ratio": vol_ratio,
        "gap50_pct": gap50_pct,
        "dist_to_stop_pct": dist_to_stop,
        "toppick_score": toppick_score,
        "growth_score": growth_score,
        "earnings_score": earn_score,
        "health_score": health_score,
        "moat_score": moat_score,
    }

    return updated_item, indicator_row


PROTECTED     = {"ENTRY_1", "ENTRY_2", "ENTRY_3", "TRIM", "EXIT"}
SCORE_DROP    = 40   # 이 점수 미만 WATCH → REMOVED (펀더 완전 붕괴 수준만)
SCORE_RECOVER = 70   # 이 점수 이상 회복 시 REMOVED → WATCH 복귀


def sync_universe(positions: dict, universe: dict) -> dict:
    """
    universe.json 상위 종목을 positions.json에 동기화.
    ENTRY/TRIM/EXIT 상태 종목은 절대 변경하지 않음.
    """
    u_items  = universe.get("items", [])
    top_syms = {u["symbol"] for u in u_items}
    u_map    = {u["symbol"]: u for u in u_items}

    cur = {item["symbol"]: item for item in positions.get("items", [])}
    new_items = []

    # 기존 종목 처리
    for sym, item in cur.items():
        status = item.get("status", "WATCH")
        if status in PROTECTED:
            new_items.append(item)          # 포지션 보유 중 → 보호
        elif sym in top_syms:
            if status == "REMOVED":         # MA50 재돌파 → WATCH 복귀
                item = {**item, "status": "WATCH", "reason": "유니버스 복귀 (MA50 돌파)"}
            new_items.append(item)
        else:
            score = u_map.get(sym, {}).get("toppick_score", 0)
            if status == "WATCH" and score < SCORE_DROP:
                item = {**item, "status": "REMOVED",
                        "reason": f"탑픽 점수 하락 ({score}점)"}
            new_items.append(item)

    # 신규 편입 (WATCH 상태로)
    existing = {item["symbol"] for item in new_items}

    for u in u_items:
        sym = u["symbol"]
        if sym in existing:
            continue
        if u.get("toppick_score", 0) < 70:
            continue
        new_items.append({
            "symbol":           sym,
            "name":             u["name"],
            "name_ko":          u.get("name_ko", ""),
            "domain":           u.get("domain", ""),
            "status":           "WATCH",
            "moat_score":       u["moat_score"],
            "avg_price":        None,
            "weight":           0,
            "deployed_tranches": [],
            "recent_high":      None,
            "trailing_stop_line": None,
            "horizontal_support": None,
            "cooldown_until":   None,
            "toppick_score":    u["toppick_score"],
            "metrics":          {},
        })
        print(f"  [신규 편입] {sym} ({u['toppick_score']}점) → WATCH")

    return {**positions, "items": new_items}


def main():
    today = date.today()
    print(f"\n[모멘텀 배치] {today}")

    positions = load_json(DATA / "positions.json")
    mm        = load_json(DATA / "momentum_market.json")
    regime    = mm.get("regime", "GREEN")

    # universe.json이 있으면 먼저 sync
    universe_path = DATA / "universe.json"
    if universe_path.exists():
        universe = load_json(universe_path)
        positions = sync_universe(positions, universe)
        print(f"  유니버스 sync 완료 ({len(positions.get('items',[]))}개)")

    items     = positions.get("items", [])
    new_items = []
    indicators = []

    for item in items:
        updated, ind = process_symbol(item, regime)
        new_items.append(updated)
        if ind:
            indicators.append(ind)
        symbol = item["symbol"]
        action = updated.get("next_action", "HOLD")
        reason = updated.get("reason", "")
        print(f"    → {action}  ({reason})")

    save_json(DATA / "positions.json", {
        **positions,
        "as_of": today.isoformat(),
        "regime": regime,
        "items": new_items,
    })

    save_json(DATA / "indicators.json", {
        "as_of": today.isoformat(),
        "items": indicators,
    })

    print(f"\n✓ 모멘텀 배치 완료 ({today})")


if __name__ == "__main__":
    main()
