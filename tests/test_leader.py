import pytest
from unittest.mock import MagicMock, patch


def _mock_ticker_factory(mcap_map: dict):
    def factory(t):
        m = MagicMock()
        m.info = {"marketCap": mcap_map.get(t, 0)}
        return m
    return factory


def test_leader_rank1_is_largest():
    from engines.leader import get_leader_status

    mcaps = {"NVDA": 3_500_000_000_000, "AAPL": 3_100_000_000_000, "MSFT": 2_900_000_000_000}
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=list(mcaps))

    assert result["rank1_ticker"] == "NVDA"
    assert result["rank2_ticker"] == "AAPL"


def test_leader_gap_pct():
    from engines.leader import get_leader_status

    # rank1=1000, rank2=900 → gap = (1000-900)/1000 * 100 = 10%
    mcaps = {"A": 1_000_000_000, "B": 900_000_000}
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=["A", "B"])

    assert result["gap_pct"] == pytest.approx(10.0)
    assert result["gap_below_10pct"] is False  # exactly 10% → NOT below 10%


def test_leader_gap_below_10pct():
    from engines.leader import get_leader_status

    mcaps = {"A": 1_000_000_000, "B": 950_000_000}  # gap = 5%
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=["A", "B"])

    assert result["gap_below_10pct"] is True


def test_leader_overtake_not_detected():
    from engines.leader import get_leader_status

    mcaps = {"AAPL": 3_200_000_000_000, "NVDA": 3_500_000_000_000}
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=["AAPL", "NVDA"])

    assert result["rank1_ticker"] == "NVDA"
    assert result["overtake_detected"] is False


def test_leader_insufficient_data_returns_none_fields():
    from engines.leader import get_leader_status

    # Only 1 ticker with valid mcap → can't determine rank2
    mcaps = {"AAPL": 3_000_000_000_000}
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=["AAPL", "MISSING"])

    assert result["rank1_ticker"] is None
    assert result["rank2_ticker"] is None
