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
        return {"stock_pct": 25, "hedge_pct": 35, "cash_pct": 40, "label": "25% 말뚝박기 (제로금리)"}
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
