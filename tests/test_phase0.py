import pytest
import pandas as pd
from datetime import date


# ── check_masam ──────────────────────────────────────────────


def test_check_masam_detects_masam_day(ixic_june_2026):
    from scripts.phase0_poc import check_masam

    result = check_masam(df_ixic=ixic_june_2026)

    assert result["status"] == "PASS"
    assert result["latest_masam_date"].date() == date(2026, 6, 5)
    assert abs(result["latest_masam_pct"] - (-4.18)) < 0.1


def test_check_masam_month_count_is_calendar_month(ixic_june_2026):
    from scripts.phase0_poc import check_masam

    result = check_masam(df_ixic=ixic_june_2026)

    # June 2026 has exactly 1 마삼 (06/05 only)
    assert result["month_count"] == 1


def test_check_masam_no_masam_returns_none():
    from scripts.phase0_poc import check_masam
    from tests.conftest import make_ixic_df

    # All changes are less than -3%
    df = make_ixic_df([1000.0, 990.0, 985.0, 988.0, 992.0])

    result = check_masam(df_ixic=df)

    assert result["status"] == "PASS"
    assert result["latest_masam_date"] is None


def test_check_masam_prev_year_return(ixic_with_prev_year):
    from scripts.phase0_poc import check_masam

    result = check_masam(df_ixic=ixic_with_prev_year)

    # 2025-01-02: 19000 → 2025-12-31: 23111.46 → approx +21.6%
    assert result["prev_year_return"] is not None
    assert 15.0 < result["prev_year_return"] < 30.0


def test_check_masam_ath_drawdown(ixic_june_2026):
    from scripts.phase0_poc import check_masam

    result = check_masam(df_ixic=ixic_june_2026)

    # ATH is 27000.0 (first value), current is 25678.82 → approx -4.9%
    assert result["ath_value"] == pytest.approx(27000.0, abs=1.0)
    assert result["ath_drawdown"] < 0
