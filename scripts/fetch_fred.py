"""FRED API → app/public/data/masam_market.json"""

import os
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request

API_KEY = os.environ.get("FRED_API_KEY", "")
if not API_KEY:
    sys.exit("FRED_API_KEY 환경변수를 설정하세요")

OUT = Path(__file__).parent.parent / "app/public/data/masam_market.json"
BASE = "https://api.stlouisfed.org/fred/series/observations"
TIMEOUT = 20
RETRIES = 3

# 시리즈 설정을 한 곳에서 관리(2026-08-20 리팩터링 — 예전엔 main() 안에 하드코딩).
# critical=True(기존 DFF/DGS10/WALCL)는 실패 시 fetch()가 배치 전체를 sys.exit로
# 중단시켜 기존 파일을 보존함 — 이 셋은 fetch_eod.py의 헤지 자동판정 엔진
# (calc_hedge_type)에 그대로 들어가는 마삼룰 판정용 값이라 부분 갱신을 허용하면 안 됨.
# critical=False(신규 6종)는 try_fetch()를 써서 개별 실패가 다른 카드에 영향 없음
# — 실패한 시리즈는 latest_value()가 None을 반환하고, 프론트는 그 카드만
# "데이터 없음"으로 표시(마삼룰 판정과 무관한 표시 전용 지표라 이렇게 처리 가능).
SERIES = [
    {"key": "dff",             "id": "DFF",         "limit": 60, "critical": True},
    {"key": "dgs10",           "id": "DGS10",       "limit": 60, "critical": True},
    {"key": "walcl",           "id": "WALCL",       "limit": 60, "critical": True},
    {"key": "dgs30",           "id": "DGS30",       "limit": 60, "critical": False},
    {"key": "wresbal",         "id": "WRESBAL",     "limit": 60, "critical": False},
    {"key": "dtwexbgs",        "id": "DTWEXBGS",    "limit": 60, "critical": False},
    {"key": "t5yifr",          "id": "T5YIFR",      "limit": 60, "critical": False},
    {"key": "treast",          "id": "TREAST",      "limit": 60, "critical": False},
    # 요청받은 "ACMTP10"은 FRED에 존재하지 않는 시리즈 ID(404 확인, 2026-08-20).
    # ACM 모델의 10년 기간프리미엄 실제 FRED ID는 THREEFYTP10
    # ("Term Premium on a 10 Year Zero Coupon Bond").
    {"key": "term_premium_10y", "id": "THREEFYTP10", "limit": 60, "critical": False},
]


def _get(url: str):
    """timeout=20s, 실패 시 최대 3회 재시도(1s/2s 대기)."""
    last_err: urllib.error.URLError = urllib.error.URLError("unreachable")
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
                return json.loads(r.read())
        except urllib.error.URLError as e:
            last_err = e
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    raise last_err


def fetch(series: str, limit: int = 60) -> list:
    url = (
        f"{BASE}?series_id={series}&api_key={API_KEY}"
        f"&file_type=json&sort_order=desc&limit={limit}"
    )
    try:
        data = _get(url)
    except urllib.error.HTTPError as e:
        sys.exit(f"FRED API 오류 ({series}): HTTP {e.code} {e.reason}")
    except urllib.error.URLError as e:
        sys.exit(f"FRED API 연결 실패 ({series}, {RETRIES}회 재시도 후): {e.reason}")

    if "observations" not in data:
        sys.exit(f"FRED 응답 오류 ({series}): 'observations' 키 없음 — {data}")

    return data["observations"]


def try_fetch(series: str, limit: int = 3) -> list:
    """실패 시 sys.exit 없이 빈 리스트 반환."""
    url = (
        f"{BASE}?series_id={series}&api_key={API_KEY}"
        f"&file_type=json&sort_order=desc&limit={limit}"
    )
    try:
        data = _get(url)
        return data.get("observations", [])
    except Exception:
        return []


def series_values(obs: list, n: int = 20) -> list:
    """obs(내림차순, 최신 먼저)에서 유효값 n개를 뽑아 오래된→최신 순으로 반환.
    경제지표 탭 스파크라인용 — 값만 필요하고 날짜는 안 씀(단순 추세선)."""
    vals = []
    for o in obs:
        try:
            vals.append(float(o["value"]))
        except (ValueError, KeyError):
            continue
        if len(vals) >= n:
            break
    return list(reversed(vals))


def ma4_up(obs: list) -> Optional[bool]:
    """obs(내림차순, 최신 먼저)에서 최근 4개 관측치 평균 vs 그 이전 4개 평균 비교.
    기존 WALCL 단독 QE 판정과 동일한 방식 — 일관성을 위해 통일(2026-08-20).
    관측치가 8개 미만이면 처음/끝 단순 비교로 폴백, 2개 미만이면 판정 불가(None)."""
    vals = []
    for o in obs:
        try:
            vals.append(float(o["value"]))
        except (ValueError, KeyError):
            continue
    if len(vals) >= 8:
        return (sum(vals[:4]) / 4) > (sum(vals[4:8]) / 4)
    if len(vals) >= 2:
        return vals[0] > vals[-1]
    return None


def latest_value(obs: list) -> Optional[float]:
    for o in obs:
        try:
            return float(o["value"])
        except (ValueError, KeyError):
            continue
    return None


def latest_date(obs: list) -> Optional[str]:
    """4단계(2026-08-21): 일간/주간 발표 주기 구분 카드에 "기준일" 표시용.
    obs(내림차순, 최신 먼저)의 첫 유효 관측치 날짜(FRED 응답 그대로 YYYY-MM-DD)."""
    for o in obs:
        try:
            float(o["value"])
            return o.get("date")
        except (ValueError, KeyError):
            continue
    return None


def dff_monthly_change(obs: list, n: int = 22) -> str:
    """DFF obs(내림차순). 최신 vs ~22거래일 전 비교 → 인상/인하/동결."""
    vals = []
    for o in obs:
        try:
            vals.append(float(o["value"]))
        except (ValueError, KeyError):
            continue
    if len(vals) < 2:
        return "동결"
    recent = vals[0]
    old = vals[min(n, len(vals) - 1)]
    diff = recent - old
    if diff < -0.04:
        return "인하"
    elif diff > 0.04:
        return "인상"
    return "동결"


def slope_sign(obs: list, n: int = 20, threshold_bp: float = 20.0) -> str:
    """obs는 내림차순(최신 먼저). n개 유효값의 최신 vs 최오래된 비교.
    차이가 threshold_bp(기본 20bp) 미만이면 UNKNOWN(→ 달러 보유) 반환."""
    vals = []
    for o in obs:
        try:
            vals.append(float(o["value"]))
        except (ValueError, KeyError):
            continue
        if len(vals) >= n:
            break
    if len(vals) < 2:
        return "UNKNOWN"
    diff_bp = (vals[0] - vals[-1]) * 100  # %p → bp 변환
    if diff_bp < -threshold_bp:
        return "DOWN"
    elif diff_bp > threshold_bp:
        return "UP"
    return "UNKNOWN"


def to_trillion(v: Optional[float]) -> Optional[float]:
    """WALCL/TREAST/WRESBAL은 FRED 단위가 백만 달러 — 조 달러로 변환."""
    return round(v / 1_000_000, 2) if v is not None else None


def change_over(obs: list, n: int, transform=None) -> tuple:
    """obs(내림차순, 최신 먼저)에서 최신값과 n번째 이전 관측치의 차이.
    transform이 있으면 각 값에 먼저 적용(예: to_trillion) — 선형 변환이라 순서 무관.
    반환: (변화량, 방향 'UP'/'DOWN'/'FLAT') — 관측치가 n개보다 적으면 (None, None).
    3단계(2026-08-21): "20영업일 변화량" 요청을 일간 시리즈는 그대로(n=20),
    주간 시리즈(WALCL/TREAST/WRESBAL)는 n=4(4주)로 적용 — 20개 주간 관측치면
    거의 5개월 전과 비교하는 셈이라 "최근 변화"라는 취지에 안 맞음. 2단계 QE
    판정에 쓴 4주 이평 윈도우와도 맞춰 일관성 유지."""
    vals = []
    for o in obs:
        try:
            v = float(o["value"])
            vals.append(transform(v) if transform else v)
        except (ValueError, KeyError):
            continue
        if len(vals) > n:
            break
    if len(vals) <= n:
        return None, None
    diff = round(vals[0] - vals[n], 4)
    direction = "UP" if diff > 0 else "DOWN" if diff < 0 else "FLAT"
    return diff, direction


def main():
    print("FRED 데이터 수집 중...")

    obs_by_key = {}
    for s in SERIES:
        fn = fetch if s["critical"] else try_fetch
        obs_by_key[s["key"]] = fn(s["id"], s["limit"])
        if not s["critical"] and not obs_by_key[s["key"]]:
            print(f"  [경고] {s['id']} 조회 실패 — 이 카드만 데이터 없음으로 저장")

    dff_obs   = obs_by_key["dff"]
    dgs_obs   = obs_by_key["dgs10"]
    walcl_obs = obs_by_key["walcl"]

    dff = latest_value(dff_obs)
    if dff is None:
        sys.exit("DFF 유효값 없음")

    dgs10 = latest_value(dgs_obs)
    if dgs10 is None:
        sys.exit("DGS10 유효값 없음")

    # 전일 DGS10 (두 번째 유효값)
    dgs10_prev: Optional[float] = None
    _found_first = False
    for o in dgs_obs:
        try:
            v = float(o["value"])
            if not _found_first:
                _found_first = True
            else:
                dgs10_prev = v
                break
        except (ValueError, KeyError):
            continue
    treasury_10y_change = round(dgs10 - dgs10_prev, 4) if dgs10_prev is not None else None

    # QE: WALCL 최근 4주 평균 vs 이전 4주 평균
    walcl_vals = []
    for o in walcl_obs:
        try:
            walcl_vals.append(float(o["value"]))
        except (ValueError, KeyError):
            continue

    if len(walcl_vals) >= 8:
        ma4_recent = sum(walcl_vals[:4]) / 4
        ma4_prev = sum(walcl_vals[4:8]) / 4
        qe_active = ma4_recent > ma4_prev
        walcl_trend = "UP" if qe_active else "DOWN"
    elif len(walcl_vals) >= 2:
        qe_active = walcl_vals[0] > walcl_vals[-1]
        walcl_trend = "UP" if qe_active else "DOWN"
    else:
        qe_active = False
        walcl_trend = "UNKNOWN"

    # WALCL 최신값 (단위: 백만 달러 → 조 달러)
    walcl_trillion = round(walcl_vals[0] / 1_000_000, 2) if walcl_vals else None

    rate_env      = "ZERO" if dff <= 0.25 else "NON_ZERO"
    t10_trend     = slope_sign(dgs_obs, 20)
    dff_trend     = slope_sign(dff_obs, 20)
    dff_chg_text  = dff_monthly_change(dff_obs)

    # 신규 6종 — 표시 전용, critical=False라 실패해도 latest_value가 None을 반환할 뿐
    # main() 자체는 안 죽음(위 SERIES 루프 참고).
    dgs30              = latest_value(obs_by_key["dgs30"])
    wresbal_trillion   = to_trillion(latest_value(obs_by_key["wresbal"]))
    dollar_index       = latest_value(obs_by_key["dtwexbgs"])
    inflation_exp_5y5y = latest_value(obs_by_key["t5yifr"])
    treast_trillion    = to_trillion(latest_value(obs_by_key["treast"]))
    term_premium_10y   = latest_value(obs_by_key["term_premium_10y"])
    treasury_30y_10y_spread = round(dgs30 - dgs10, 4) if dgs30 is not None else None

    # QE 3-state 판정 (표시 전용 — 2단계, 2026-08-20 추가).
    # ⚠️ 마삼룰 헤지 자동판정(calc_hedge_type)이 쓰는 기존 qe_active 불리언은
    # 위에서 그대로 유지(WALCL 단독 4주 이평 비교) — 이 블록은 그걸 대체하지 않음.
    #
    # WALCL 증가만으로는 QE_ON을 오판할 수 있음(TGA 변동·레포 사용 등으로도 총자산이
    # 늘 수 있음) → TREAST(연준의 순수 국채 보유량) 방향까지 같이 봐서 구분:
    #   WALCL↑ AND TREAST↑           → QE_ON        (총자산도 늘고 실제 국채도 사들이는 중)
    #   WALCL↑ AND TREAST 횡보/감소   → LIQUIDITY_SUPPLY (총자산은 늘지만 국채 매입은 아님 —
    #                                                     레포·긴급대출 등 비QE성 유동성 공급)
    #   WALCL 횡보/감소               → QT            (TREAST 방향과 무관 — 총자산 자체가
    #                                                     안 늘면 QE로 볼 수 없음이 우선 판단.
    #                                                     WALCL↓+TREAST↑ 같은 애매한 조합도
    #                                                     이 case로 떨어짐 — 재투자 중인 QT로 해석)
    treast_up = ma4_up(obs_by_key["treast"])
    if walcl_trend != "UP":
        qe_state = "QT"
    elif treast_up:
        qe_state = "QE_ON"
    elif treast_up is False:
        qe_state = "LIQUIDITY_SUPPLY"
    else:
        # TREAST 조회 실패(치명적이지 않음) — WALCL만으로는 QE_ON/유동성공급을
        # 구분 못 하므로 UNKNOWN으로 명시(추측성 판정 금지)
        qe_state = "UNKNOWN"

    # 3단계: 추세 축 — 일간 시리즈는 20영업일, 주간 시리즈는 4주 변화량
    dff_chg_20d,         dff_chg_dir         = change_over(dff_obs, 20)
    treasury_10y_chg_20d, treasury_10y_chg_dir = change_over(dgs_obs, 20)
    treasury_30y_chg_20d, treasury_30y_chg_dir = change_over(obs_by_key["dgs30"], 20)
    dollar_index_chg_20d, dollar_index_chg_dir = change_over(obs_by_key["dtwexbgs"], 20)
    inflation_exp_chg_20d, inflation_exp_chg_dir = change_over(obs_by_key["t5yifr"], 20)
    term_premium_chg_20d, term_premium_chg_dir = change_over(obs_by_key["term_premium_10y"], 20)
    walcl_chg_4w,   walcl_chg_dir   = change_over(walcl_obs, 4, transform=to_trillion)
    wresbal_chg_4w, wresbal_chg_dir = change_over(obs_by_key["wresbal"], 4, transform=to_trillion)
    treast_chg_4w,  treast_chg_dir  = change_over(obs_by_key["treast"], 4, transform=to_trillion)
    # 스프레드 = 30Y - 10Y이므로 변화량도 두 변화량의 차(같은 구간 재계산 불필요)
    if treasury_30y_chg_20d is not None and treasury_10y_chg_20d is not None:
        spread_chg_20d = round(treasury_30y_chg_20d - treasury_10y_chg_20d, 4)
        spread_chg_dir = "UP" if spread_chg_20d > 0 else "DOWN" if spread_chg_20d < 0 else "FLAT"
    else:
        spread_chg_20d, spread_chg_dir = None, None


    # 기존 파일에서 표시용 필드(vix, fear_greed, usd_krw) 유지
    existing = {}
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text())
        except Exception:
            pass

    # existing를 먼저 펼치고 이 스크립트가 계산한 키만 덮어씀(기존엔 vix/fear_greed 등
    # 정해둔 몇 개만 화이트리스트로 골라 옮겼는데, fetch_eod.py가 나중에 추가한
    # vix_chg_20d/vix_chg_dir처럼 새 필드가 생길 때마다 화이트리스트에 안 넣으면
    # fetch_fred.py가 재실행될 때 조용히 사라지는 문제가 있었음 — 2026-08-21 확인).
    result = {
        **existing,
        "as_of": datetime.utcnow().strftime("%Y-%m-%d"),
        "rate_env": rate_env,
        "dff": round(dff, 4),
        "dff_change_text": dff_chg_text,
        "qe_active": qe_active,
        "walcl_trend": walcl_trend,
        "walcl_trillion": walcl_trillion,
        "treasury_10y": round(dgs10, 4),
        "treasury_10y_prev": round(dgs10_prev, 4) if dgs10_prev is not None else None,
        "treasury_10y_change": treasury_10y_change,
        "treasury_10y_trend": t10_trend,
        "dff_trend": dff_trend,

        # 1단계 신규 수집 (2026-08-20) — 전부 표시 전용, 마삼룰 판정 로직 미사용
        "treasury_30y": round(dgs30, 4) if dgs30 is not None else None,
        "treasury_30y_10y_spread": treasury_30y_10y_spread,
        "wresbal_trillion": wresbal_trillion,
        "dollar_index": round(dollar_index, 4) if dollar_index is not None else None,
        "inflation_expectation_5y5y": round(inflation_exp_5y5y, 4) if inflation_exp_5y5y is not None else None,
        "treast_trillion": treast_trillion,
        "term_premium_10y": round(term_premium_10y, 4) if term_premium_10y is not None else None,
        "qe_state": qe_state,

        # 4단계(2026-08-21): 일간/주간 발표 주기가 섞이면 며칠 지난 값을 오늘 값으로
        # 오독할 수 있어서, 새 섹션 카드마다 실제 관측치 날짜를 같이 보여주기 위함.
        "treasury_10y_as_of": latest_date(dgs_obs),
        "treasury_30y_as_of": latest_date(obs_by_key["dgs30"]),
        "dollar_index_as_of": latest_date(obs_by_key["dtwexbgs"]),
        "inflation_expectation_5y5y_as_of": latest_date(obs_by_key["t5yifr"]),
        "term_premium_10y_as_of": latest_date(obs_by_key["term_premium_10y"]),
        "walcl_trillion_as_of": latest_date(walcl_obs),
        "treast_trillion_as_of": latest_date(obs_by_key["treast"]),
        "wresbal_trillion_as_of": latest_date(obs_by_key["wresbal"]),

        # 3단계 추세 축(2026-08-21) — {지표}_chg_20d/4w(변화량 숫자, 주간 시리즈는
        # 이름은 그대로 두고 실제론 4주 값), {지표}_chg_dir('UP'/'DOWN'/'FLAT')
        "dff_chg_20d": dff_chg_20d, "dff_chg_dir": dff_chg_dir,
        "treasury_10y_chg_20d": treasury_10y_chg_20d, "treasury_10y_chg_dir": treasury_10y_chg_dir,
        "treasury_30y_chg_20d": treasury_30y_chg_20d, "treasury_30y_chg_dir": treasury_30y_chg_dir,
        "treasury_30y_10y_spread_chg_20d": spread_chg_20d, "treasury_30y_10y_spread_chg_dir": spread_chg_dir,
        "dollar_index_chg_20d": dollar_index_chg_20d, "dollar_index_chg_dir": dollar_index_chg_dir,
        "inflation_expectation_5y5y_chg_20d": inflation_exp_chg_20d, "inflation_expectation_5y5y_chg_dir": inflation_exp_chg_dir,
        "term_premium_10y_chg_20d": term_premium_chg_20d, "term_premium_10y_chg_dir": term_premium_chg_dir,
        "walcl_trillion_chg_4w": walcl_chg_4w, "walcl_trillion_chg_dir": walcl_chg_dir,
        "wresbal_trillion_chg_4w": wresbal_chg_4w, "wresbal_trillion_chg_dir": wresbal_chg_dir,
        "treast_trillion_chg_4w": treast_chg_4w, "treast_trillion_chg_dir": treast_chg_dir,

        "vix": existing.get("vix"),
        "fear_greed": existing.get("fear_greed"),
        "usd_krw": existing.get("usd_krw"),
        "market_sentiment": existing.get("market_sentiment"),
        "spy_ma200_label": existing.get("spy_ma200_label"),

        # 경제지표 탭 스파크라인용 추세값(오래된→최신 순). vix는 fetch_eod.py가 채움 —
        # 여기선 기존 값을 그대로 보존만 함. 3단계(2026-08-21)에서 20/12개 → 60개로 확장
        # + 신규 6종 추가.
        "history": {
            "dff": series_values(dff_obs, 60),
            "walcl_trillion": [round(v / 1_000_000, 2) for v in series_values(walcl_obs, 60)],
            "treasury_10y": series_values(dgs_obs, 60),
            "treasury_30y": series_values(obs_by_key["dgs30"], 60),
            "treasury_30y_10y_spread": [
                round(a - b, 4) for a, b in zip(
                    series_values(obs_by_key["dgs30"], 60),
                    series_values(dgs_obs, 60),
                )
            ] if obs_by_key["dgs30"] else [],
            "wresbal_trillion": [round(v / 1_000_000, 2) for v in series_values(obs_by_key["wresbal"], 60)],
            "dollar_index": series_values(obs_by_key["dtwexbgs"], 60),
            "inflation_expectation_5y5y": series_values(obs_by_key["t5yifr"], 60),
            "treast_trillion": [round(v / 1_000_000, 2) for v in series_values(obs_by_key["treast"], 60)],
            "term_premium_10y": series_values(obs_by_key["term_premium_10y"], 60),
            "vix": existing.get("history", {}).get("vix", []),
        },
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"완료: {OUT}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
