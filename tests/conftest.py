import pandas as pd
import numpy as np
import pytest


def make_ixic_df(closes: list, start: str = "2026-06-02") -> pd.DataFrame:
    """비즈니스일 기준 ^IXIC mock DataFrame 생성."""
    dates = pd.bdate_range(start, periods=len(closes))
    close_series = pd.Series(closes, index=dates, name="Close")
    return pd.DataFrame({"Close": close_series})


@pytest.fixture
def ixic_june_2026():
    """
    실제 데이터 기반 mock:
    06/02(기준), 06/03(-0.54%), 06/04(-0.09%), 06/05(-4.18%), 06/08(+0.86%), 06/09(-0.97%)
    마삼: 06/05 1건
    """
    return make_ixic_df(
        closes=[27000.0, 26853.98, 26830.96, 25709.43, 25929.66, 25678.82],
        start="2026-06-02",
    )


@pytest.fixture
def ixic_with_prev_year():
    """
    2025년 전체 + 2026년 상반기 포함 mock (전년도 역년 수익률 테스트용).
    2025-01-02: 19000, 2025-12-31: 23111.46 → +21.6%
    2026-06-09: 25678.82
    """
    dates_2025 = pd.bdate_range("2025-01-02", "2025-12-31", freq="BME")
    # 간단하게 월말 기준 12개 포인트로 선형 보간
    closes_2025 = np.linspace(19000, 23111.46, len(dates_2025))

    dates_2026 = pd.bdate_range("2026-01-02", "2026-06-09", freq="BME")
    closes_2026 = np.linspace(23200, 25678.82, len(dates_2026))

    all_dates = list(dates_2025) + list(dates_2026)
    all_closes = list(closes_2025) + list(closes_2026)
    close_series = pd.Series(all_closes, index=all_dates, name="Close")
    return pd.DataFrame({"Close": close_series})
