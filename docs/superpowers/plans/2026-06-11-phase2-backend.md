# Phase 2 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매일 장 마감 후 두 엔진을 자동 실행하고, MA50 ticker 상태를 일별로 이어받으며, 산출 JSON을 public GitHub raw URL로 제공한다.

**Architecture:** `main` 브랜치에 코드, `data` 브랜치에 산출물+상태(force-push, 커밋 1개). GitHub Actions cron이 22:00 UTC에 `data` 브랜치에서 상태를 복원 → 엔진 실행 → `data` 브랜치에 force-push. `scripts/state_manager.py`가 positions.json 읽기/쓰기를 순수 함수로 담당. `run_ma50.py`가 저장된 state를 이어받아 상태머신을 올바르게 진행.

**Tech Stack:** Python 3.11, yfinance, GitHub Actions, gh CLI

---

## 파일 구조

| 파일 | 변경 |
|---|---|
| `scripts/state_manager.py` | 신규 — positions 로드/저장/업데이트 순수 함수 |
| `tests/test_state_manager.py` | 신규 — state_manager 단위 테스트 |
| `scripts/run_ma50.py` | 수정 — state 읽기/쓰기 + 올바른 상태머신 로직 |
| `.github/workflows/daily_update.yml` | 신규 — cron 워크플로우 |
| `.gitignore` | 수정 — `state/` 추가 |

---

## Task 1: `scripts/state_manager.py` — 순수 함수

**Files:**
- Create: `scripts/state_manager.py`
- Create: `tests/test_state_manager.py`

### 배경

`run_ma50.py`가 매일 실행될 때 전날 각 ticker의 상태(WATCH/BUY/HOLDING/SELL_WATCH/SELL)와 진입가·손절선을 이어받아야 한다. 이 파일은 그 읽기/쓰기를 담당하는 순수 함수 모음이다. I/O 없는 `update_position`이 불변 패턴을 보장해 테스트를 쉽게 만든다.

---

- [ ] **Step 1: 테스트 파일 작성**

```python
# tests/test_state_manager.py
from __future__ import annotations
import json
from datetime import date
import pytest


def test_load_positions_missing_file_returns_empty():
    from scripts.state_manager import load_positions
    result = load_positions("/nonexistent/path/positions.json")
    assert result == {"as_of": None, "positions": {}}


def test_get_position_unknown_ticker_returns_watch_defaults():
    from scripts.state_manager import get_position
    positions = {"as_of": None, "positions": {}}
    pos = get_position(positions, "UNKNOWN")
    assert pos["state"] == "WATCH"
    assert pos["days_in_state"] == 0
    assert pos["entry_price"] is None
    assert pos["stop_level"] is None


def test_update_position_does_not_mutate_original():
    from scripts.state_manager import update_position
    original = {"as_of": None, "positions": {}}
    updated = update_position(
        original, "AAPL", "HOLDING", 3,
        "2026-06-08", 201.3, 193.5, "STRONG_BREAKOUT",
    )
    assert "AAPL" not in original.get("positions", {})
    assert updated["positions"]["AAPL"]["state"] == "HOLDING"
    assert updated["positions"]["AAPL"]["entry_price"] == 201.3


def test_update_position_sets_as_of_today():
    from scripts.state_manager import update_position
    positions = {"as_of": None, "positions": {}}
    updated = update_position(positions, "MSFT", "WATCH", 0, None, None, None, None)
    assert updated["as_of"] == str(date.today())


def test_save_and_load_roundtrip(tmp_path):
    from scripts.state_manager import save_positions, load_positions, update_position
    path = str(tmp_path / "positions.json")
    positions = {"as_of": None, "positions": {}}
    positions = update_position(
        positions, "AAPL", "HOLDING", 3,
        "2026-06-08", 201.3, 193.5, "STRONG_BREAKOUT",
    )
    save_positions(positions, path)
    loaded = load_positions(path)
    assert loaded["positions"]["AAPL"]["state"] == "HOLDING"
    assert loaded["positions"]["AAPL"]["entry_price"] == 201.3
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_state_manager.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError: No module named 'scripts.state_manager'`

- [ ] **Step 3: `scripts/state_manager.py` 구현**

```python
"""MA50 ticker 상태 persistence — 순수 함수, I/O 최소화."""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from typing import Optional

_DEFAULT_POSITION: dict = {
    "state": "WATCH",
    "days_in_state": 0,
    "entered_at": None,
    "entry_price": None,
    "stop_level": None,
    "signal_type": None,
}


def load_positions(path: str) -> dict:
    """positions.json 로드. 파일 없으면 빈 구조 반환 (첫 실행 대응)."""
    p = Path(path)
    if not p.exists():
        return {"as_of": None, "positions": {}}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_positions(positions: dict, path: str) -> None:
    """positions dict를 JSON으로 저장. 디렉토리 없으면 자동 생성."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=2, default=str)


def get_position(positions: dict, ticker: str) -> dict:
    """ticker의 저장된 상태 반환. 없으면 기본 WATCH 상태."""
    return dict(positions.get("positions", {}).get(ticker, _DEFAULT_POSITION))


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
    """불변 패턴 — 새 dict 반환. 원본 positions 변경 없음."""
    updated_positions = dict(positions.get("positions", {}))
    updated_positions[ticker] = {
        "state": state,
        "days_in_state": days_in_state,
        "entered_at": entered_at,
        "entry_price": entry_price,
        "stop_level": stop_level,
        "signal_type": signal_type,
    }
    return {
        "as_of": str(date.today()),
        "positions": updated_positions,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_state_manager.py -v
```
Expected: `5 passed`

- [ ] **Step 5: 전체 테스트 스위트 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/ -q 2>&1 | tail -3
```
Expected: `135 passed` (기존 130 + 신규 5)

- [ ] **Step 6: 커밋**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add scripts/state_manager.py tests/test_state_manager.py && git commit -m "feat: state_manager — positions 로드/저장/업데이트 순수 함수"
```

---

## Task 2: `scripts/run_ma50.py` 수정 — state 통합

**Files:**
- Modify: `scripts/run_ma50.py`

### 배경

현재 `run_ma50.py`는 상태머신을 사용하지 않는다 — 매일 처음부터 재계산하고 `get_sell_signal`을 항상 `"HOLDING"` / `days_in_state=0`으로 호출한다. 이 태스크에서 올바른 상태머신 로직으로 교체한다.

**핵심 변경 사항:**
1. 실행 시작 시 `load_positions`로 전날 state 읽기
2. ticker별 루프에서 저장된 state에 따라 `get_buy_signal` 또는 `get_sell_signal` 호출
3. `BUY` 상태(전일 BUY 신호) → 오늘 시가(open)로 `entry_price` 확정 → `HOLDING`
4. 실행 종료 시 `save_positions`로 갱신된 state 저장
5. `state_path` 파라미터 추가 (테스트·CLI 재사용)

---

- [ ] **Step 1: .gitignore에 `state/` 추가**

```
# /Users/jubro/Claude Project/ma3 momentum/.gitignore 파일 끝에 추가
state/
```

- [ ] **Step 2: `run_ma50.py` import 섹션 교체**

기존 import 블록 아래에 다음을 추가:

```python
# 기존 import 다음에 추가
from scripts.state_manager import load_positions, save_positions, get_position, update_position
from engines.backtest_ma50 import calc_stop_level
```

- [ ] **Step 3: `_STATE_PATH` 상수 추가**

`_OUTPUT_SIGNALS` 상수 바로 아래에 추가:

```python
_STATE_PATH = Path(__file__).parent.parent / "state" / "positions.json"
```

- [ ] **Step 4: `run()` 함수 시그니처 + state 로드 추가**

`def run(watchlist: list = None) -> dict:` 를 아래로 교체:

```python
def run(watchlist: list = None, state_path: str = None) -> dict:
```

`tickers = watchlist or _DEFAULT_WATCHLIST` 바로 다음 줄에 추가:

```python
    _path = Path(state_path) if state_path else _STATE_PATH
    positions = load_positions(str(_path))
```

- [ ] **Step 5: ticker 루프 내 Open 시리즈 추가**

`volume_s = get_series(raw, ticker, "Volume")` 줄 바로 다음에 추가:

```python
        open_s     = get_series(raw, ticker, "Open")
        today_open = float(open_s.iloc[-1]) if open_s is not None else close_last
```

- [ ] **Step 6: 상태머신 로직 교체**

기존 `buy = get_buy_signal(...)` ~ `trigger = ""` 블록(lines 111-134)을 아래 코드로 완전 교체:

```python
        # 저장된 state 로드
        saved      = get_position(positions, ticker)
        prev_state = saved["state"]
        prev_days  = saved["days_in_state"]

        # 상태에 따라 시그널 산출
        buy_sig  = None
        sell_sig = None
        if prev_state == "WATCH":
            buy_sig = get_buy_signal(
                close_s, high_s, low_s if low_s is not None else high_s,
                ma50, ma200, vol_ratio, gap50, slope_pct, rs_pct_val, regime, params,
            )
        elif prev_state in ("HOLDING", "SELL_WATCH"):
            sell_sig = get_sell_signal(
                prev_state, close_s, ma50, ma200,
                rs_pct_val, prev_days, regime, params,
            )
        # BUY / SELL 상태: 전일 보류 주문 → transition만 수행

        new_state = transition_state(prev_state, buy_sig, sell_sig)
        new_days  = 0 if new_state != prev_state else prev_days + 1

        # 포지션 필드 결정
        if new_state == "HOLDING" and prev_state == "BUY":
            # 전일 BUY 신호 → 오늘 시가로 체결
            new_entry   = round(today_open, 2)
            new_stop    = round(calc_stop_level(new_entry, ma50_last, atr14), 2)
            new_entered = str(as_of_dt)
            new_stype   = saved.get("signal_type")
        elif new_state == "WATCH" and prev_state == "SELL":
            # 전일 SELL 신호 → 청산 완료, 리셋
            new_entry   = None
            new_stop    = None
            new_entered = None
            new_stype   = None
        elif new_state == "BUY":
            # 오늘 BUY 신호 발생 → 내일 시가 체결 예정
            new_entry   = None
            new_stop    = None
            new_entered = None
            new_stype   = buy_sig
        else:
            # HOLDING / SELL_WATCH / SELL / WATCH 유지
            new_entry   = saved.get("entry_price")
            new_stop    = saved.get("stop_level")
            new_entered = saved.get("entered_at")
            new_stype   = saved.get("signal_type")

        positions = update_position(
            positions, ticker, new_state, new_days,
            new_entered, new_entry, new_stop, new_stype,
        )

        # signals.json 출력용 표시값
        display_sig  = buy_sig or sell_sig or "OK"
        display_trig = (
            f"MA50 {buy_sig.replace('_', ' ')}" if buy_sig
            else ("MA50 하향 이탈" if sell_sig else "")
        )
        signal_type  = display_sig
        state        = new_state
        trigger      = display_trig
```

- [ ] **Step 7: `items.append` 라인 교체**

기존:
```python
        items.append(build_signal_item(ticker, signal_type, state, score, trigger, metrics))
```

는 이미 `signal_type`, `state`, `trigger` 변수를 사용하므로 그대로 유지. `score` 계산도 그대로 유지.

- [ ] **Step 8: `save_positions` 호출 추가**

`items.sort(...)` 줄 바로 위에 추가:

```python
    # 갱신된 state 저장
    save_positions(positions, str(_path))
    print(f"state 저장: {_path}")
```

- [ ] **Step 9: 로컬 실행으로 동작 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && python scripts/run_ma50.py 2>&1 | tail -10
```

Expected:
- `state 저장: .../state/positions.json` 출력
- `signals.json 저장: ...` 출력
- 에러 없음

```bash
# state 파일 생성 확인
cat "/Users/jubro/Claude Project/ma3 momentum/state/positions.json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('as_of:', d['as_of'])
tickers = list(d['positions'].keys())
print('tickers:', tickers[:3], '...')
states = [d['positions'][t]['state'] for t in tickers]
print('states:', states[:3])
"
```

- [ ] **Step 10: 전체 테스트 스위트 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/ -q 2>&1 | tail -3
```
Expected: `135 passed`

- [ ] **Step 11: 커밋**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add scripts/run_ma50.py .gitignore && git commit -m "feat: run_ma50 — state persistence 통합, 상태머신 올바르게 적용"
```

---

## Task 3: GitHub 레포 생성 + 환경 설정

**Files:**
- 없음 (레포·시크릿 설정)

### 배경

현재 로컬 git 레포에 remote가 없다. `gh` CLI(JubroPark 계정 인증 완료)로 public 레포를 생성하고 `FRED_API_KEY` 시크릿을 등록한다.

---

- [ ] **Step 1: GitHub 레포 생성 + remote 연결 + push**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && gh repo create ma3-momentum --public --description "마삼 대응 + MA50 스크리너 투자 보조 PWA 백엔드" --source=. --remote=origin --push
```

Expected 출력:
```
✓ Created repository JubroPark/ma3-momentum on GitHub
✓ Added remote origin https://github.com/JubroPark/ma3-momentum.git
✓ Pushed commits to https://github.com/JubroPark/ma3-momentum.git
```

- [ ] **Step 2: remote 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git remote -v
```

Expected:
```
origin  https://github.com/JubroPark/ma3-momentum.git (fetch)
origin  https://github.com/JubroPark/ma3-momentum.git (push)
```

- [ ] **Step 3: FRED_API_KEY 시크릿 등록**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && gh secret set FRED_API_KEY --body "$(grep FRED_API_KEY .env | cut -d= -f2)"
```

Expected: `✓ Set Actions secret FRED_API_KEY for JubroPark/ma3-momentum`

- [ ] **Step 4: 시크릿 등록 확인**

```bash
gh secret list --repo JubroPark/ma3-momentum
```

Expected: `FRED_API_KEY` 목록에 표시

---

## Task 4: `.github/workflows/daily_update.yml` + 수동 실행 검증

**Files:**
- Create: `.github/workflows/daily_update.yml`

### 배경

평일 22:00 UTC에 두 엔진을 실행하고 산출물을 `data` 브랜치에 force-push한다. `workflow_dispatch`로 수동 실행도 지원해 초기 셋업 검증에 사용한다.

---

- [ ] **Step 1: 워크플로우 디렉토리 생성**

```bash
mkdir -p "/Users/jubro/Claude Project/ma3 momentum/.github/workflows"
```

- [ ] **Step 2: 워크플로우 파일 작성**

```yaml
# .github/workflows/daily_update.yml
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
          # git rm 전에 /tmp에 미리 저장 (git rm -rf 가 파일도 삭제하므로)
          cp state/positions.json /tmp/positions.json
          cp outputs/signals.json /tmp/signals.json
          cp outputs/masam.json   /tmp/masam.json

          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout --orphan data-new
          git rm -rf . --quiet
          mkdir -p state outputs
          cp /tmp/positions.json state/positions.json
          cp /tmp/signals.json   outputs/signals.json
          cp /tmp/masam.json     outputs/masam.json
          git add state/ outputs/
          git commit -m "[cron] $(date -u +%Y-%m-%d)"
          git push origin data-new:data --force
```

- [ ] **Step 3: 워크플로우 파일 push**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add .github/workflows/daily_update.yml && git commit -m "feat: GitHub Actions daily_update 워크플로우 — cron + data 브랜치 배포" && git push origin main
```

- [ ] **Step 4: 수동 실행으로 검증**

```bash
gh workflow run daily_update.yml --repo JubroPark/ma3-momentum
```

Expected: `✓ Created workflow_dispatch event for daily_update.yml at main`

- [ ] **Step 5: 워크플로우 완료 대기 + 로그 확인**

```bash
# 30초 대기 후 상태 확인
sleep 30 && gh run list --repo JubroPark/ma3-momentum --limit 1
```

완료(✓) 될 때까지 반복:
```bash
gh run watch --repo JubroPark/ma3-momentum
```

실패 시 로그 확인:
```bash
gh run view --repo JubroPark/ma3-momentum --log-failed
```

- [ ] **Step 6: data 브랜치 산출물 확인**

```bash
# data 브랜치의 signals.json as_of 확인
curl -s "https://raw.githubusercontent.com/JubroPark/ma3-momentum/data/outputs/signals.json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('as_of:', d['as_of'], '| items:', len(d['items']))"
```

Expected: `as_of: 2026-06-11 | items: 16` (오늘 날짜, 16종목)

```bash
# positions.json 확인
curl -s "https://raw.githubusercontent.com/JubroPark/ma3-momentum/data/state/positions.json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('as_of:', d['as_of']); print('tickers:', len(d['positions']))"
```

Expected: `as_of: 오늘 날짜 | tickers: 16`

---

## 검증 체크리스트

- [ ] `pytest tests/ -q` → 135 passed
- [ ] `state/positions.json` 로컬 실행 후 생성 확인
- [ ] GitHub Actions 수동 실행 성공 (녹색 체크)
- [ ] `data` 브랜치에 `state/positions.json` + `outputs/signals.json` + `outputs/masam.json` 존재
- [ ] raw.githubusercontent.com URL로 JSON fetch 성공
- [ ] `state/` 가 `.gitignore`에 있어 `main` 브랜치에 커밋되지 않음
