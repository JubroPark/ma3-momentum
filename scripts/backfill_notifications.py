"""notifications.json 1회성 백필 — masam.json의 git 히스토리에서 최근 30일
마삼 모드 전환·시총 순위 역전을 재구성한다. 권장 비중은 대상 아님(스펙 참고).
실행: python3 scripts/backfill_notifications.py
"""
import json
import subprocess
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "app/public/data"


def git_show(sha: str, path: str) -> dict:
    result = subprocess.run(
        ["git", "show", f"{sha}:{path}"], capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def build_events(cutoff_days: int = 30) -> list[dict]:
    cutoff = date.today() - timedelta(days=cutoff_days)
    shas = subprocess.run(
        ["git", "log", "--reverse", "--format=%H", "--since", cutoff.isoformat(),
         "--", "app/public/data/masam.json"],
        capture_output=True, text=True, cwd=ROOT, check=True,
    ).stdout.split()

    events = []
    prev_mode = None
    prev_leader = None
    for sha in shas:
        snapshot = git_show(sha, "app/public/data/masam.json")
        as_of = snapshot.get("as_of")
        mode = snapshot.get("mode")
        leader = snapshot.get("leader_status", {}).get("rank1_ticker")
        if not as_of:
            continue
        if prev_mode is not None and mode != prev_mode:
            events.append({"date": as_of, "type": "masam_mode", "text": f"{prev_mode} → {mode} 전환"})
        if prev_leader is not None and leader and leader != prev_leader:
            events.append({"date": as_of, "type": "leader_swap", "text": f"1등주가 {prev_leader} → {leader}로 바뀌었습니다"})
        prev_mode, prev_leader = mode, leader
    return events


def main():
    events = build_events()
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    events = [e for e in events if e["date"] >= cutoff]
    out = DATA / "notifications.json"
    out.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"백필 완료: {len(events)}건 → {out}")
    for e in events:
        print(f"  {e['date']}  [{e['type']}]  {e['text']}")


if __name__ == "__main__":
    main()
