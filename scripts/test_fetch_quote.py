"""fetch_live.fetch_quote()가 NaN 꼬리 행을 건너뛰는지 검증 (실행: python3 scripts/test_fetch_quote.py)."""
from unittest.mock import patch

import pandas as pd

import fetch_live


class _Stub:
    def __init__(self, closes):
        self._df = pd.DataFrame({"Close": closes}, index=pd.date_range("2026-09-24", periods=len(closes)))

    def history(self, **kw):
        return self._df


def _quote(closes):
    with patch.object(fetch_live.yf, "Ticker", return_value=_Stub(closes)):
        return fetch_live.fetch_quote("NVDA")


nan = float("nan")
assert _quote([100.0, 110.0, nan]) == {"price": 110.0, "change_pct": 10.0}, "NaN 꼬리는 버리고 유효 2행 사용"
assert _quote([100.0, 110.0, 121.0]) == {"price": 121.0, "change_pct": 10.0}
assert _quote([100.0, nan, nan]) is None, "유효 행 2개 미만이면 None(기존 값 폴백)"

# 최신 행 누락으로 마지막 날짜가 기존보다 오래되면 None(기존 값 폴백) — 2026-11-20 사고
fetch_live._PREV_DATES["NVDA"] = "2026-09-27"  # stub 3행의 마지막 날짜 = 09-26
assert _quote([100.0, 110.0, 121.0]) is None, "시세 날짜 역행이면 None"
fetch_live._PREV_DATES["NVDA"] = "2026-09-26"
assert _quote([100.0, 110.0, 121.0]) == {"price": 121.0, "change_pct": 10.0}, "같은 날짜는 정상"
assert fetch_live._NEW_DATES["NVDA"] == "2026-09-26"
print("OK — fetch_quote NaN tail + stale date passed")
