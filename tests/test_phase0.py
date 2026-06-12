import pytest
import pandas as pd
import numpy as np
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


# ── check_rate_env ───────────────────────────────────────────


def test_check_rate_env_non_zero():
    from scripts.phase0_poc import check_rate_env
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [4.5], index=pd.to_datetime(["2026-06-09"])
    )

    result = check_rate_env(fred=mock_fred)

    assert result["status"] == "PASS"
    assert result["rate_env"] == "NON_ZERO"
    assert result["dff"] == pytest.approx(4.5)


def test_check_rate_env_zero():
    from scripts.phase0_poc import check_rate_env
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [0.08], index=pd.to_datetime(["2021-06-09"])
    )

    result = check_rate_env(fred=mock_fred)

    assert result["status"] == "PASS"
    assert result["rate_env"] == "ZERO"


def test_check_rate_env_boundary():
    """DFF = 0.25%는 ZERO_RATE 경계값."""
    from scripts.phase0_poc import check_rate_env
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [0.25], index=pd.to_datetime(["2022-03-15"])
    )

    result = check_rate_env(fred=mock_fred)

    assert result["rate_env"] == "ZERO"  # DFF ≤ 0.25% = ZERO


# ── check_drawdown ───────────────────────────────────────────


def test_check_drawdown_current_is_ath():
    """현재 종가가 전고점이면 하락률 0."""
    from scripts.phase0_poc import check_drawdown
    from tests.conftest import make_ixic_df

    df = make_ixic_df([1000.0, 1010.0, 1020.0, 1030.0])  # 계속 상승

    result = check_drawdown(df_ixic=df)

    assert result["status"] == "PASS"
    assert result["ath_drawdown"] == pytest.approx(0.0, abs=0.01)


def test_check_drawdown_below_ath(ixic_june_2026):
    from scripts.phase0_poc import check_drawdown

    # ATH 27000(index 0), 현재 25678.82 → 약 -4.9%
    result = check_drawdown(df_ixic=ixic_june_2026)

    assert result["status"] == "PASS"
    assert result["ath_value"] == pytest.approx(27000.0, abs=1.0)
    assert result["ath_drawdown"] < 0
    assert result["ath_drawdown"] == pytest.approx(-4.89, abs=0.1)


# ── check_qe ────────────────────────────────────────────────


def _make_walcl_series(values: list, start: str = "2026-04-01") -> pd.Series:
    dates = pd.date_range(start, periods=len(values), freq="W-WED")
    return pd.Series(values, index=dates, name="WALCL")


def test_check_qe_off():
    from scripts.phase0_poc import check_qe
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = _make_walcl_series(
        [8000, 7980, 7960, 7940, 7920, 7900, 7880, 7860]
    )

    result = check_qe(fred=mock_fred)

    assert result["status"] == "PASS"
    assert result["qe_active"] is False
    assert result["qe_state"] == "QE_OFF"


def test_check_qe_on():
    from scripts.phase0_poc import check_qe
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = _make_walcl_series(
        [8000, 8020, 8040, 8060, 8080, 8100, 8120, 8140]
    )

    result = check_qe(fred=mock_fred)

    assert result["status"] == "PASS"
    assert result["qe_active"] is True
    assert result["qe_state"] == "QE_ON"


def test_check_qe_ambiguous():
    from scripts.phase0_poc import check_qe
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = _make_walcl_series(
        [8000, 8001, 7999, 8000, 8001, 8000, 7999, 8000]
    )

    result = check_qe(fred=mock_fred)

    assert result["status"] == "WARN"
    assert result["qe_state"] == "AMBIGUOUS"


# ── check_rs_percentile ──────────────────────────────────────


def make_price_df(n_days: int, tickers: list, seed: int = 42) -> pd.DataFrame:
    """각 ticker의 일별 종가 mock DataFrame."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-11-01", periods=n_days)
    data = {}
    for i, t in enumerate(tickers):
        drift = 0.001 * (i - len(tickers) / 2)
        returns = rng.normal(drift, 0.02, n_days)
        data[t] = 100 * np.cumprod(1 + returns)
    return pd.DataFrame(data, index=dates)


def test_check_rs_percentile_ranking():
    from scripts.phase0_poc import _calc_rs_pct

    tickers = [f"T{i}" for i in range(10)]
    prices = make_price_df(130, tickers)
    spy = prices["T0"]

    rs_pcts = _calc_rs_pct(prices, spy)

    assert all(0 <= v <= 100 for v in rs_pcts.values())
    assert len(rs_pcts) == 10


def test_check_rs_percentile_high_performer():
    from scripts.phase0_poc import _calc_rs_pct

    tickers = [f"T{i}" for i in range(10)]
    prices = make_price_df(130, tickers)
    spy = prices["T0"]

    rs_pcts = _calc_rs_pct(prices, spy)

    # T9 has highest drift → should have highest RS_pct
    assert rs_pcts["T9"] > rs_pcts["T0"]


# ── check_pmi_source ─────────────────────────────────────────


def test_check_pmi_source_pass_when_valid():
    from scripts.phase0_poc import check_pmi_source
    from unittest.mock import MagicMock, patch

    mock_response = MagicMock()
    mock_response.text = "PMI: 48.7\n발표월: 2026-05"

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = check_pmi_source(gemini_key="test-key")

    assert result["status"] == "PASS"
    assert result["pmi_value"] == pytest.approx(48.7)
    assert result["release_month"] == "2026-05"


def test_check_pmi_source_warn_on_parse_failure():
    from scripts.phase0_poc import check_pmi_source
    from unittest.mock import MagicMock, patch

    mock_response = MagicMock()
    mock_response.text = "죄송합니다, 정보를 찾을 수 없습니다."

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = check_pmi_source(gemini_key="test-key")

    assert result["status"] == "WARN"
    assert "파싱 실패" in result["warn_message"]


def test_check_pmi_source_warn_on_exception():
    from scripts.phase0_poc import check_pmi_source
    from unittest.mock import MagicMock, patch

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_client_cls.return_value = mock_client

        result = check_pmi_source(gemini_key="test-key")

    assert result["status"] == "WARN"
    assert "수동입력 폴백" in result["warn_message"]
