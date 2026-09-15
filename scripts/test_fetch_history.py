"""fetch_eod.py의 fetch_history() NaN 꼬리 재조회 로직 검증 (실행: python3 scripts/test_fetch_history.py).
yfinance가 긴 기간 조회 시 최신 종가를 NaN으로 잘못 반환하는 버그(2026-09-15 확인)에 대한
재시도 로직을 yf.Ticker를 스텁으로 교체해 검증. 실제 fetch_history()를 그대로 호출함
(로직을 복제하지 않음 — 복제본은 실제 코드와 어긋날 수 있음)."""
from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd

import fetch_eod


class _StubTicker:
    def __init__(self, wide_hist, gap_fill_hist):
        self._wide = wide_hist
        self._gap_fill = gap_fill_hist
        self.gap_fill_calls = []

    def history(self, period=None, start=None, end=None, auto_adjust=True):
        if period is not None:
            return self._wide
        self.gap_fill_calls.append((start, end))
        return self._gap_fill


def _df(dates, closes):
    return pd.DataFrame({"Close": closes}, index=pd.to_datetime(dates))


def test_nan_tail_is_replaced_by_gap_fill():
    # period= 조회 결과 마지막 행(2026-09-14)이 NaN — 실제 재현된 버그와 동일 형태
    wide = _df(["2026-09-10", "2026-09-11", "2026-09-14"], [218.36, 218.29, float("nan")])
    # 누락 구간만 딱 재조회하면 정상 값이 나옴(2026-09-15 확인된 실제 동작)
    gap_fill = _df(["2026-09-14"], [210.96])
    stub = _StubTicker(wide, gap_fill)
    with patch.object(fetch_eod.yf, "Ticker", return_value=stub):
        hist = fetch_eod.fetch_history("NVDA")

    assert not hist["Close"].isna().any(), "재조회 후에도 NaN이 남아있으면 안 됨"
    assert fetch_eod.latest_close(hist) == 210.96, f"최신 종가 210.96 기대, 실제 {fetch_eod.latest_close(hist)}"
    # 재조회는 "마지막 유효일 다음 날"부터만 요청해야 함(그 앞 유효 행이 같이 딸려오면
    # 버그가 그대로 재현되는 것까지 확인됨 — 단순 "최근 N일"로는 안 됨)
    gap_start, _ = stub.gap_fill_calls[0]
    assert gap_start == date(2026, 9, 12), f"마지막 유효일(9/11) 다음 날부터 재조회 기대, 실제 {gap_start}"


def test_no_nan_skips_gap_fill():
    wide = _df(["2026-09-10", "2026-09-11", "2026-09-14"], [218.36, 218.29, 210.96])
    stub = _StubTicker(wide, gap_fill_hist=None)
    with patch.object(fetch_eod.yf, "Ticker", return_value=stub):
        hist = fetch_eod.fetch_history("NVDA")

    assert fetch_eod.latest_close(hist) == 210.96
    assert stub.gap_fill_calls == [], "NaN이 없으면 재조회를 시도하면 안 됨"


if __name__ == "__main__":
    test_nan_tail_is_replaced_by_gap_fill()
    test_no_nan_skips_gap_fill()
    print("OK — fetch_history NaN gap-fill passed")
