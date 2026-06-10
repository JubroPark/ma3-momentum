import pytest
import pandas as pd
from unittest.mock import MagicMock


def _make_fred(dff: float, walcl_values: list) -> MagicMock:
    """Mock Fred API with DFF and WALCL series."""
    mock = MagicMock()
    walcl_series = pd.Series(
        walcl_values,
        index=pd.date_range("2026-04-01", periods=len(walcl_values), freq="W"),
    )
    mock.get_series.side_effect = [
        pd.Series([dff], index=pd.to_datetime(["2026-06-08"])),
        walcl_series,
    ]
    return mock


def test_market_context_non_zero_qe_off():
    from engines.market_context import get_market_context
    import re

    mock_fred = _make_fred(3.62, [8000, 7980, 7960, 7940, 7920, 7900, 7880, 7860])
    result = get_market_context(fred=mock_fred)

    assert result["rate_env"] == "NON_ZERO"
    assert result["dff"] == pytest.approx(3.62)
    assert result["qe_state"] == "QE_OFF"
    assert result["qe_active"] is False
    assert re.match(r"\d{4}-\d{2}-\d{2}", result["last_updated"])
    assert isinstance(result["slope_pct"], float)


def test_market_context_zero_qe_on():
    from engines.market_context import get_market_context
    import re

    mock_fred = _make_fred(0.08, [8000, 8020, 8040, 8060, 8080, 8100, 8120, 8140])
    result = get_market_context(fred=mock_fred)

    assert result["rate_env"] == "ZERO"
    assert result["qe_state"] == "QE_ON"
    assert result["qe_active"] is True
    assert re.match(r"\d{4}-\d{2}-\d{2}", result["last_updated"])
    assert isinstance(result["slope_pct"], float)
