from datetime import date
from fetch_eod import update_masam_state


def test_early_release_not_reverted():
    """올인 트리거로 조기 해제(released_date > 마지막 마삼)되면 다음 배치에서 CRISIS로 복구하지 않음"""
    ex = {"mode": "NORMAL", "released_date": "2026-11-10",
          "masam": {"month_count": 1, "last_masam_date": "2026-11-05"}}
    _, mode = update_masam_state(ex, date(2026, 11, 11), 0.5, date(2026, 11, 11))
    assert mode == "NORMAL"
    # 해제일이 마삼 이전이면 기존처럼 위기 기간 내 복구
    _, mode = update_masam_state({**ex, "released_date": "2026-07-06"}, date(2026, 11, 11), 0.5, date(2026, 11, 11))
    assert mode == "CRISIS"
    # 조기 해제 후 새 마삼이 나면 다시 CRISIS
    st, mode = update_masam_state(ex, date(2026, 11, 13), -3.5, date(2026, 11, 12))
    assert mode == "CRISIS" and st["month_count"] == 2
