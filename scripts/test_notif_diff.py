"""fetch_eod.py의 알림 이벤트 diff 로직 단독 검증. 실행: python3 scripts/test_notif_diff.py"""
from datetime import date, timedelta


def build_notif_events(prev_mode, new_mode, prev_rank1, rank1_ticker, today):
    events = []
    if prev_mode != new_mode:
        events.append({
            "date": today.isoformat(), "type": "masam_mode",
            "text": f"{prev_mode} → {new_mode} 전환",
        })
    if prev_rank1 and prev_rank1 != rank1_ticker:
        events.append({
            "date": today.isoformat(), "type": "leader_swap",
            "text": f"1등주가 {prev_rank1} → {rank1_ticker}로 바뀌었습니다",
        })
    return events


def trim_to_30_days(notifications, today):
    cutoff = (today - timedelta(days=30)).isoformat()
    return [n for n in notifications if n.get("date", "") >= cutoff]


def test_no_change_produces_no_event():
    today = date(2026, 8, 3)
    assert build_notif_events("NORMAL", "NORMAL", "NVDA", "NVDA", today) == []


def test_mode_change_produces_event():
    today = date(2026, 8, 3)
    events = build_notif_events("NORMAL", "CRISIS", "NVDA", "NVDA", today)
    assert len(events) == 1
    assert events[0]["type"] == "masam_mode"
    assert events[0]["date"] == "2026-08-03"


def test_leader_swap_produces_event():
    today = date(2026, 8, 3)
    events = build_notif_events("NORMAL", "NORMAL", "NVDA", "AAPL", today)
    assert len(events) == 1
    assert events[0]["type"] == "leader_swap"
    assert "NVDA" in events[0]["text"] and "AAPL" in events[0]["text"]


def test_both_change_same_day_produces_two_events():
    today = date(2026, 8, 3)
    events = build_notif_events("CRISIS", "NORMAL", "NVDA", "AAPL", today)
    assert len(events) == 2


def test_first_run_no_prev_leader_no_event():
    today = date(2026, 8, 3)
    events = build_notif_events("NORMAL", "NORMAL", None, "NVDA", today)
    assert events == []


def test_trim_drops_old_events():
    today = date(2026, 8, 3)
    notifications = [
        {"date": "2026-06-01", "type": "masam_mode", "text": "old"},
        {"date": "2026-07-20", "type": "masam_mode", "text": "recent"},
        {"date": "2026-08-03", "type": "leader_swap", "text": "today"},
    ]
    result = trim_to_30_days(notifications, today)
    assert result == [
        {"date": "2026-07-20", "type": "masam_mode", "text": "recent"},
        {"date": "2026-08-03", "type": "leader_swap", "text": "today"},
    ]


if __name__ == "__main__":
    test_no_change_produces_no_event()
    test_mode_change_produces_event()
    test_leader_swap_produces_event()
    test_both_change_same_day_produces_two_events()
    test_first_run_no_prev_leader_no_event()
    test_trim_drops_old_events()
    print("OK — all notif diff checks passed")
