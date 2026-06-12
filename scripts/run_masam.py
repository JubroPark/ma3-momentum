"""마삼 엔진 실행 진입점 — 데이터 수집 + 엔진 평가 + masam.json 저장."""
import os
import json
import sys
from pathlib import Path

from typing import Optional

import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.masam_engine import (
    determine_mode,
    calc_target_allocation,
    calc_hedge_type,
    check_allin_conditions,
    calc_distance_to_triggers,
    check_additional_buy_signal,
    build_masam_json,
)
from engines.market_context import get_market_context
from engines.leader import get_leader_status
from scripts.phase0_poc import _get_close, check_masam

load_dotenv()

_OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "masam.json"


def run() -> dict:
    print("=" * 50)
    print("마삼 엔진 실행")
    print("=" * 50)

    # 1. 데이터 수집
    print("^IXIC 다운로드 중...")
    df_ixic = yf.download("^IXIC", period="2y", auto_adjust=True, progress=False)
    fred = Fred(api_key=os.getenv("FRED_API_KEY"))

    # 2. 기초 지표 (phase0 함수 재사용)
    masam_result = check_masam(df_ixic=df_ixic)
    ctx = get_market_context(fred=fred)

    # 3. 1등주 판정 + 주가 수집 + QQQ
    print("1등주 시총 조회 중...")
    leader = get_leader_status()
    rank1 = leader["rank1_ticker"] or "AAPL"
    print(f"1등주: {rank1}")
    df_leader = yf.download(rank1, period="1y", auto_adjust=True, progress=False)
    df_qqq = yf.download("QQQ", period="1y", auto_adjust=True, progress=False)

    close_ixic = _get_close(df_ixic)
    close_leader = _get_close(df_leader)
    as_of = close_ixic.index[-1].date()

    # 4. 상태 결정
    mode, panic_type = determine_mode(masam_result["month_count"], masam_result["prev_year_return"])
    hedge_alloc = calc_hedge_type(ctx["rate_env"], ctx["qe_active"], ctx["qe_state"])

    # 그리드 기준은 나스닥이 아니라 1등주 전고점 대비 낙폭
    # REBALANCING: 1등주 종가 현재가 vs 1등주 ATH
    # CRISIS_STAKING: 마삼 발생 후 1등주 장중 저가 기준 (낮은 가격에 최대한 매수하기 위해)
    #   — 회복돼도 찍힌 구간은 유지
    low_leader = df_leader["Low"].squeeze().dropna()
    leader_ath = float(close_leader.max())
    if mode == "CRISIS_STAKING":
        crisis_start = masam_result.get("first_masam_date") or masam_result.get("latest_masam_date")
        if crisis_start is not None:
            since_masam = low_leader[low_leader.index >= crisis_start]
            crisis_low = float(since_masam.min()) if len(since_masam) > 0 else float(close_leader.iloc[-1])
        else:
            crisis_low = float(close_leader.iloc[-1])
        ath_drawdown_pct = round((crisis_low / leader_ath - 1) * 100, 2)
    else:
        ath_drawdown_pct = round((float(close_leader.iloc[-1]) / leader_ath - 1) * 100, 2)

    target_alloc = calc_target_allocation(
        mode, panic_type, ctx["rate_env"],
        ath_drawdown_pct=ath_drawdown_pct,
        hedge_type=hedge_alloc["type"],
    )

    leader_current = float(close_leader.iloc[-1])
    leader_crisis_low = crisis_low if mode == "CRISIS_STAKING" else None

    # QQQ 가격 계산
    close_qqq = _get_close(df_qqq)
    low_qqq = df_qqq["Low"].squeeze().dropna()
    qqq_ath = float(close_qqq.max())
    qqq_current = float(close_qqq.iloc[-1])
    if mode == "CRISIS_STAKING" and crisis_start is not None:
        since_qqq = low_qqq[low_qqq.index >= crisis_start]
        qqq_crisis_low: "float | None" = float(since_qqq.min()) if len(since_qqq) > 0 else None
    else:
        qqq_crisis_low = None

    allin_conds = check_allin_conditions(
        masam_result["latest_masam_date"], close_ixic, close_leader, as_of
    )
    dist = calc_distance_to_triggers(
        close_leader, ctx["rate_env"],
        leader_ath=leader_ath,
        crisis_low=leader_crisis_low,
    )
    buy_signal = check_additional_buy_signal(close_leader)

    recommended = _build_recommended_action(mode, panic_type, ctx["rate_env"])
    alerts = _build_alerts(mode, panic_type, masam_result, buy_signal)

    # 5. JSON 빌드 + 저장
    result = build_masam_json(
        as_of=as_of,
        mode=mode,
        panic_type=panic_type,
        rate_env=ctx["rate_env"],
        qe_active=ctx["qe_active"],
        masam_month_count=masam_result["month_count"],
        masam_cumulative=masam_result["month_count"],
        last_masam_date=masam_result["latest_masam_date"],
        leader_status=leader,
        leader_prices={
            "ath": round(leader_ath, 2),
            "current": round(leader_current, 2),
            "crisis_low": round(leader_crisis_low, 2) if leader_crisis_low is not None else None,
        },
        qqq_prices={
            "ath": round(qqq_ath, 2),
            "current": round(qqq_current, 2),
            "crisis_low": round(qqq_crisis_low, 2) if qqq_crisis_low is not None else None,
        },
        target_allocation=target_alloc,
        hedge_allocation=hedge_alloc,
        distance_to_triggers=dist,
        allin_conditions=allin_conds,
        additional_buy_signal=buy_signal,
        recommended_action=recommended,
        alerts=alerts,
    )

    _OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print(f"\nmasam.json 저장 완료: {_OUTPUT_PATH}")
    print(f"모드: {mode} / panic_type: {panic_type}")
    print(f"1등주: {leader['rank1_ticker']} / 금리: {ctx['rate_env']} / QE: {ctx['qe_state']}")
    return result


def _build_recommended_action(mode: str, panic_type: Optional[str], rate_env: str) -> str:
    if mode == "REBALANCING":
        return "1등주 보유 유지. 전고점 대비 -2.5% 하락마다 10% 현금화."
    if mode == "CRISIS_STAKING":
        pct = "50%" if rate_env == "NON_ZERO" else "25%"
        interval = "-5% 하락마다" if rate_env == "NON_ZERO" else "-2.5% 하락마다"
        return f"말뚝박기 진입. 초기 {pct} 매수. {interval} +10% 추가 매수."
    if panic_type == "EMERGENCY":
        return "공황 비상: 전량 매도 → 현금 100%. 고점 -30% 긴급 올인 없음. V자 6구간(+30%) 기준 적용."
    return "공황 확정: 전량 매도 → 헤지 자산 운용. 해제 조건 모니터링."


def _build_alerts(
    mode: str, panic_type: Optional[str], masam_result: dict, buy_signal: dict
) -> list:
    alerts = []
    if mode == "PANIC" and panic_type == "EMERGENCY":
        alerts.append("PANIC_EMERGENCY: 고점 -30% 몰빵 없음 · V자 6구간(+30%) 기준 적용 중")
    month_count = masam_result["month_count"]
    if 1 <= month_count <= 3:
        alerts.append(f"이번 달 마삼 {month_count}회 — 공황 확정까지 {4 - month_count}회 남음")
    if buy_signal.get("both_below_50"):
        alerts.append("추가 자금 투입 조건 충족: 1등주 RSI14 <= 50")
    return alerts


if __name__ == "__main__":
    run()
