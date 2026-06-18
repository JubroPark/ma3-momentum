"""FRED API → app/public/data/masam_market.json"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request

API_KEY = os.environ.get("FRED_API_KEY", "")
if not API_KEY:
    sys.exit("FRED_API_KEY 환경변수를 설정하세요")

OUT = Path(__file__).parent.parent / "app/public/data/masam_market.json"
BASE = "https://api.stlouisfed.org/fred/series/observations"


def fetch(series: str, limit: int = 60) -> list:
    url = (
        f"{BASE}?series_id={series}&api_key={API_KEY}"
        f"&file_type=json&sort_order=desc&limit={limit}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"FRED API 오류 ({series}): HTTP {e.code} {e.reason}")
    except urllib.error.URLError as e:
        sys.exit(f"FRED API 연결 실패 ({series}): {e.reason}")

    if "observations" not in data:
        sys.exit(f"FRED 응답 오류 ({series}): 'observations' 키 없음 — {data}")

    return data["observations"]


def latest_value(obs: list) -> Optional[float]:
    for o in obs:
        try:
            return float(o["value"])
        except (ValueError, KeyError):
            continue
    return None


def slope_sign(obs: list, n: int = 20) -> str:
    """obs는 내림차순(최신 먼저). n개 유효값의 최신 vs 최오래된 비교."""
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
    # vals[0] = 최신, vals[-1] = 가장 오래된
    return "DOWN" if vals[0] < vals[-1] else "UP"


def main():
    print("FRED 데이터 수집 중...")

    dff_obs = fetch("DFF", 10)
    dgs_obs = fetch("DGS10", 30)
    walcl_obs = fetch("WALCL", 8)

    dff = latest_value(dff_obs)
    if dff is None:
        sys.exit("DFF 유효값 없음")

    dgs10 = latest_value(dgs_obs)
    if dgs10 is None:
        sys.exit("DGS10 유효값 없음")

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

    rate_env = "ZERO" if dff <= 0.25 else "NON_ZERO"
    t10_trend = slope_sign(dgs_obs, 20)

    # 기존 파일에서 표시용 필드(vix, fear_greed, usd_krw) 유지
    existing = {}
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text())
        except Exception:
            pass

    result = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d"),
        "rate_env": rate_env,
        "dff": round(dff, 4),
        "qe_active": qe_active,
        "walcl_trend": walcl_trend,
        "treasury_10y": round(dgs10, 4),
        "treasury_10y_trend": t10_trend,
        "vix": existing.get("vix"),
        "fear_greed": existing.get("fear_greed"),
        "usd_krw": existing.get("usd_krw"),
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"완료: {OUT}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
