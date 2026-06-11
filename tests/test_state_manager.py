from __future__ import annotations
from datetime import date


def test_load_positions_missing_file_returns_empty():
    from scripts.state_manager import load_positions
    result = load_positions("/nonexistent/path/positions.json")
    assert result == {"as_of": None, "positions": {}}


def test_get_position_unknown_ticker_returns_watch_defaults():
    from scripts.state_manager import get_position
    positions = {"as_of": None, "positions": {}}
    pos = get_position(positions, "UNKNOWN")
    assert pos["state"] == "WATCH"
    assert pos["days_in_state"] == 0
    assert pos["entry_price"] is None
    assert pos["stop_level"] is None


def test_update_position_does_not_mutate_original():
    from scripts.state_manager import update_position
    original = {"as_of": None, "positions": {}}
    updated = update_position(
        original, "AAPL", "HOLDING", 3,
        "2026-06-08", 201.3, 193.5, "STRONG_BREAKOUT",
    )
    assert "AAPL" not in original.get("positions", {})
    assert updated["positions"]["AAPL"]["state"] == "HOLDING"
    assert updated["positions"]["AAPL"]["entry_price"] == 201.3


def test_update_position_sets_as_of_today():
    from scripts.state_manager import update_position
    positions = {"as_of": None, "positions": {}}
    updated = update_position(positions, "MSFT", "WATCH", 0, None, None, None, None)
    assert updated["as_of"] == str(date.today())


def test_save_and_load_roundtrip(tmp_path):
    from scripts.state_manager import save_positions, load_positions, update_position
    path = str(tmp_path / "positions.json")
    positions = {"as_of": None, "positions": {}}
    positions = update_position(
        positions, "AAPL", "HOLDING", 3,
        "2026-06-08", 201.3, 193.5, "STRONG_BREAKOUT",
    )
    save_positions(positions, path)
    loaded = load_positions(path)
    assert loaded["positions"]["AAPL"]["state"] == "HOLDING"
    assert loaded["positions"]["AAPL"]["entry_price"] == 201.3
