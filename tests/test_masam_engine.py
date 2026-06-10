import pytest
import pandas as pd
import numpy as np


# ── determine_mode ───────────────────────────────────────────


def test_mode_rebalancing_no_masam():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=0, prev_year_return=None)
    assert mode == "REBALANCING"
    assert panic_type is None


def test_mode_crisis_1_masam():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=1, prev_year_return=20.0)
    assert mode == "CRISIS_STAKING"
    assert panic_type is None


def test_mode_crisis_3_masam():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=3, prev_year_return=50.0)
    # 3회는 아직 PANIC 아님
    assert mode == "CRISIS_STAKING"


def test_mode_panic_basic_4_masam():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=4, prev_year_return=20.0)
    assert mode == "PANIC"
    assert panic_type == "BASIC"


def test_mode_panic_emergency_45pct():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=4, prev_year_return=45.0)
    assert mode == "PANIC"
    assert panic_type == "EMERGENCY"


def test_mode_panic_emergency_above_45():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=5, prev_year_return=60.0)
    assert panic_type == "EMERGENCY"


def test_mode_panic_basic_no_prev_year():
    from engines.masam_engine import determine_mode
    # prev_year_return=None → BASIC (데이터 없으면 EMERGENCY 미판정)
    mode, panic_type = determine_mode(masam_month_count=4, prev_year_return=None)
    assert panic_type == "BASIC"


# ── calc_target_allocation ───────────────────────────────────


def test_allocation_rebalancing():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("REBALANCING", None, "NON_ZERO")
    assert result["stock_pct"] == 100


def test_allocation_crisis_non_zero():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("CRISIS_STAKING", None, "NON_ZERO")
    assert result["stock_pct"] == 50


def test_allocation_crisis_zero():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("CRISIS_STAKING", None, "ZERO")
    assert result["stock_pct"] == 25


def test_allocation_panic_emergency():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("PANIC", "EMERGENCY", "NON_ZERO")
    assert result["stock_pct"] == 0
    assert result["cash_pct"] == 100


def test_allocation_panic_basic():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("PANIC", "BASIC", "NON_ZERO")
    assert result["stock_pct"] == 0


# ── calc_hedge_type ──────────────────────────────────────────


def test_hedge_non_zero_qe_off():
    from engines.masam_engine import calc_hedge_type
    result = calc_hedge_type("NON_ZERO", False, "QE_OFF")
    assert result["type"] == "TLT"


def test_hedge_zero_rate():
    from engines.masam_engine import calc_hedge_type
    result = calc_hedge_type("ZERO", False, "QE_OFF")
    assert result["type"] == "IAU_GLD_TIP"


def test_hedge_qe_active():
    from engines.masam_engine import calc_hedge_type
    result = calc_hedge_type("NON_ZERO", True, "QE_ON")
    assert result["type"] == "IAU_GLD_TIP"


def test_hedge_ambiguous():
    from engines.masam_engine import calc_hedge_type
    result = calc_hedge_type("NON_ZERO", False, "AMBIGUOUS")
    assert result["type"] == "DOLLAR"
