# Phase 2 백엔드 설계 — GitHub Actions cron + State Persistence

## 목표

매일 장 마감 후 두 엔진(마삼·MA50)을 자동 실행하고, MA50 ticker 상태를 일별로 이어받으며, 산출 JSON을 PWA가 fetch할 수 있는 공개 URL로 제공한다.

## 확정 사항

- **레포**: public GitHub 레포 (raw.githubusercontent.com으로 PWA 접근)
- **저장 전략**: 방식 A — 레포 내 `data` 브랜치 (force-push, 커밋 1개 유지)
- **State persistence**: B — state + position 통합 (entry_price, stop_level 포함)
- **cron 시각**: 22:00 UTC 평일 (여름 18:00 ET / 겨울 17:00 ET, 장 마감 후)

---

## 1. 브랜치 레이아웃

```
main                         ← 코드 (engines/, scripts/, tests/, docs/)
data                         ← 데이터 전용 (force-push, 커밋 1개 유지)
  ├── state/
  │   └── positions.json     ← MA50 ticker 상태 (내부용, PWA 미소비)
  └── outputs/
      ├── signals.json       ← MA50 매수 후보 (PWA 소비)
      └── masam.json         ← 마삼 국면 (PWA 소비)
      # market.json (레짐·금리·VIX 공통 컴포넌트) — Phase 3에서 추가
      # backtest_results.json — 일회성 분석, data 브랜치 미포함
```

**PWA 접근 URL 패턴**
```
https://raw.githubusercontent.com/{user}/ma3-momentum/data/outputs/signals.json
```

---

## 2. 일일 실행 흐름

```
GitHub Actions (22:00 UTC, 평일)
  1. main 체크아웃 + data 브랜치에서 state/positions.json 복원
  2. run_masam.py  → outputs/masam.json 갱신
  3. run_ma50.py   → state/positions.json 읽기 → 상태 이어받기
                   → outputs/signals.json 갱신
                   → state/positions.json 쓰기
  4. data 브랜치에 force-push (커밋 1개 유지)
```

---

## 3. State Persistence Layer

### 신규 파일: `scripts/state_manager.py`

순수 함수만 포함, I/O 없음.

```python
def load_positions(path: str) -> dict:
    """positions.json 로드. 파일 없으면 빈 dict 반환 (첫 실행 대응)."""

def save_positions(positions: dict, path: str) -> None:
    """positions dict를 JSON으로 저장."""

def update_position(
    positions: dict,
    ticker: str,
    state: str,
    days_in_state: int,
    entered_at: Optional[str],
    entry_price: Optional[float],
    stop_level: Optional[float],
    signal_type: Optional[str],
) -> dict:
    """불변 패턴 — 새 dict 반환."""
```

### `state/positions.json` 스키마

```json
{
  "as_of": "2026-06-11",
  "positions": {
    "AAPL": {
      "state": "HOLDING",
      "days_in_state": 3,
      "entered_at": "2026-06-08",
      "entry_price": 201.3,
      "stop_level": 193.5,
      "signal_type": "STRONG_BREAKOUT"
    },
    "MSFT": {
      "state": "WATCH",
      "days_in_state": 0,
      "entered_at": null,
      "entry_price": null,
      "stop_level": null,
      "signal_type": null
    }
  }
}
```

### `run_ma50.py` 수정 흐름

```
시작 : load_positions(STATE_PATH) → ticker별 이전 state 읽기
루프 : 각 ticker 평가 시 saved_state 주입 → transition_state()
       WATCH→HOLDING 전이 시: entry_price = 오늘 open, stop_level 계산
       HOLDING→SELL 전이 시:  entry_price/stop_level = null 리셋
종료 : save_positions(updated, STATE_PATH)
```

**entry_price 결정 기준**: BUY 신호 발생일 다음 거래일 open 가격.
- 신호 발생일 EOD → state = "BUY" 저장
- 다음 cron 실행 시 state = "BUY" 확인 → 오늘 open으로 entry_price 확정 → state = "HOLDING"

---

## 4. GitHub Actions 워크플로우

**`.github/workflows/daily_update.yml`**

```yaml
name: Daily Market Update

on:
  schedule:
    - cron: '0 22 * * 1-5'   # 평일 22:00 UTC (여름 18:00 ET / 겨울 17:00 ET)
  workflow_dispatch:           # 수동 실행 지원

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout main
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Restore state from data branch
        run: |
          mkdir -p state outputs
          git fetch origin data || true
          git show origin/data:state/positions.json > state/positions.json 2>/dev/null \
            || echo '{"as_of": null, "positions": {}}' > state/positions.json

      - name: Run masam engine
        run: python scripts/run_masam.py
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}

      - name: Run MA50 engine
        run: python scripts/run_ma50.py

      - name: Publish to data branch
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout --orphan data-new
          git rm -rf . --quiet
          mkdir -p state outputs
          cp state/positions.json state/
          cp outputs/signals.json outputs/masam.json outputs/
          git add state/ outputs/
          git commit -m "[cron] $(date -u +%Y-%m-%d)"
          git push origin data-new:data --force
```

---

## 5. 에러 핸들링

| 상황 | 대응 |
|---|---|
| 특정 ticker yfinance 실패 | `try/except`로 SKIP, 나머지 처리 계속 |
| masam 엔진 전체 실패 | MA50 step은 계속 실행 (별도 step) |
| state 저장 실패 | 명시적 에러 출력 + 워크플로우 실패 처리 |
| data branch 없음 (첫 실행) | `git fetch origin data \|\| true` 로 무시 |
| 전체 워크플로우 실패 | GitHub가 등록 이메일로 자동 알림 |

**초기 실행**: `state/positions.json` 없으면 모든 ticker를 `WATCH`로 시작. 이미 보유 중인 종목은 다음 신호 발생 시 자동 추적되거나 수동으로 파일 편집.

---

## 6. 파일 변경 요약

| 파일 | 변경 |
|---|---|
| `scripts/state_manager.py` | 신규 |
| `scripts/run_ma50.py` | 수정 — state 읽기/쓰기 추가 |
| `.github/workflows/daily_update.yml` | 신규 |
| `state/positions.json` | 신규 (data 브랜치, 첫 실행 시 생성) |
| `requirements.txt` | 확인 (추가 의존성 없음) |

**Web Push(알림)는 Phase 4 범위** — 이번 Phase 2에서 제외.
