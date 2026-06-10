import pytest
import pandas as pd
import numpy as np
from datetime import date


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


def test_allocation_rebalancing_no_drawdown():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("REBALANCING", None, "NON_ZERO", ath_drawdown_pct=0.0)
    assert result["stock_pct"] == 100
    assert result["cash_pct"] == 0


def test_allocation_rebalancing_1_level():
    from engines.masam_engine import calc_target_allocation
    # ATH -3% → level=1 (floor(3/2.5)=1) → 10% 현금화 → stock 90%
    result = calc_target_allocation("REBALANCING", None, "NON_ZERO", ath_drawdown_pct=-3.0)
    assert result["stock_pct"] == 90
    assert result["cash_pct"] == 10


def test_allocation_rebalancing_capped_at_max():
    from engines.masam_engine import calc_target_allocation
    # ATH -20% → level=8 → 80% 현금화, but max=25 → cash 25%, stock 75%
    result = calc_target_allocation("REBALANCING", None, "NON_ZERO",
                                    ath_drawdown_pct=-20.0, max_rebalancing_pct=25)
    assert result["stock_pct"] == 75
    assert result["cash_pct"] == 25


def test_allocation_crisis_non_zero_level0():
    from engines.masam_engine import calc_target_allocation
    # ATH -3% → level=0 (floor(3/5)=0) → stock 0%
    result = calc_target_allocation("CRISIS_STAKING", None, "NON_ZERO", ath_drawdown_pct=-3.0)
    assert result["stock_pct"] == 0
    assert result["cash_pct"] == 100


def test_allocation_crisis_non_zero_level1():
    from engines.masam_engine import calc_target_allocation
    # ATH -6% → level=1 (floor(6/5)=1) → stock 10%
    result = calc_target_allocation("CRISIS_STAKING", None, "NON_ZERO", ath_drawdown_pct=-6.0)
    assert result["stock_pct"] == 10
    assert result["cash_pct"] == 90


def test_allocation_crisis_non_zero_level5():
    from engines.masam_engine import calc_target_allocation
    # ATH -26% → level=5 → stock 50% ("초기 50%" 상태)
    result = calc_target_allocation("CRISIS_STAKING", None, "NON_ZERO", ath_drawdown_pct=-26.0)
    assert result["stock_pct"] == 50


def test_allocation_crisis_non_zero_hedge_tlt():
    from engines.masam_engine import calc_target_allocation
    # hedge_type=TLT → non_stock goes to hedge_pct
    result = calc_target_allocation("CRISIS_STAKING", None, "NON_ZERO",
                                    ath_drawdown_pct=-11.0, hedge_type="TLT")
    assert result["stock_pct"] == 20
    assert result["hedge_pct"] == 80
    assert result["cash_pct"] == 0


def test_allocation_crisis_zero_level1():
    from engines.masam_engine import calc_target_allocation
    # ATH -3% → level=1 (floor(3/2.5)=1) → stock 10%
    result = calc_target_allocation("CRISIS_STAKING", None, "ZERO", ath_drawdown_pct=-3.0)
    assert result["stock_pct"] == 10


def test_allocation_panic_emergency():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("PANIC", "EMERGENCY", "NON_ZERO", ath_drawdown_pct=-30.0)
    assert result["stock_pct"] == 0
    assert result["cash_pct"] == 100


def test_allocation_panic_basic_dollar():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("PANIC", "BASIC", "NON_ZERO",
                                    ath_drawdown_pct=-30.0, hedge_type="DOLLAR")
    assert result["stock_pct"] == 0
    assert result["cash_pct"] == 100
    assert result["hedge_pct"] == 0


def test_allocation_panic_basic_tlt():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("PANIC", "BASIC", "NON_ZERO",
                                    ath_drawdown_pct=-30.0, hedge_type="TLT")
    assert result["stock_pct"] == 0
    assert result["hedge_pct"] == 100
    assert result["cash_pct"] == 0


def test_allocation_sum_always_100():
    from engines.masam_engine import calc_target_allocation
    cases = [
        ("REBALANCING", None, "NON_ZERO", -10.0, "DOLLAR"),
        ("CRISIS_STAKING", None, "NON_ZERO", -11.0, "TLT"),
        ("CRISIS_STAKING", None, "ZERO", -5.0, "IAU_GLD_TIP"),
        ("PANIC", "EMERGENCY", "NON_ZERO", -40.0, "DOLLAR"),
        ("PANIC", "BASIC", "NON_ZERO", -40.0, "TLT"),
    ]
    for mode, panic_type, rate_env, dd, ht in cases:
        r = calc_target_allocation(mode, panic_type, rate_env, dd, ht)
        total = r["stock_pct"] + r["hedge_pct"] + r["cash_pct"]
        assert total == 100, f"{mode}/{panic_type}/{rate_env}: total={total}"


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


# ── _calc_rsi14 ───────────────────────────────────────────────


def test_rsi14_all_up_returns_near_100():
    from engines.masam_engine import _calc_rsi14
    closes = pd.Series([float(100 + i) for i in range(20)])
    rsi = _calc_rsi14(closes)
    assert rsi is not None
    assert rsi == pytest.approx(100.0, abs=1.0)


def test_rsi14_insufficient_data_returns_none():
    from engines.masam_engine import _calc_rsi14
    closes = pd.Series([100.0, 101.0, 102.0])
    rsi = _calc_rsi14(closes)
    assert rsi is None


def test_rsi14_normal_range():
    from engines.masam_engine import _calc_rsi14
    np.random.seed(42)
    closes = pd.Series(100.0 + np.cumsum(np.random.randn(50)))
    rsi = _calc_rsi14(closes)
    assert rsi is not None
    assert 0 <= rsi <= 100


# ── check_allin_conditions ────────────────────────────────────


def _make_series(closes: list, start: str = "2026-01-02") -> pd.Series:
    dates = pd.bdate_range(start, periods=len(closes))
    return pd.Series(closes, index=dates)


def test_allin_cond1_met_after_31_days():
    from engines.masam_engine import check_allin_conditions
    from datetime import date
    last_masam = pd.Timestamp("2026-05-09")  # 32일 전
    ixic = _make_series([100.0] * 20)
    leader = _make_series([100.0] * 20)
    conds = check_allin_conditions(last_masam, ixic, leader, date(2026, 6, 10))
    assert conds[0]["met"] is True


def test_allin_cond1_not_met_within_30_days():
    from engines.masam_engine import check_allin_conditions
    from datetime import date
    last_masam = pd.Timestamp("2026-06-05")  # 5일 전
    ixic = _make_series([100.0] * 20)
    leader = _make_series([100.0] * 20)
    conds = check_allin_conditions(last_masam, ixic, leader, date(2026, 6, 10))
    assert conds[0]["met"] is False


def test_allin_cond2_8_consecutive_up():
    from engines.masam_engine import check_allin_conditions
    from datetime import date
    closes = [float(100 + i) for i in range(9)]  # 9일 연속 상승
    ixic = _make_series(closes)
    leader = _make_series([100.0] * 9)
    conds = check_allin_conditions(None, ixic, leader, date(2026, 1, 13))
    assert conds[1]["met"] is True


def test_allin_cond2_not_met_with_down_day():
    from engines.masam_engine import check_allin_conditions
    from datetime import date
    closes = [100.0, 101.0, 100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5]
    ixic = _make_series(closes)
    leader = _make_series([100.0] * 9)
    conds = check_allin_conditions(None, ixic, leader, date(2026, 1, 13))
    assert conds[1]["met"] is False  # 3번째 날 하락


def test_allin_cond4_ixic_ath():
    from engines.masam_engine import check_allin_conditions
    from datetime import date
    closes = [100.0, 95.0, 98.0, 101.0]  # 101 = 신고점
    ixic = _make_series(closes)
    leader = _make_series([100.0, 95.0, 98.0, 97.0])  # 리더는 신고점 아님
    conds = check_allin_conditions(None, ixic, leader, date(2026, 1, 5))
    assert conds[3]["met"] is True
    assert conds[2]["met"] is False


# ── build_masam_json ──────────────────────────────────────────


def test_build_masam_json_structure():
    from engines.masam_engine import build_masam_json
    from datetime import date

    result = build_masam_json(
        as_of=date(2026, 6, 10),
        mode="CRISIS_STAKING",
        panic_type=None,
        rate_env="NON_ZERO",
        qe_active=False,
        masam_month_count=1,
        masam_cumulative=1,
        last_masam_date=pd.Timestamp("2026-06-05"),
        leader_status={"rank1_ticker": "NVDA", "rank1_mcap": 3_500_000_000_000,
                       "rank2_ticker": "AAPL", "rank2_mcap": 3_100_000_000_000,
                       "gap_pct": 11.4, "overtake_detected": False, "gap_below_10pct": False},
        target_allocation={"stock_pct": 50, "hedge_pct": 30, "cash_pct": 20, "label": "50% 말뚝"},
        hedge_allocation={"type": "TLT", "rationale": "비제로+QE이전", "exit_trigger": ""},
        distance_to_triggers={"v_allin_pct_needed": 10.0, "emergency_allin_pct_away": -1.5},
        allin_conditions=[{"id": 1, "label": "한달+1일 무마삼", "met": False, "grade": "약"}],
        additional_buy_signal={"rsi14": 55.0, "mfi14": None, "both_below_50": False, "label": ""},
        recommended_action="말뚝박기 진입",
        alerts=[],
    )

    assert result["as_of"] == "2026-06-10"
    assert result["mode"] == "CRISIS_STAKING"
    assert result["masam"]["month_count"] == 1
    assert result["masam"]["last_masam_date"] == "2026-06-05"
    assert result["leader_status"]["rank1_ticker"] == "NVDA"
    assert result["target_allocation"]["stock_pct"] == 50
    assert result["hedge_allocation"]["type"] == "TLT"


# ── additional coverage ───────────────────────────────────────


def test_allin_cond1_none_masam_date_returns_false():
    from engines.masam_engine import check_allin_conditions
    ixic = _make_series([100.0] * 20)
    leader = _make_series([100.0] * 20)
    conds = check_allin_conditions(None, ixic, leader, date(2026, 6, 10))
    assert conds[0]["met"] is False


def test_calc_distance_to_triggers_non_zero():
    from engines.masam_engine import calc_distance_to_triggers
    closes = pd.Series([100.0, 95.0, 90.0, 80.0])  # ATH=100, current=80
    result = calc_distance_to_triggers(closes, "NON_ZERO")
    assert result["v_allin_pct_needed"] == 10.0
    # emergency_level = 100 * 0.70 = 70. current=80 → (80/70 - 1)*100 ≈ +14.29%
    assert result["emergency_allin_pct_away"] == pytest.approx(14.29, abs=0.1)


def test_calc_distance_to_triggers_zero():
    from engines.masam_engine import calc_distance_to_triggers
    closes = pd.Series([100.0, 95.0])
    result = calc_distance_to_triggers(closes, "ZERO")
    assert result["v_allin_pct_needed"] == 5.0


def test_check_additional_buy_signal_below_50():
    from engines.masam_engine import check_additional_buy_signal
    closes = pd.Series([float(100 - i * 0.5) for i in range(20)])  # downtrend → RSI < 50
    result = check_additional_buy_signal(closes)
    assert result["mfi14"] is None
    assert result["rsi14"] is not None
    assert result["both_below_50"] is True


def test_check_additional_buy_signal_above_50():
    from engines.masam_engine import check_additional_buy_signal
    closes = pd.Series([float(100 + i) for i in range(20)])  # uptrend → RSI > 50
    result = check_additional_buy_signal(closes)
    assert result["both_below_50"] is False


def test_build_masam_json_panic_reentry_tranches():
    from engines.masam_engine import build_masam_json
    from datetime import date
    result = build_masam_json(
        as_of=date(2026, 6, 10),
        mode="PANIC",
        panic_type="BASIC",
        rate_env="NON_ZERO",
        qe_active=False,
        masam_month_count=4,
        masam_cumulative=4,
        last_masam_date=pd.Timestamp("2026-06-05"),
        leader_status={"rank1_ticker": "NVDA", "rank1_mcap": 3_500_000_000_000,
                       "rank2_ticker": "AAPL", "rank2_mcap": 3_100_000_000_000,
                       "gap_pct": 11.4, "overtake_detected": False, "gap_below_10pct": False},
        target_allocation={"stock_pct": 0, "hedge_pct": 70, "cash_pct": 30, "label": "헤지"},
        hedge_allocation={"type": "TLT", "rationale": "", "exit_trigger": ""},
        distance_to_triggers={"v_allin_pct_needed": 10.0, "emergency_allin_pct_away": 5.0},
        allin_conditions=[],
        additional_buy_signal={"rsi14": None, "mfi14": None, "both_below_50": False, "label": ""},
        recommended_action="헤지 운용",
        alerts=[],
    )
    assert result["panic_reentry"]["tranches"] == [35, 35, 30]
