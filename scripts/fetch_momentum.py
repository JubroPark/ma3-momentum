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

수동 유지:
  - toppick_score / avg_price / weight / deployed_tranches / cooldown_until
  - horizontal_support (자동 탐색 fallback: 52주 저점)
  - status (매수 판단은 사용자 확정 원칙)
"""
import json
from datetime import date
from pathlib import Path
from typing import Optional

import yfinance as yf

DATA = Path(__file__).parent.parent / "app/public/data"

TRAIL_MIN = 0.15
TRAIL_MAX = 0.30
TRAIL_DEFAULT = 0.20
ATR_MULT = 5.0
ENTRY2_BAND = 0.03   # MA50 ±3% = 2차 줍줍 구간
SUPPORT_BAND = 0.03  # 지지선 ±3% 근접 판단


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장: {path.name}")


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

    closes = hist["Close"].values
    lows   = hist["Low"].values
    n = min(len(closes), 126)  # 약 6개월
    recent_closes = closes[-n:]
    recent_lows   = lows[-n:]

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


# ── 메인 처리 ─────────────────────────────────────────────────────────────────

def process_symbol(item: dict, regime: str) -> tuple:
    """(updated_item, indicator_row) 반환"""
    symbol = item["symbol"]
    status = item.get("status", "WATCH")
    existing_support = item.get("horizontal_support")
    existing_recent_high = item.get("recent_high")

    print(f"  {symbol} 조회 중...")
    try:
        hist = yf.Ticker(symbol).history(period="1y", auto_adjust=True)
        if hist.empty:
            print(f"  [경고] {symbol} 데이터 없음 — 스킵")
            return item, None
    except Exception as e:
        print(f"  [경고] {symbol} 조회 실패: {e}")
        return item, None

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

    # recent_high: 보유 중이면 비감소 최고가 유지
    year_high = float(closes.max())
    if status in ("ENTRY_1", "ENTRY_2", "ENTRY_3", "TRIM"):
        recent_high = max(existing_recent_high or 0, price, year_high)
    else:
        recent_high = year_high

    # 트레일링 스탑
    trail_pct = calc_trailing_pct(atr14, price)
    trailing_stop_line = round(recent_high * (1 - trail_pct), 2) if recent_high > 0 else None

    # 지지선
    horizontal_support = detect_support(hist, price, existing_support)

    # 파생 지표
    gap50_pct       = round((price - ma50) / ma50 * 100, 1)
    dist_to_stop    = round((price - trailing_stop_line) / price * 100, 1) if trailing_stop_line else None

    # next_action
    next_action, reason = calc_next_action(
        status=status,
        price=price,
        ma50=ma50,
        trailing_stop_line=trailing_stop_line,
        horizontal_support=horizontal_support,
        vol_ratio=vol_ratio,
        regime=regime,
        toppick_score=item.get("toppick_score", 0),
    )

    updated_item = {
        **item,
        "recent_high": round(recent_high, 2),
        "trailing_stop_line": trailing_stop_line,
        "horizontal_support": round(horizontal_support, 2) if horizontal_support else None,
        "next_action": next_action,
        "reason": reason,
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
    }

    return updated_item, indicator_row


def main():
    today = date.today()
    print(f"\n[모멘텀 배치] {today}")

    positions = load_json(DATA / "positions.json")
    mm        = load_json(DATA / "momentum_market.json")
    regime    = mm.get("regime", "GREEN")

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
