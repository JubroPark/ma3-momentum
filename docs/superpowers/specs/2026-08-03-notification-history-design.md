# 마삼룰 알림 히스토리 — 설계 명세서

**날짜**: 2026-08-03
**범위**: 마삼룰 화면(발견/관심/경제지표/설정) 상단바 알림 아이콘 + 최근 30일 변동 히스토리 드로어
**기준 문서**: CLAUDE.md §5(공통 파이프라인), §9(UX/IA)

---

## 1. 배경

CLAUDE.md §5 파이프라인 설계에는 원래 "전일 스냅샷 대조 → 신규 트리거 추출 → Web Push"가 있었으나 Web Push는 미구현(§10 Phase 4). 이번 기능은 그 축소판 — 푸시 대신 **인앱 히스토리 드로어**로 최근 변동(마삼 모드 전환·시총 순위 역전·권장 비중 변경)을 확인할 수 있게 한다.

## 2. 핵심 제약: 권장 비중은 서버가 계산할 수 없다

`portfolio_ratio`(1등주:QQQ 비율), `max_pct_nvda`/`max_pct_rank2`/`max_pct_qqq`(현금화 그리드)가 모두 **기기별 `localStorage` 설정**이다. 서버 배치(`fetch_eod.py`)는 이 값을 알 수 없으므로 권장 비중을 정확히 재현할 수 없다. 반면 마삼 모드(`mode`)·시총 순위(`leader_status.rank1_ticker`)는 순수 서버 계산값으로 모든 기기에서 동일하다.

→ **두 갈래로 나눠 추적한다.**

## 3. 아키텍처

```
[fetch_eod.py]                          [app.html, 브라우저]
  전일 masam.json과 diff                    페이지 로드마다 권장비중 재계산
  ├─ mode 변경?      → 이벤트 기록           ├─ localStorage 마지막 값과 비교
  └─ 1등주 변경?      → 이벤트 기록           └─ 다르면 이벤트 기록
        │                                        │
        ▼                                        ▼
  notifications.json                    localStorage['alloc_history']
  (레포에 커밋, 모든 기기 공통,                (기기 로컬, 이 기기만)
   최근 30일만 유지)                            (최근 30일만 유지)
        │                                        │
        └──────────────┬─────────────────────────┘
                        ▼
              벨 아이콘 클릭 → 두 소스를 날짜 내림차순으로 병합해 드로어에 표시
```

- `notifications.json`은 마삼 모드 전환·시총 순위 역전 두 종류만 다룬다. 이번 세션에서 git 커밋 히스토리(`masam.json`)를 훑어 최근 30일치를 1회 백필한다.
- 권장 비중 변경 이력은 **오늘부터 새로 쌓기 시작**한다(과거분 재계산 안 함 — 로직이 최근 계속 바뀌어서 재계산값이 실제 과거 화면값과 다를 수 있기 때문. 지난 대화에서 합의됨).

## 4. 데이터 스키마

### `app/public/data/notifications.json` (신규 파일)
```json
[
  { "date": "2026-07-27", "type": "leader_swap", "text": "1등주가 NVDA → AAPL로 바뀌었습니다" },
  { "date": "2026-08-01", "type": "leader_swap", "text": "1등주가 AAPL → NVDA로 바뀌었습니다" },
  { "date": "2026-06-05", "type": "masam_mode", "text": "평상시 → 위기 전환 (마삼 발생)" }
]
```
- 배열, 최신순 정렬 불필요(프론트에서 정렬) — `fetch_eod.py`가 append만 하고, 저장 직전 30일 초과분을 트림.
- `type`: `"masam_mode"` | `"leader_swap"` — 프론트에서 아이콘/색상 구분용.

### `localStorage['alloc_history']` (신규 키, 클라이언트)
```json
[
  { "date": "2026-08-03", "text": "권장 비중 변경: 1등주 100% → 90%, 현금 0% → 10%" }
]
```
- app.html이 매 로드마다 배너용으로 이미 계산 중인 `nvdaPct/rank2Pct/qqqPct/cash`(`window._allocDetail`)를 `localStorage['alloc_last']`와 비교, 다르면 `alloc_history`에 항목 추가 후 `alloc_last` 갱신. 30일 초과분 트림.

## 5. 백엔드 변경 (`fetch_eod.py`)

- `main()` 끝부분, `masam_out` 저장 직후: `existing_masam.mode` vs `new_mode`, `existing_masam.leader_status.rank1_ticker` vs `rank1_ticker` 비교
- 변경 시 `notifications.json` 로드 → append → `date` 기준 최근 30일만 남기고 저장
- 1회성 백필: 이 세션에서 `git log`로 `masam.json`의 일별 `mode`/`leader_status.rank1_ticker`를 훑어 지난 30일 이벤트를 재구성, `notifications.json`에 시드

## 6. 프론트 변경 (`app.html`)

- **아이콘 버튼**: `.refresh-btn`과 동일한 32px 원형 스타일, Iconify `heroicons:bell`. 기준일-시간 `<span>` 오른쪽, `.refresh-btn` 왼쪽에 배치.
  - 발견/관심 탭(마삼룰 전용 topbar, 대략 L318/359)에는 그대로 추가.
  - **경제지표·설정 탭은 마삼룰·모멘텀이 topbar 마크업을 공유**하고 `stratToggle()`로 내용만 바꾸는 구조(CLAUDE.md §9-2) — 단순히 두 곳(대략 L501/613)에 아이콘을 추가하면 모멘텀 선택 시에도 같이 보이게 됨. `stratToggle()`이 전략 전환 시 `display:none`/`flex`로 벨 아이콘 자체를 토글하도록 처리(현재 탭 내용 전환과 동일한 방식).
- **드로어**: 기존 `#alloc-overlay`/`#alloc-drawer` 패턴 재사용(하단 슬라이드업, 스와이프 닫기). 날짜별로 묶어서 최신순 리스트, 항목 없으면 "최근 변동 없음" 빈 상태.
- **읽음 배지 없음**(사용자 확인) — 클릭하면 그냥 열림.
- 데이터 로드(`initFromData`) 시점에 권장비중 diff 체크 로직 실행.

## 7. 테스트/검증

- 커밋 전 `npm run dev`로 localhost에서 직접 확인(사용자 요청).
- 확인 항목: 벨 아이콘 위치·스타일, 드로어 열기/닫기, 30일 백필 이벤트 표시, 권장비중 변경 시 새 항목 추가(로컬스토리지 값 강제로 바꿔서 확인).

## 8. 범위 밖 (이번엔 안 함)

- Web Push 실제 발송(§10 Phase 4, 별도 작업)
- 읽음/안읽음 배지
- 권장 비중 과거 이력 재계산 백필
- 서버로 기기 설정값을 보내 권장비중을 서버에서도 추적하는 것
