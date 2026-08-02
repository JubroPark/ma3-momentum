# 마삼룰 알림 히스토리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 마삼룰 화면 상단바에 알림(벨) 아이콘을 추가하고, 클릭 시 최근 30일간의 마삼 모드 전환·시총 순위 역전(서버 기록)과 권장 비중 변경(기기 로컬 기록)을 합쳐서 보여주는 드로어를 만든다.

**Architecture:** 마삼 모드/시총 순위는 서버 계산값이라 `fetch_eod.py`가 매 배치 전일 대비 diff해서 `app/public/data/notifications.json`에 append(최근 30일 트림)한다. 권장 비중은 기기별 localStorage 설정(`portfolio_ratio`, `max_pct_*`)에 의존해 서버가 계산할 수 없으므로, `app.html`이 페이지 로드마다 클라이언트에서 계산값을 diff해 `localStorage['alloc_history']`에 기록한다. 벨 아이콘 클릭 시 두 소스를 합쳐 최신순으로 드로어에 표시한다.

**Tech Stack:** Python 3(`scripts/fetch_eod.py`, 표준 라이브러리만), 순수 JS(`app/public/app.html`, 프레임워크 없음), 기존 `#alloc-overlay`/`#alloc-drawer` 하단 드로어 패턴 재사용.

## Global Constraints

- 서버 API 없음 — `app.html`은 `/data/*.json` 정적 파일만 fetch한다 (CLAUDE.md §2).
- 판정용 데이터는 EOD 배치가 기준. 이 기능은 표시/기록용이라 신호 로직에 영향 주지 않는다.
- 히스토리 보관 기간은 30일 고정(마삼 모드/시총 순위는 서버 측, 권장 비중은 클라이언트 측 각각 독립 트림).
- 권장 비중 히스토리는 기능 추가 시점부터 새로 쌓는다 — 과거분 재계산 백필 안 함(스펙 §3에서 합의됨, 로직이 최근 계속 바뀌어 재계산값이 실제 과거 화면값과 다를 수 있기 때문).
- 벨 아이콘은 마삼룰 화면(발견/관심/피드/설정)에만 보이고 모멘텀 화면(모멘텀/관심종목)에는 보이지 않아야 한다. 피드/설정은 두 전략이 topbar 마크업을 공유하므로 조건부 표시가 필요하다(CLAUDE.md §9-2).
- 커밋은 사용자가 명시적으로 요청할 때만 한다(프로젝트 표준 규칙). 각 태스크의 "커밋" 스텝은 사용자 승인 후 실행자가 별도로 확인받고 진행할 것.

---

## Task 1: 백엔드 — 알림 이벤트 기록 (`fetch_eod.py`)

**Files:**
- Modify: `scripts/fetch_eod.py`

**Interfaces:**
- Produces: `app/public/data/notifications.json` — JSON 배열, 각 원소 `{"date": "YYYY-MM-DD", "type": "masam_mode"|"leader_swap", "text": "..."}`. 이후 프론트(Task 4)가 그대로 fetch해서 소비한다.

- [ ] **Step 1: `save_json(DATA / "masam.json", masam_out)` 호출 직후에 알림 기록 로직 추가**

`scripts/fetch_eod.py`에서 아래 줄을 찾는다(약 541번째 줄 부근):

```python
    save_json(DATA / "masam.json", masam_out)
```

이 줄 바로 다음에 아래 블록을 삽입한다:

```python
    # 10. 알림 히스토리: 마삼 모드 전환·시총 순위 역전 기록 (최근 30일 유지)
    # ponytail: 서버가 계산 가능한 이벤트만 기록. 권장 비중은 기기별 localStorage
    # 설정에 의존해 서버가 재현 불가 → 프론트(app.html)가 클라이언트에서 별도 기록.
    notif_events = []
    if prev_mode != new_mode:
        notif_events.append({
            "date": today.isoformat(),
            "type": "masam_mode",
            "text": f"{prev_mode} → {new_mode} 전환",
        })
    prev_rank1 = existing_masam.get("leader_status", {}).get("rank1_ticker")
    if prev_rank1 and prev_rank1 != rank1_ticker:
        notif_events.append({
            "date": today.isoformat(),
            "type": "leader_swap",
            "text": f"1등주가 {prev_rank1} → {rank1_ticker}로 바뀌었습니다",
        })
    if notif_events:
        notifications = load_json(DATA / "notifications.json")
        if not isinstance(notifications, list):
            notifications = []
        notifications.extend(notif_events)
        cutoff = (today - timedelta(days=30)).isoformat()
        notifications = [n for n in notifications if n.get("date", "") >= cutoff]
        save_json(DATA / "notifications.json", notifications)
        print(f"  알림 기록: {len(notif_events)}건 추가 (보관 {len(notifications)}건)")
```

`timedelta`는 파일 상단에 이미 `from datetime import date, timedelta`로 import되어 있으므로 추가 import 불필요.

- [ ] **Step 2: 로컬에서 독립 실행되는 검증 스크립트 작성**

새 파일 `scripts/test_notif_diff.py`를 만든다(이 저장소에 pytest 등 테스트 프레임워크가 없으므로, 프로젝트 관례대로 `assert` 기반 단독 실행 스크립트로 작성):

```python
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
```

- [ ] **Step 3: 검증 스크립트 실행**

Run: `python3 scripts/test_notif_diff.py`
Expected: `OK — all notif diff checks passed` 출력, 예외 없음.

- [ ] **Step 4: fetch_eod.py 문법 확인**

Run: `python3 -m py_compile scripts/fetch_eod.py`
Expected: 에러 없이 종료(exit code 0).

- [ ] **Step 5: 커밋 (사용자 승인 후)**

```bash
git add scripts/fetch_eod.py scripts/test_notif_diff.py
git commit -m "feat: EOD 배치에 마삼 모드·시총 순위 변동 알림 기록 추가"
```

---

## Task 2: 백엔드 — 최근 30일 백필 (`notifications.json` 초기 시드)

**Files:**
- Create: `scripts/backfill_notifications.py` (1회성 유틸리티, 저장소에 유지해 재실행/재현 가능하게 함)
- Create (실행 결과물): `app/public/data/notifications.json`

**Interfaces:**
- Consumes: `git log`로 조회 가능한 `app/public/data/masam.json`의 과거 커밋들(각 커밋의 `mode`, `leader_status.rank1_ticker`, `as_of` 필드)
- Produces: `app/public/data/notifications.json` — Task 1과 동일한 스키마

- [ ] **Step 1: 백필 스크립트 작성**

`scripts/backfill_notifications.py`:

```python
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
```

- [ ] **Step 2: 실행해서 실제 결과 확인**

Run: `python3 scripts/backfill_notifications.py`
Expected: 콘솔에 이벤트 목록 출력(최소 아래 3건이 포함되어야 함 — 실제 날짜는 실행 시점 기준 30일 윈도우에 따라 달라질 수 있음):
```
2026-07-06  [masam_mode]  CRISIS → NORMAL 전환
2026-07-27  [leader_swap]  1등주가 NVDA → AAPL로 바뀌었습니다
2026-07-31  [leader_swap]  1등주가 AAPL → NVDA로 바뀌었습니다
```
(30일 윈도우가 지나면서 이 중 오래된 항목은 자연히 빠질 수 있음 — `date.today()` 기준 30일 이내인 것만 채워지면 정상.)

- [ ] **Step 3: 생성된 JSON 유효성 확인**

Run: `python3 -c "import json; d=json.load(open('app/public/data/notifications.json')); print(len(d), 'events'); [print(e) for e in d]"`
Expected: 에러 없이 이벤트 목록 출력.

- [ ] **Step 4: 커밋 (사용자 승인 후)**

```bash
git add scripts/backfill_notifications.py app/public/data/notifications.json
git commit -m "feat: 알림 히스토리 최근 30일 백필 (마삼 모드·시총 순위)"
```

---

## Task 3: 프론트 — 벨 아이콘 + 드로어 마크업

**Files:**
- Modify: `app/public/app.html`

**Interfaces:**
- Produces: DOM에 `#notif-overlay`/`#notif-drawer`/`#notif-drawer-content` 존재, 전역 함수 `openNotifDrawer()`/`closeNotifDrawer()`/`injectNotifBell()` 정의됨. Task 4가 `openNotifDrawer()` 내부에서 렌더링할 데이터(`window._notifEvents`)를 채워 넣는다.
- Consumes: 기존 `.refresh-btn` CSS 클래스(32px 원형 버튼 스타일), 기존 `#alloc-overlay`/`#alloc-drawer` 패턴(동일한 open/close 애니메이션 구조를 복제).

- [ ] **Step 1: 드로어 마크업 추가**

`app/public/app.html`에서 아래 블록을 찾는다(약 2914~2921번째 줄, `<!-- ===== 권장 비중 자세히 보기 드로어 ===== -->` 바로 아래):

```html
<!-- ===== 권장 비중 자세히 보기 드로어 ===== -->
<div id="alloc-overlay" onclick="closeAllocDetail()" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:200;transition:opacity .28s ease;opacity:0;backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);"></div>
<div id="alloc-drawer" style="display:none;position:fixed;bottom:0;left:50%;transform:translateX(-50%) translateY(100%);width:100%;max-width:430px;background:#1D1D25;border-radius:24px 24px 0 0;z-index:201;padding:0 0 env(safe-area-inset-bottom,24px);transition:transform .32s cubic-bezier(.32,1.2,.48,1);max-height:80dvh;overflow:hidden;box-shadow:0 -8px 48px rgba(0,0,0,.55);">
  <div style="padding:14px 20px 0;display:flex;align-items:center;justify-content:center;">
    <div style="width:40px;height:4px;border-radius:2px;background:#36363F;"></div>
  </div>
  <div id="alloc-drawer-content" style="padding:20px 20px 40px;overflow-y:auto;max-height:calc(80dvh - 40px);-webkit-overflow-scrolling:touch;overscroll-behavior:contain;"></div>
</div>
```

이 블록 바로 다음(그 뒤의 `<script>` 태그 이전)에 아래를 추가한다:

```html

<!-- ===== 알림 히스토리 드로어 ===== -->
<div id="notif-overlay" onclick="closeNotifDrawer()" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:200;transition:opacity .28s ease;opacity:0;backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);"></div>
<div id="notif-drawer" style="display:none;position:fixed;bottom:0;left:50%;transform:translateX(-50%) translateY(100%);width:100%;max-width:430px;background:#1D1D25;border-radius:24px 24px 0 0;z-index:201;padding:0 0 env(safe-area-inset-bottom,24px);transition:transform .32s cubic-bezier(.32,1.2,.48,1);max-height:80dvh;overflow:hidden;box-shadow:0 -8px 48px rgba(0,0,0,.55);">
  <div style="padding:14px 20px 0;display:flex;align-items:center;justify-content:center;">
    <div style="width:40px;height:4px;border-radius:2px;background:#36363F;"></div>
  </div>
  <div id="notif-drawer-content" style="padding:20px 20px 40px;overflow-y:auto;max-height:calc(80dvh - 40px);-webkit-overflow-scrolling:touch;overscroll-behavior:contain;"></div>
</div>
```

- [ ] **Step 2: open/close 함수 + 벨 주입 함수 추가**

같은 파일에서 `closeAllocDetail()` 함수 정의 끝(약 3134~3140번째 줄)을 찾는다:

```javascript
function closeAllocDetail() {
  const overlay = document.getElementById('alloc-overlay');
  const drawer  = document.getElementById('alloc-drawer');
  overlay.style.opacity = '0';
  drawer.style.transform = 'translateX(-50%) translateY(100%)';
  setTimeout(() => { overlay.style.display = 'none'; drawer.style.display = 'none'; }, 280);
}
```

이 함수 정의 바로 다음에 아래를 추가한다:

```javascript
function openNotifDrawer() {
  const events = window._notifEvents || [];
  const ICONS = { masam_mode: 'heroicons:arrow-path', leader_swap: 'heroicons:trophy', allocation: 'heroicons:chart-pie' };
  const rows = events.length
    ? events.map(e => `
      <div style="display:flex;gap:12px;padding:14px 0;border-top:1px solid rgba(255,255,255,.06);">
        <div style="width:32px;height:32px;border-radius:50%;background:#26262E;display:flex;align-items:center;justify-content:center;flex:none;">
          <span class="iconify" data-icon="${ICONS[e.type] || 'heroicons:bell'}" style="font-size:16px;color:#9A9AA3;"></span>
        </div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:11.5px;color:#6B6B73;margin-bottom:2px;">${e.date}</div>
          <div style="font-size:14px;font-weight:500;color:#F4F5F7;">${e.text}</div>
        </div>
      </div>`).join('')
    : `<div style="padding:40px 0;text-align:center;color:#6B6B73;font-size:14px;">최근 30일간 변동 이력이 없습니다</div>`;
  document.getElementById('notif-drawer-content').innerHTML = `
    <div style="font-size:17px;font-weight:700;color:#F4F5F7;margin:6px 0 8px;">🔔 최근 변동 히스토리</div>
    ${rows}
  `;
  const overlay = document.getElementById('notif-overlay');
  const drawer  = document.getElementById('notif-drawer');
  overlay.style.display = 'block';
  drawer.style.display  = 'block';
  requestAnimationFrame(() => {
    overlay.style.opacity = '1';
    drawer.style.transform = 'translateX(-50%) translateY(0)';
  });
  if (window.Iconify) Iconify.scan(drawer);
}
function closeNotifDrawer() {
  const overlay = document.getElementById('notif-overlay');
  const drawer  = document.getElementById('notif-drawer');
  overlay.style.opacity = '0';
  drawer.style.transform = 'translateX(-50%) translateY(100%)';
  setTimeout(() => { overlay.style.display = 'none'; drawer.style.display = 'none'; }, 280);
}
function injectNotifBell() {
  const bellHtml = `<button class="refresh-btn notif-btn" style="display:flex;" onclick="openNotifDrawer()" title="변동 히스토리"><span class="iconify" data-icon="heroicons:bell" style="font-size:20px;width:20px;height:20px;"></span></button>`;
  ['관심', '발견', '피드', '설정'].forEach(view => {
    const topbar = document.querySelector(`.view[data-view="${view}"] .topbar`);
    if (!topbar) return;
    const refreshBtn = topbar.querySelector('.refresh-btn');
    if (!refreshBtn || topbar.querySelector('.notif-btn')) return;
    refreshBtn.insertAdjacentHTML('beforebegin', bellHtml);
  });
  if (window.Iconify) Iconify.scan(document.body);
}
injectNotifBell();
```

`injectNotifBell()`은 데이터 fetch와 무관하게 DOM에만 의존하므로, 정의 직후 즉시 호출한다(`initFromData()`의 비동기 데이터 로딩을 기다릴 필요 없음). `.refresh-btn` 기본 CSS는 `display:none`이므로 인라인 `style="display:flex;"`로 벨 버튼은 항상 보이게 오버라이드한다(기존 새로고침 버튼 자체는 계속 숨김 유지 — 클래스만 재사용, 동작은 별개).

- [ ] **Step 3: 피드/설정(공유 topbar)에서 모멘텀 모드일 때 벨 숨기기**

`updateSettingsView()` 함수(약 2118~2128번째 줄)를 찾는다:

```javascript
  function updateSettingsView(){
    const isMomt = currentMode === '모멘텀';
    const masam = document.getElementById('settings-masam');
    const momt  = document.getElementById('settings-momt');
    if(masam) masam.style.display = isMomt ? 'none' : '';
    if(momt)  momt.style.display  = isMomt ? '' : 'none';
    const feedMasam = document.getElementById('feed-masam');
    const feedMomt  = document.getElementById('feed-momt');
    if(feedMasam) feedMasam.style.display = isMomt ? 'none' : '';
    if(feedMomt)  feedMomt.style.display  = isMomt ? '' : 'none';
  }
```

아래처럼 마지막 줄 앞에 벨 토글을 추가한다:

```javascript
  function updateSettingsView(){
    const isMomt = currentMode === '모멘텀';
    const masam = document.getElementById('settings-masam');
    const momt  = document.getElementById('settings-momt');
    if(masam) masam.style.display = isMomt ? 'none' : '';
    if(momt)  momt.style.display  = isMomt ? '' : 'none';
    const feedMasam = document.getElementById('feed-masam');
    const feedMomt  = document.getElementById('feed-momt');
    if(feedMasam) feedMasam.style.display = isMomt ? 'none' : '';
    if(feedMomt)  feedMomt.style.display  = isMomt ? '' : 'none';
    document.querySelectorAll('.view[data-view="피드"] .notif-btn, .view[data-view="설정"] .notif-btn').forEach(b => {
      b.style.display = isMomt ? 'none' : 'flex';
    });
  }
```

(발견/관심은 마삼룰 전용 뷰라 별도 토글 불필요 — 모멘텀 모드에서는 애초에 해당 뷰로 이동하지 않음.)

- [ ] **Step 4: localhost에서 육안 확인 (커밋 전, 사용자 요청사항)**

Run: `cd app && npm run dev` (백그라운드 실행 권장)
브라우저로 `http://localhost:3000/app.html` 접속 후 확인:
1. 발견/관심 탭 상단바에 벨 아이콘이 새로고침 버튼 왼쪽에 보이는지
2. 경제지표(피드)/설정 탭에서도 마삼룰 모드일 때 벨이 보이는지
3. 상단 `[마삼룰][모멘텀]` 토글로 모멘텀 전환 시 모멘텀/관심종목 탭에는 벨이 없고, 경제지표/설정 탭에서는 벨이 사라지는지
4. 벨 클릭 시 드로어가 하단에서 올라오는지 (이 시점엔 아직 Task 4를 안 붙여서 "최근 30일간 변동 이력이 없습니다"만 떠도 정상 — 빈 상태 UI 확인 목적)
5. 드로어 바깥(오버레이) 클릭 시 닫히는지

문제 있으면 다음 스텝(커밋) 진행 전에 수정.

- [ ] **Step 5: 커밋 (사용자 승인 후)**

```bash
git add app/public/app.html
git commit -m "feat: 마삼룰 화면에 알림 히스토리 벨 아이콘·드로어 UI 추가"
```

---

## Task 4: 프론트 — notifications.json 로드 + 병합 렌더링

**Files:**
- Modify: `app/public/app.html`

**Interfaces:**
- Consumes: `app/public/data/notifications.json`(Task 1/2가 만든 파일), `localStorage['alloc_history']`(Task 5가 채움 — 이 태스크 시점엔 비어있어도 정상 동작해야 함), `openNotifDrawer()`(Task 3에서 정의됨, `window._notifEvents`를 읽음)
- Produces: 전역 함수 `renderNotifList(serverEvents)` — 이후 `window._notifEvents`를 채워 `openNotifDrawer()`가 사용

- [ ] **Step 1: `notifications.json`을 Promise.all에 추가**

`initFromData()` 안의 아래 블록을 찾는다(약 2202~2208번째 줄):

```javascript
(async function initFromData() {
  try {
    const [masam, live, mkt, momtMkt, positions, mcapDaily, companies] = await Promise.all([
      fetch('/data/masam.json').then(r => r.json()),
      fetch('/data/live.json').then(r => r.json()),
      fetch('/data/masam_market.json').then(r => r.json()),
      fetch('/data/momentum_market.json').then(r => r.json()),
      fetch('/data/positions.json').then(r => r.json()),
      fetch('/data/mcap_daily.json').then(r => r.json()).catch(() => ({})),
      fetch('/data/companies.json').then(r => r.json()).catch(() => ({})),
    ]);
```

아래처럼 `notifications`를 추가한다(다른 항목은 그대로 유지):

```javascript
(async function initFromData() {
  try {
    const [masam, live, mkt, momtMkt, positions, mcapDaily, companies, notifications] = await Promise.all([
      fetch('/data/masam.json').then(r => r.json()),
      fetch('/data/live.json').then(r => r.json()),
      fetch('/data/masam_market.json').then(r => r.json()),
      fetch('/data/momentum_market.json').then(r => r.json()),
      fetch('/data/positions.json').then(r => r.json()),
      fetch('/data/mcap_daily.json').then(r => r.json()).catch(() => ({})),
      fetch('/data/companies.json').then(r => r.json()).catch(() => ({})),
      fetch('/data/notifications.json').then(r => r.json()).catch(() => []),
    ]);
```

- [ ] **Step 2: `renderNotifList()` 함수 정의**

Task 3에서 추가한 `injectNotifBell()` 함수 정의 바로 앞(즉 `closeNotifDrawer()` 함수 뒤, `injectNotifBell()` 앞)에 추가한다:

```javascript
function renderNotifList(serverEvents) {
  let allocHistory = [];
  try { allocHistory = JSON.parse(localStorage.getItem('alloc_history') || '[]'); } catch (e) {}
  const allocEvents = allocHistory.map(h => ({ date: h.date, type: 'allocation', text: h.text }));
  const merged = [...(serverEvents || []), ...allocEvents].sort((a, b) => b.date.localeCompare(a.date));
  window._notifEvents = merged;
}
```

- [ ] **Step 3: 데이터 로드 후 `renderNotifList()` 호출**

`initFromData()` 안의 아래 줄을 찾는다(약 2812~2813번째 줄):

```javascript
    // 14. 시가총액 순위 — mcap_daily + companies + live 데이터로 동적 렌더링
    renderMcapList(mcapDaily, companies, live.mcap_live, live.as_of);
```

바로 다음 줄에 추가한다:

```javascript
    // 14. 시가총액 순위 — mcap_daily + companies + live 데이터로 동적 렌더링
    renderMcapList(mcapDaily, companies, live.mcap_live, live.as_of);

    // 15. 알림 히스토리: 서버 기록(notifications) + 로컬 권장비중 이력 병합
    if (typeof renderNotifList === 'function') renderNotifList(notifications);
```

- [ ] **Step 4: localhost에서 확인**

`app/public/data/notifications.json`이 Task 2에서 이미 생성되어 있어야 한다(없으면 `python3 scripts/backfill_notifications.py` 먼저 실행).

Run: `cd app && npm run dev` (아직 안 띄웠으면)
브라우저에서 발견 탭 → 벨 아이콘 클릭 → Task 2에서 백필된 이벤트(마삼 모드 전환, 시총 순위 역전)가 날짜 내림차순으로 보이는지 확인. 아이콘(🔄 모드전환 / 🏆 순위역전)이 타입별로 다르게 나오는지 확인.

- [ ] **Step 5: 커밋 (사용자 승인 후)**

```bash
git add app/public/app.html
git commit -m "feat: 알림 드로어에 notifications.json 서버 기록 로드·렌더링 연결"
```

---

## Task 5: 프론트 — 권장 비중 변경 클라이언트 기록

**Files:**
- Modify: `app/public/app.html`

**Interfaces:**
- Consumes: `window._allocDetail`(기존 `renderRangeTable()`가 이미 채우는 전역 객체, `{nvdaPct, rank2Pct, qqqPct, cash, ...}`)
- Produces: `localStorage['alloc_history']`(Task 4의 `renderNotifList()`가 읽는 키), `localStorage['alloc_last']`(diff 비교용 내부 상태)

- [ ] **Step 1: `checkAllocationChange()` 함수 정의**

Task 4에서 만든 `renderNotifList()` 함수 정의 바로 앞에 추가한다:

> (2026-08-03 실사용 피드백 반영) 처음엔 퍼센트만 비교했으나, 1·2등 리더 몫 재배분처럼
> 합계가 상쇄되어 "38% → 38%"로 보이는 문제가 있었고, "구간이 얼마나 움직여서 비중이
> 바뀌었는지" 보여달라는 요청에 따라 `renderRangeTable()`의 `window._allocDetail`에
> `nvdaZone`/`rank2Zone`/`qqqZone`(각 대상의 구간 번호)을 추가로 담아 아래처럼 최종
> 반영함.

```javascript
function checkAllocationChange() {
  const d = window._allocDetail;
  if (!d) return;
  const today = new Date().toISOString().slice(0, 10);
  const snapshot = JSON.stringify({
    nvdaPct: d.nvdaPct, rank2Pct: d.rank2Pct, qqqPct: d.qqqPct, cash: d.cash,
    nvdaZone: d.nvdaZone, rank2Zone: d.rank2Zone, qqqZone: d.qqqZone,
  });
  const last = localStorage.getItem('alloc_last');
  if (last && last !== snapshot) {
    let prev;
    try { prev = JSON.parse(last); } catch (e) { prev = null; }
    if (prev) {
      const ZONE_LABELS = { nvdaZone: '1등주', rank2Zone: '2등주', qqqZone: 'QQQ' };
      const zoneParts = [];
      ['nvdaZone', 'rank2Zone', 'qqqZone'].forEach(key => {
        if (prev[key] != null && d[key] != null && prev[key] !== d[key]) {
          zoneParts.push(`${ZONE_LABELS[key]} ${prev[key]}→${d[key]}구간`);
        }
      });
      const pctChanged = prev.nvdaPct !== d.nvdaPct || prev.rank2Pct !== d.rank2Pct
        || prev.qqqPct !== d.qqqPct || prev.cash !== d.cash;
      if (zoneParts.length || pctChanged) {
        const prevStock = prev.nvdaPct + prev.rank2Pct + prev.qqqPct;
        const nowStock  = d.nvdaPct + d.rank2Pct + d.qqqPct;
        const zonePrefix = zoneParts.length ? `${zoneParts.join(', ')} — ` : '';
        const text = `${zonePrefix}주식 ${prevStock}% → ${nowStock}%, 현금 ${prev.cash}% → ${d.cash}%`;
        let history = [];
        try { history = JSON.parse(localStorage.getItem('alloc_history') || '[]'); } catch (e) {}
        history.push({ date: today, text });
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - 30);
        const cutoffStr = cutoff.toISOString().slice(0, 10);
        history = history.filter(h => h.date >= cutoffStr);
        localStorage.setItem('alloc_history', JSON.stringify(history));
      }
    }
  }
  localStorage.setItem('alloc_last', snapshot);
}
```

`window._allocDetail`에 `nvdaZone`/`rank2Zone`/`qqqZone`을 추가하려면 `renderRangeTable()` 내부(약 1782~1802번째 줄)의 `_leaderPct(shareBase, tgt)` 헬퍼가 매번 `_calcZone(tgt)`를 다시 계산하던 것을, 진입 전에 `nvdaZone`/`rank2Zone`/`qqqZone`을 한 번씩만 계산해 재사용하고 `window._allocDetail`에 같이 담도록 바꿔야 한다:

```javascript
      const _leaderPct = (shareBase, z) => {
        return isRebalancing ? shareBase * (1 - z * 0.1) : shareBase * z * 0.1;
      };
      const leaderShare = 100 * _rParts[0] / _rTotal;
      const qqqShare = 100 * (_rParts[1] || 0) / _rTotal;
      const nvdaZone = _calcZone('nvda');
      const rank2Zone = _calcZone('rank2');
      const qqqZone = _calcZone('qqq');
      let nvdaPct, rank2Pct = 0, qqqPct = 0;
      if (_dualLeader) {
        nvdaPct = Math.round(_leaderPct(leaderShare / 2, nvdaZone));
        rank2Pct = Math.round(_leaderPct(leaderShare / 2, rank2Zone));
      } else {
        nvdaPct = Math.round(_leaderPct(leaderShare, nvdaZone));
      }
      if (qqqShare > 0) qqqPct = Math.round(_leaderPct(qqqShare, qqqZone));
      const cash = 100 - nvdaPct - rank2Pct - qqqPct;
      window._allocDetail = {
        nvdaPct, rank2Pct, qqqPct, cash, dualLeader: _dualLeader, gapPct: _ls.gap_pct,
        nvdaTicker: _ls.rank1_ticker || 'NVDA', rank2Ticker: _ls.rank2_ticker || 'MSFT',
        nvdaZone, rank2Zone, qqqZone,
      };
```
```

첫 실행(이 기기에 `alloc_last`가 아예 없을 때)은 `last`가 `null`이라 조건문을 타지 않고 그냥 현재 스냅샷만 저장한다 — "없음 → 값"을 변경으로 기록하지 않기 위함(스펙 §4에서 의도한 동작).

- [ ] **Step 2: `renderRangeTable()` 호출 직후에 diff 체크 실행**

`initFromData()` 안에서 아래 부분을 찾는다(약 2562~2564번째 줄, "직전 고점"/"올인 지점" 자동 탭 전환 블록 바로 다음):

```javascript
      if (typeof renderRangeHeader === 'function') renderRangeHeader();
      if (typeof renderRangeTable  === 'function') renderRangeTable();
    }
```

`renderRangeTable()` 호출 다음 줄에 추가한다:

```javascript
      if (typeof renderRangeHeader === 'function') renderRangeHeader();
      if (typeof renderRangeTable  === 'function') renderRangeTable();
      if (typeof checkAllocationChange === 'function') checkAllocationChange();
    }
```

- [ ] **Step 3: localhost에서 변경 발생을 강제로 재현해 확인**

Run: `cd app && npm run dev` (아직 안 띄웠으면)
브라우저 개발자도구 콘솔에서:

```javascript
localStorage.setItem('alloc_last', JSON.stringify({nvdaPct: 100, rank2Pct: 0, qqqPct: 0, cash: 0}));
location.reload();
```

리로드 후 현재 실제 권장 비중이 위 값과 다르면(대부분의 경우 다름), 벨 아이콘 클릭 시 드로어에 "권장 비중 변경: ..." 항목이 새로 추가되어 보이는지 확인. 콘솔에서 `localStorage.getItem('alloc_history')`로도 직접 확인 가능.

다시 리로드했을 때(값이 그대로면) 같은 항목이 중복 추가되지 않는지도 확인.

- [ ] **Step 4: 커밋 (사용자 승인 후)**

```bash
git add app/public/app.html
git commit -m "feat: 권장 비중 변경을 기기 로컬(localStorage)에 기록해 알림 드로어에 표시"
```

---

## Task 6: 통합 확인 (커밋 없음 — 검증 전용)

**Files:** 없음(코드 변경 없음)

- [ ] **Step 1: 전체 플로우 재확인**

`cd app && npm run dev`로 로컬 서버가 떠 있는 상태에서:
1. 발견 탭 — 벨 아이콘 클릭 → 백필된 마삼 모드/시총 순위 이력 + (있다면) 권장 비중 변경 이력이 날짜 내림차순으로 섞여서 보이는지
2. 관심 탭에서도 동일하게 벨이 있고 같은 목록이 뜨는지 (드로어는 공유 상태 `window._notifEvents` 기반이라 탭 이동해도 내용 동일해야 함)
3. 경제지표/설정 탭 — 마삼룰 모드에서 벨 보임, `[모멘텀]` 토글 후 벨 사라짐, 다시 `[마삼룰]` 토글 시 벨 재등장
4. 새로고침 버튼(있다면) 눌러서 데이터 갱신해도 벨/드로어 정상 동작
5. 모바일 폭(390px)에서 드로어 레이아웃이 안 깨지는지 — 브라우저 개발자도구 반응형 모드로 확인

- [ ] **Step 2: 문제 없으면 사용자에게 최종 확인 요청**

로컬 서버 종료 여부·전체 커밋 푸시 여부를 사용자에게 확인받는다(이 프로젝트는 명시적 요청 없이 커밋·푸시·배포 금지 규칙이 있음).
