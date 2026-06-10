"""마삼 3-모드 상태머신 — 순수 함수, I/O 없음."""
from __future__ import annotations
from datetime import date
import pandas as pd
import numpy as np


# ── 모드 결정 ──────────────────────────────────────────────────


def determine_mode(
    masam_month_count: int,
    prev_year_return: float | None,
) -> tuple[str, str | None]:
    """
    이번 달 마삼 횟수와 전년 역년 수익률로 3-모드 결정.

    Returns:
        (mode, panic_type)
        mode: "REBALANCING" | "CRISIS_STAKING" | "PANIC"
        panic_type: None | "BASIC" | "EMERGENCY"

    규칙 (CLAUDE.md §5-2):
        month_count >= 4 → PANIC
          prev_year_return >= 45% → EMERGENCY
          else → BASIC
        month_count >= 1 → CRISIS_STAKING
        else → REBALANCING
    """
    if masam_month_count >= 4:
        if prev_year_return is not None and prev_year_return >= 45.0:
            return "PANIC", "EMERGENCY"
        return "PANIC", "BASIC"
    if masam_month_count >= 1:
        return "CRISIS_STAKING", None
    return "REBALANCING", None


# ── 비중 배분 ──────────────────────────────────────────────────


def calc_target_allocation(
    mode: str,
    panic_type: str | None,
    rate_env: str,
) -> dict:
    """
    모드별 목표 비중 (주식/헤지/현금 %).

    REBALANCING   : 주식 100%
    CRISIS_STAKING: 비제로 → 50% 말뚝 / 제로 → 25% 말뚝
    PANIC EMERGENCY: 현금 100%
    PANIC BASIC   : 주식 0%, 헤지 운용
    """
    if mode == "REBALANCING":
        return {"stock_pct": 100, "hedge_pct": 0, "cash_pct": 0, "label": "1등주 보유 유지"}
    if mode == "CRISIS_STAKING":
        if rate_env == "NON_ZERO":
            return {"stock_pct": 50, "hedge_pct": 30, "cash_pct": 20, "label": "50% 말뚝박기 (비제로금리)"}
        if rate_env == "ZERO":
            return {"stock_pct": 25, "hedge_pct": 35, "cash_pct": 40, "label": "25% 말뚝박기 (제로금리)"}
        raise ValueError(f"calc_target_allocation: unknown rate_env={rate_env!r}")
    if panic_type == "EMERGENCY":
        return {"stock_pct": 0, "hedge_pct": 0, "cash_pct": 100, "label": "현금 100% (공황 비상)"}
    return {"stock_pct": 0, "hedge_pct": 70, "cash_pct": 30, "label": "헤지 운용 (공황 기본)"}


# ── 헤지 배치 ──────────────────────────────────────────────────


def calc_hedge_type(
    rate_env: str,
    qe_active: bool,
    qe_state: str,
) -> dict:
    """
    헤지 자산 배치 결정 (CLAUDE.md §5-2).

    비제로 + QE이전(QE_OFF) → TLT
    제로금리 or QE시작(QE_ON) → IAU+GLD/TIP 1:1
    모호(AMBIGUOUS) or 방향 미상 → DOLLAR
    """
    if qe_active or rate_env == "ZERO":
        return {
            "type": "IAU_GLD_TIP",
            "rationale": "제로금리 or QE 시작 — 금/물가연동채 1:1",
            "exit_trigger": "금리인상 or QE 축소 시 전량 매도 → 현금",
        }
    if rate_env == "NON_ZERO" and qe_state == "QE_OFF":
        return {
            "type": "TLT",
            "rationale": "비제로금리 + QE 이전 — 미국채 장기",
            "exit_trigger": "Fed 금리인하 or QE 시작 → TLT 매도 → IAU or 현금",
        }
    return {
        "type": "DOLLAR",
        "rationale": "QE 여부 모호 — 달러 현금 보유",
        "exit_trigger": "QE 명확해지면 TLT or IAU+GLD+TIP 전환",
    }


# ── RSI14 ────────────────────────────────────────────────────


def _calc_rsi14(close: pd.Series) -> float | None:
    """1등주 종가 기준 RSI14. 데이터 15개 미만이면 None."""
    if len(close) < 15:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    last_loss = float(loss.iloc[-1])
    last_gain = float(gain.iloc[-1])
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0
    rsi = 100 - (100 / (1 + last_gain / last_loss))
    return float(rsi)


# ── 올인 조건 4종 ────────────────────────────────────────────


def check_allin_conditions(
    last_masam_date: "pd.Timestamp | None",
    close_ixic: pd.Series,
    close_leader: pd.Series,
    as_of: date,
) -> list[dict]:
    """
    MODE 2 올인 조건 4종 체크 (CLAUDE.md §5-2).
    1. 한달+1일 무마삼 (≥31일)
    2. 8거래일 연속 상승
    3. 1등주 전고 돌파
    4. 나스닥 전고 돌파
    """
    today = pd.Timestamp(as_of)

    # 조건 1
    cond1 = False
    if last_masam_date is not None:
        cond1 = (today - last_masam_date).days >= 31

    # 조건 2: 최근 8 거래일 모두 양봉
    if len(close_ixic) >= 9:
        last9 = close_ixic.iloc[-9:]
        changes = last9.pct_change().dropna()
        cond2 = len(changes) >= 8 and bool((changes.iloc[-8:] > 0).all())
    else:
        cond2 = False

    # 조건 3: 1등주 신고점
    cond3 = float(close_leader.iloc[-1]) >= float(close_leader.max())

    # 조건 4: 나스닥 신고점
    cond4 = float(close_ixic.iloc[-1]) >= float(close_ixic.max())

    return [
        {"id": 1, "label": "한달+1일 무마삼", "met": cond1, "grade": "약"},
        {"id": 2, "label": "8거래일 연속 상승", "met": cond2, "grade": "중"},
        {"id": 3, "label": "1등주 전고 돌파", "met": cond3, "grade": "강"},
        {"id": 4, "label": "나스닥 전고 돌파", "met": cond4, "grade": "강"},
    ]


# ── 트리거 거리 ───────────────────────────────────────────────


def calc_distance_to_triggers(
    close_ixic: pd.Series,
    rate_env: str,
) -> dict:
    """
    V자 올인 기준 및 긴급 올인 레벨까지 거리.
    v_allin_pct_needed : 비제로 +10%(2구간) / 제로 +5%(2구간)
    emergency_allin_pct_away : 현재가 vs 고점-30% 레벨 거리(%, 양수=아직 멀었음)
    """
    ixic_ath = float(close_ixic.max())
    current = float(close_ixic.iloc[-1])
    if rate_env == "NON_ZERO":
        v_allin_pct_needed = 10.0
    elif rate_env == "ZERO":
        v_allin_pct_needed = 5.0
    else:
        raise ValueError(f"calc_distance_to_triggers: unknown rate_env={rate_env!r}")
    emergency_level = ixic_ath * 0.70
    emergency_allin_pct_away = round((current / emergency_level - 1) * 100, 2)
    return {
        "v_allin_pct_needed": v_allin_pct_needed,
        "emergency_allin_pct_away": emergency_allin_pct_away,
    }


# ── 추가 자금 투입 신호 ───────────────────────────────────────


def check_additional_buy_signal(close_leader: pd.Series) -> dict:
    """추가 자금 투입 조건: 1등주 RSI14 ≤ 50."""
    rsi = _calc_rsi14(close_leader)
    both = rsi is not None and rsi <= 50
    return {
        "rsi14": round(rsi, 1) if rsi is not None else None,
        "mfi14": None,  # volume 데이터 Phase 2에서 추가
        "both_below_50": both,
        "label": "RSI14 ≤ 50 — 추가 자금 투입 조건 충족" if both else "",
    }


# ── masam.json 빌더 ────────────────────────────────────────────


def build_masam_json(
    as_of: date,
    mode: str,
    panic_type: "str | None",
    rate_env: str,
    qe_active: bool,
    masam_month_count: int,
    masam_cumulative: int,
    last_masam_date: "pd.Timestamp | None",
    leader_status: dict,
    target_allocation: dict,
    hedge_allocation: dict,
    distance_to_triggers: dict,
    allin_conditions: list,
    additional_buy_signal: dict,
    recommended_action: str,
    alerts: list,
) -> dict:
    return {
        "as_of": str(as_of),
        "mode": mode,
        "panic_type": panic_type,
        "rate_env": rate_env,
        "qe_active": qe_active,
        "masam": {
            "month_count": masam_month_count,
            "cumulative_count": masam_cumulative,
            "last_masam_date": str(last_masam_date.date()) if last_masam_date else None,
        },
        "leader_status": leader_status,
        "target_allocation": target_allocation,
        "hedge_allocation": hedge_allocation,
        "distance_to_triggers": distance_to_triggers,
        "all_in_conditions": allin_conditions,
        "additional_buy_signal": additional_buy_signal,
        "panic_reentry": {"stage": 0, "next_tranche_pct": 35, "tranches": [35, 35, 30]},
        "recommended_action": recommended_action,
        "alerts": alerts,
    }
