# Phase 1A: 마삼 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `^IXIC` 종가·FRED 금리·WALCL·1등주 시총을 입력받아 3-모드 상태(REBALANCING / CRISIS_STAKING / PANIC)와 비중 배분 안내를 담은 `outputs/masam.json`을 생성하는 엔진을 구현한다.

**Architecture:** Phase 0에서 검증된 `check_masam()·check_rate_env()·check_qe()` 함수를 재사용한다. 엔진 계층(`masam_engine.py`)은 순수 함수만 포함하며 I/O 없음. 데이터 수집(`run_masam.py`)과 엔진 로직을 완전히 분리한다.

**Tech Stack:** Python 3.9+, pandas, yfinance, fredapi, pytest

---

## 파일 맵

| 파일 | 역할 | 신규/기존 |
|---|---|---|
| `engines/__init__.py` | 패키지 마커 | 신규 |
| `engines/masam_engine.py` | 3-모드 상태머신 + masam.json 빌더 (순수 함수) | 신규 |
| `engines/market_context.py` | 금리환경+QE — phase0 _get_close 재사용 | 신규 |
| `engines/leader.py` | 1등주 mcap 판정 | 신규 |
| `outputs/.gitkeep` | outputs 디렉토리 보존 | 신규 |
| `scripts/run_masam.py` | 데이터 수집 + 엔진 실행 + JSON 저장 진입점 | 신규 |
| `tests/test_masam_engine.py` | masam_engine 단위 테스트 | 신규 |
| `tests/test_market_context.py` | market_context 단위 테스트 | 신규 |
| `tests/test_leader.py` | leader 단위 테스트 | 신규 |

---

## Task 1: 디렉토리 구조 + engines 패키지

**Files:**
- Create: `engines/__init__.py`
- Create: `outputs/.gitkeep`

- [ ] **Step 1: 디렉토리 + 빈 파일 생성**

```bash
cd "ma3 momentum"
mkdir -p engines outputs
touch engines/__init__.py outputs/.gitkeep
```

- [ ] **Step 2: 생성 확인**

```bash
ls engines/ outputs/
```
Expected:
```
engines/: __init__.py
outputs/: .gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add engines/__init__.py outputs/.gitkeep
git commit -m "chore: engines + outputs 디렉토리 초기화"
```

---

## Task 2: engines/market_context.py — 금리환경 + QE

phase0_poc.py의 `check_rate_env()`·`check_qe()` 로직을 래핑해 단일 `get_market_context()` 함수로 제공한다.

**Files:**
- Create: `engines/market_context.py`
- Create: `tests/test_market_context.py`

- [ ] **Step 1: 테스트 작성 (RED)**

`tests/test_market_context.py`:
```python
import pytest
import pandas as pd
from unittest.mock import MagicMock


def _make_fred(dff: float, walcl_values: list) -> MagicMock:
    mock = MagicMock()
    walcl_series = pd.Series(
        walcl_values,
        index=pd.date_range("2026-04-01", periods=len(walcl_values), freq="W"),
    )
    mock.get_series.side_effect = [
        pd.Series([dff], index=pd.to_datetime(["2026-06-08"])),
        walcl_series,
    ]
    return mock


def test_market_context_non_zero_qe_off():
    from engines.market_context import get_market_context

    mock_fred = _make_fred(3.62, [8000, 7980, 7960, 7940, 7920, 7900, 7880, 7860])
    result = get_market_context(fred=mock_fred)

    assert result["rate_env"] == "NON_ZERO"
    assert result["dff"] == pytest.approx(3.62)
    assert result["qe_state"] == "QE_OFF"
    assert result["qe_active"] is False


def test_market_context_zero_qe_on():
    from engines.market_context import get_market_context

    mock_fred = _make_fred(0.08, [8000, 8020, 8040, 8060, 8080, 8100, 8120, 8140])
    result = get_market_context(fred=mock_fred)

    assert result["rate_env"] == "ZERO"
    assert result["qe_state"] == "QE_ON"
    assert result["qe_active"] is True
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "ma3 momentum" && source .venv/bin/activate
pytest tests/test_market_context.py -v
```
Expected: `ImportError: cannot import name 'get_market_context'`

- [ ] **Step 3: 구현**

`engines/market_context.py`:
```python
"""금리환경 + QE 컨텍스트 — FRED 데이터 기반."""
import os
import pandas as pd
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()
_FRED_API_KEY = os.getenv("FRED_API_KEY")
_QE_THRESHOLD = 0.1  # %


def get_market_context(fred: Fred = None) -> dict:
    """
    금리환경(DFF)과 QE 상태(WALCL)를 하나의 dict로 반환.
    Returns:
        rate_env: "ZERO" | "NON_ZERO"
        dff: float
        qe_active: bool
        qe_state: "QE_ON" | "QE_OFF" | "AMBIGUOUS"
        slope_pct: float
        last_updated: str (YYYY-MM-DD)
    """
    if fred is None:
        fred = Fred(api_key=_FRED_API_KEY)
    rate = _get_rate_env(fred)
    qe = _get_qe_state(fred)
    return {
        "rate_env": rate["rate_env"],
        "dff": rate["dff"],
        "last_updated": rate["last_updated"],
        "qe_active": qe["qe_active"],
        "qe_state": qe["qe_state"],
        "slope_pct": qe["slope_pct"],
    }


def _get_rate_env(fred: Fred) -> dict:
    series = fred.get_series("DFF").dropna()
    latest = float(series.iloc[-1])
    return {
        "rate_env": "ZERO" if latest <= 0.25 else "NON_ZERO",
        "dff": round(latest, 2),
        "last_updated": series.index[-1].strftime("%Y-%m-%d"),
    }


def _get_qe_state(fred: Fred) -> dict:
    series = fred.get_series("WALCL").dropna().tail(8)
    ma4 = series.rolling(4).mean().dropna()
    slope_pct = round(float((ma4.iloc[-1] / ma4.iloc[-2] - 1) * 100), 4)
    if slope_pct > _QE_THRESHOLD:
        return {"qe_active": True, "qe_state": "QE_ON", "slope_pct": slope_pct}
    if slope_pct < -_QE_THRESHOLD:
        return {"qe_active": False, "qe_state": "QE_OFF", "slope_pct": slope_pct}
    return {"qe_active": False, "qe_state": "AMBIGUOUS", "slope_pct": slope_pct}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_market_context.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add engines/market_context.py tests/test_market_context.py
git commit -m "feat: market_context — 금리환경+QE 통합 컨텍스트"
```

---

## Task 3: engines/leader.py — 1등주 판정

**Files:**
- Create: `engines/leader.py`
- Create: `tests/test_leader.py`

- [ ] **Step 1: 테스트 작성 (RED)**

`tests/test_leader.py`:
```python
import pytest
from unittest.mock import MagicMock, patch


def _mock_ticker_factory(mcap_map: dict):
    def factory(t):
        m = MagicMock()
        m.info = {"marketCap": mcap_map.get(t, 0)}
        return m
    return factory


def test_leader_rank1_is_largest():
    from engines.leader import get_leader_status

    mcaps = {"NVDA": 3_500_000_000_000, "AAPL": 3_100_000_000_000, "MSFT": 2_900_000_000_000}
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=list(mcaps))

    assert result["rank1_ticker"] == "NVDA"
    assert result["rank2_ticker"] == "AAPL"


def test_leader_gap_pct():
    from engines.leader import get_leader_status

    # rank1=1000, rank2=900 → gap = (1000-900)/1000 * 100 = 10%
    mcaps = {"A": 1_000_000_000, "B": 900_000_000}
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=["A", "B"])

    assert result["gap_pct"] == pytest.approx(10.0)
    assert result["gap_below_10pct"] is False  # 정확히 10%는 경계: <10% 조건 미충족


def test_leader_gap_below_10pct():
    from engines.leader import get_leader_status

    mcaps = {"A": 1_000_000_000, "B": 950_000_000}  # gap = 5%
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=["A", "B"])

    assert result["gap_below_10pct"] is True


def test_leader_overtake_detected():
    from engines.leader import get_leader_status

    # 리스트 순서와 무관하게 시총으로 판정
    mcaps = {"AAPL": 3_200_000_000_000, "NVDA": 3_500_000_000_000}
    with patch("yfinance.Ticker", side_effect=_mock_ticker_factory(mcaps)):
        result = get_leader_status(tickers=["AAPL", "NVDA"])

    assert result["rank1_ticker"] == "NVDA"
    assert result["overtake_detected"] is False
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_leader.py -v
```
Expected: `ImportError`

- [ ] **Step 3: 구현**

`engines/leader.py`:
```python
"""1등주 판정 — 대형주 상위 10개 시총 비교."""
import yfinance as yf

# 분기 1회 수동 갱신 (CLAUDE.md §5-3)
_DEFAULT_LARGE_CAP_LIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AVGO", "BRK-B", "JPM",
]


def get_leader_status(tickers: list = None) -> dict:
    """
    시총 기준 1위·2위 판정 + 격차 계산.
    Returns:
        rank1_ticker, rank1_mcap, rank2_ticker, rank2_mcap,
        gap_pct, overtake_detected, gap_below_10pct
    """
    if tickers is None:
        tickers = _DEFAULT_LARGE_CAP_LIST

    mcaps = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            mcap = info.get("marketCap") or 0
            if mcap > 0:
                mcaps[t] = mcap
        except Exception:
            continue

    if len(mcaps) < 2:
        return {
            "rank1_ticker": None, "rank1_mcap": None,
            "rank2_ticker": None, "rank2_mcap": None,
            "gap_pct": None, "overtake_detected": False, "gap_below_10pct": False,
        }

    sorted_mcaps = sorted(mcaps.items(), key=lambda x: x[1], reverse=True)
    r1_ticker, r1_mcap = sorted_mcaps[0]
    r2_ticker, r2_mcap = sorted_mcaps[1]
    gap_pct = round((r1_mcap - r2_mcap) / r1_mcap * 100, 1)

    return {
        "rank1_ticker": r1_ticker,
        "rank1_mcap": r1_mcap,
        "rank2_ticker": r2_ticker,
        "rank2_mcap": r2_mcap,
        "gap_pct": gap_pct,
        "overtake_detected": r2_mcap > r1_mcap,
        "gap_below_10pct": gap_pct < 10.0,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_leader.py -v
```
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add engines/leader.py tests/test_leader.py
git commit -m "feat: leader — 1등주 시총 판정"
```

---

## Task 4: engines/masam_engine.py — 상태머신 핵심 (determine_mode + allocations)

**Files:**
- Create: `engines/masam_engine.py` (초기 버전)
- Create: `tests/test_masam_engine.py` (초기)

- [ ] **Step 1: 테스트 작성 (RED)**

`tests/test_masam_engine.py` (초기 — determine_mode + allocations):
```python
import pytest
import pandas as pd
import numpy as np


# ── determine_mode ───────────────────────────────────────────


def test_mode_rebalancing_no_masam():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=0, prev_year_return=None)
    assert mode == "REBALANCING"
    assert panic_type is None


def test_mode_crisis_1_masam():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=1, prev_year_return=20.0)
    assert mode == "CRISIS_STAKING"
    assert panic_type is None


def test_mode_crisis_3_masam():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=3, prev_year_return=50.0)
    # 3회는 아직 PANIC 아님
    assert mode == "CRISIS_STAKING"


def test_mode_panic_basic_4_masam():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=4, prev_year_return=20.0)
    assert mode == "PANIC"
    assert panic_type == "BASIC"


def test_mode_panic_emergency_45pct():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=4, prev_year_return=45.0)
    assert mode == "PANIC"
    assert panic_type == "EMERGENCY"


def test_mode_panic_emergency_above_45():
    from engines.masam_engine import determine_mode
    mode, panic_type = determine_mode(masam_month_count=5, prev_year_return=60.0)
    assert panic_type == "EMERGENCY"


def test_mode_panic_basic_no_prev_year():
    from engines.masam_engine import determine_mode
    # prev_year_return=None → BASIC (데이터 없으면 EMERGENCY 미판정)
    mode, panic_type = determine_mode(masam_month_count=4, prev_year_return=None)
    assert panic_type == "BASIC"


# ── calc_target_allocation ───────────────────────────────────


def test_allocation_rebalancing():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("REBALANCING", None, "NON_ZERO")
    assert result["stock_pct"] == 100


def test_allocation_crisis_non_zero():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("CRISIS_STAKING", None, "NON_ZERO")
    assert result["stock_pct"] == 50


def test_allocation_crisis_zero():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("CRISIS_STAKING", None, "ZERO")
    assert result["stock_pct"] == 25


def test_allocation_panic_emergency():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("PANIC", "EMERGENCY", "NON_ZERO")
    assert result["stock_pct"] == 0
    assert result["cash_pct"] == 100


def test_allocation_panic_basic():
    from engines.masam_engine import calc_target_allocation
    result = calc_target_allocation("PANIC", "BASIC", "NON_ZERO")
    assert result["stock_pct"] == 0


# ── calc_hedge_type ──────────────────────────────────────────


def test_hedge_non_zero_qe_off():
    from engines.masam_engine import calc_hedge_type
    result = calc_hedge_type("NON_ZERO", False, "QE_OFF")
    assert result["type"] == "TLT"


def test_hedge_zero_rate():
    from engines.masam_engine import calc_hedge_type
    result = calc_hedge_type("ZERO", False, "QE_OFF")
    assert result["type"] == "IAU_GLD_TIP"


def test_hedge_qe_active():
    from engines.masam_engine import calc_hedge_type
    result = calc_hedge_type("NON_ZERO", True, "QE_ON")
    assert result["type"] == "IAU_GLD_TIP"


def test_hedge_ambiguous():
    from engines.masam_engine import calc_hedge_type
    result = calc_hedge_type("NON_ZERO", False, "AMBIGUOUS")
    assert result["type"] == "DOLLAR"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_masam_engine.py -v
```
Expected: `ImportError`

- [ ] **Step 3: 구현 (determine_mode + allocations + hedge)**

`engines/masam_engine.py`:
```python
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

    REBALANCING   : 주식 100% (기본. 리밸런싱 단계별 현금화는 사용자 실행)
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_masam_engine.py -v
```
Expected: `19 passed`

- [ ] **Step 5: Commit**

```bash
git add engines/masam_engine.py tests/test_masam_engine.py
git commit -m "feat: masam_engine — determine_mode + 비중/헤지 배분"
```

---

## Task 5: engines/masam_engine.py — 트리거 + RSI14 + build_masam_json

**Files:**
- Modify: `engines/masam_engine.py` (함수 추가)
- Modify: `tests/test_masam_engine.py` (테스트 추가)

- [ ] **Step 1: 테스트 추가 (RED)**

`tests/test_masam_engine.py` 끝에 추가:
```python
# ── _calc_rsi14 ───────────────────────────────────────────────


def test_rsi14_all_up_returns_near_100():
    from engines.masam_engine import _calc_rsi14
    closes = pd.Series([float(100 + i) for i in range(20)])
    rsi = _calc_rsi14(closes)
    assert rsi is not None
    assert rsi == pytest.approx(100.0, abs=1.0)


def test_rsi14_insufficient_data_returns_none():
    from engines.masam_engine import _calc_rsi14
    closes = pd.Series([100.0, 101.0, 102.0])
    rsi = _calc_rsi14(closes)
    assert rsi is None


def test_rsi14_normal_range():
    from engines.masam_engine import _calc_rsi14
    np.random.seed(42)
    closes = pd.Series(100.0 + np.cumsum(np.random.randn(50)))
    rsi = _calc_rsi14(closes)
    assert rsi is not None
    assert 0 <= rsi <= 100


# ── check_allin_conditions ────────────────────────────────────


def _make_series(closes: list, start: str = "2026-01-02") -> pd.Series:
    dates = pd.bdate_range(start, periods=len(closes))
    return pd.Series(closes, index=dates)


def test_allin_cond1_met_after_31_days():
    from engines.masam_engine import check_allin_conditions
    last_masam = pd.Timestamp("2026-05-09")  # 32일 전
    ixic = _make_series([100.0] * 20)
    leader = _make_series([100.0] * 20)
    conds = check_allin_conditions(last_masam, ixic, leader, date(2026, 6, 10))
    assert conds[0]["met"] is True


def test_allin_cond1_not_met_within_30_days():
    from engines.masam_engine import check_allin_conditions
    last_masam = pd.Timestamp("2026-06-05")  # 5일 전
    ixic = _make_series([100.0] * 20)
    leader = _make_series([100.0] * 20)
    conds = check_allin_conditions(last_masam, ixic, leader, date(2026, 6, 10))
    assert conds[0]["met"] is False


def test_allin_cond2_8_consecutive_up():
    from engines.masam_engine import check_allin_conditions
    closes = [float(100 + i) for i in range(9)]  # 9일 연속 상승
    ixic = _make_series(closes)
    leader = _make_series([100.0] * 9)
    conds = check_allin_conditions(None, ixic, leader, date(2026, 1, 13))
    assert conds[1]["met"] is True


def test_allin_cond2_not_met_with_down_day():
    from engines.masam_engine import check_allin_conditions
    closes = [100.0, 101.0, 100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5]
    ixic = _make_series(closes)
    leader = _make_series([100.0] * 9)
    conds = check_allin_conditions(None, ixic, leader, date(2026, 1, 13))
    assert conds[1]["met"] is False  # 3번째 날 하락


def test_allin_cond4_ixic_ath():
    from engines.masam_engine import check_allin_conditions
    closes = [100.0, 95.0, 98.0, 101.0]  # 101 = 신고점
    ixic = _make_series(closes)
    leader = _make_series([100.0, 95.0, 98.0, 97.0])  # 리더는 신고점 아님
    conds = check_allin_conditions(None, ixic, leader, date(2026, 1, 5))
    assert conds[3]["met"] is True
    assert conds[2]["met"] is False


# ── build_masam_json ──────────────────────────────────────────


def test_build_masam_json_structure():
    from engines.masam_engine import build_masam_json

    result = build_masam_json(
        as_of=date(2026, 6, 10),
        mode="CRISIS_STAKING",
        panic_type=None,
        rate_env="NON_ZERO",
        qe_active=False,
        masam_month_count=1,
        masam_cumulative=1,
        last_masam_date=pd.Timestamp("2026-06-05"),
        leader_status={"rank1_ticker": "NVDA", "rank1_mcap": 3_500_000_000_000,
                       "rank2_ticker": "AAPL", "rank2_mcap": 3_100_000_000_000,
                       "gap_pct": 11.4, "overtake_detected": False, "gap_below_10pct": False},
        target_allocation={"stock_pct": 50, "hedge_pct": 30, "cash_pct": 20, "label": "50% 말뚝"},
        hedge_allocation={"type": "TLT", "rationale": "비제로+QE이전", "exit_trigger": ""},
        distance_to_triggers={"v_allin_pct_needed": 10.0, "emergency_allin_pct_away": -1.5},
        allin_conditions=[{"id": 1, "label": "한달+1일 무마삼", "met": False, "grade": "약"}],
        additional_buy_signal={"rsi14": 55.0, "mfi14": None, "both_below_50": False, "label": ""},
        recommended_action="말뚝박기 진입",
        alerts=[],
    )

    assert result["as_of"] == "2026-06-10"
    assert result["mode"] == "CRISIS_STAKING"
    assert result["masam"]["month_count"] == 1
    assert result["masam"]["last_masam_date"] == "2026-06-05"
    assert result["leader_status"]["rank1_ticker"] == "NVDA"
    assert result["target_allocation"]["stock_pct"] == 50
    assert result["hedge_allocation"]["type"] == "TLT"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_masam_engine.py -v
```
Expected: 추가된 테스트들 FAIL

- [ ] **Step 3: masam_engine.py에 함수 추가**

`engines/masam_engine.py` 기존 코드 끝에 추가:
```python
# ── RSI14 ────────────────────────────────────────────────────


def _calc_rsi14(close: pd.Series) -> float | None:
    """1등주 종가 기준 RSI14. 데이터 15개 미만이면 None."""
    if len(close) < 15:
        return None
    delta = close.diff().dropna()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    loss_safe = loss.replace(0, float("inf"))
    rsi = 100 - (100 / (1 + gain / loss_safe))
    valid = rsi.dropna()
    return float(valid.iloc[-1]) if not valid.empty else None


# ── 올인 조건 4종 ────────────────────────────────────────────


def check_allin_conditions(
    last_masam_date: pd.Timestamp | None,
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
    v_allin_pct_needed = 10.0 if rate_env == "NON_ZERO" else 5.0
    emergency_level = ixic_ath * 0.70
    emergency_allin_pct_away = round((current / emergency_level - 1) * 100, 2)
    return {
        "v_allin_pct_needed": v_allin_pct_needed,
        "emergency_allin_pct_away": emergency_allin_pct_away,
    }


# ── 추가 자금 투입 신호 ───────────────────────────────────────


def check_additional_buy_signal(close_leader: pd.Series) -> dict:
    """
    추가 자금 투입 조건: 1등주 RSI14 ≤ 50 (CLAUDE.md §5-2, MFI14는 volume 필요).
    """
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
    panic_type: str | None,
    rate_env: str,
    qe_active: bool,
    masam_month_count: int,
    masam_cumulative: int,
    last_masam_date: pd.Timestamp | None,
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
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
pytest tests/test_masam_engine.py -v
```
Expected: 모든 테스트 PASS (약 30개)

- [ ] **Step 5: Commit**

```bash
git add engines/masam_engine.py tests/test_masam_engine.py
git commit -m "feat: masam_engine — 트리거 조건 + RSI14 + JSON 빌더"
```

---

## Task 6: scripts/run_masam.py — 실행 진입점

**Files:**
- Create: `scripts/run_masam.py`

- [ ] **Step 1: 구현**

`scripts/run_masam.py`:
```python
"""마삼 엔진 실행 진입점 — 데이터 수집 + 엔진 평가 + masam.json 저장."""
import os
import json
import sys
from pathlib import Path

import pandas as pd
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

    # 3. 1등주 판정 + 주가 수집
    print("1등주 시총 조회 중...")
    leader = get_leader_status()
    rank1 = leader["rank1_ticker"] or "AAPL"
    print(f"1등주: {rank1}")
    df_leader = yf.download(rank1, period="1y", auto_adjust=True, progress=False)

    close_ixic = _get_close(df_ixic)
    close_leader = _get_close(df_leader)
    as_of = close_ixic.index[-1].date()

    # 4. 상태 결정
    mode, panic_type = determine_mode(masam_result["month_count"], masam_result["prev_year_return"])
    target_alloc = calc_target_allocation(mode, panic_type, ctx["rate_env"])
    hedge_alloc = calc_hedge_type(ctx["rate_env"], ctx["qe_active"], ctx["qe_state"])

    allin_conds = check_allin_conditions(
        masam_result["latest_masam_date"], close_ixic, close_leader, as_of
    )
    dist = calc_distance_to_triggers(close_ixic, ctx["rate_env"])
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


def _build_recommended_action(mode: str, panic_type: str | None, rate_env: str) -> str:
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
    mode: str, panic_type: str | None, masam_result: dict, buy_signal: dict
) -> list:
    alerts = []
    if mode == "PANIC" and panic_type == "EMERGENCY":
        alerts.append("⚠️ PANIC_EMERGENCY: 고점 -30% 몰빵 없음 · V자 6구간(+30%) 기준 적용 중")
    month_count = masam_result["month_count"]
    if 1 <= month_count <= 3:
        alerts.append(f"⚠️ 이번 달 마삼 {month_count}회 — 공황 확정까지 {4 - month_count}회 남음")
    if buy_signal.get("both_below_50"):
        alerts.append("📥 추가 자금 투입 조건 충족: 1등주 RSI14 ≤ 50")
    return alerts


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: 전체 기존 테스트 통과 확인**

```bash
pytest tests/ -v
```
Expected: 기존 18 + 신규 약 30 = 총 48+ PASS

- [ ] **Step 3: 실제 실행**

```bash
cd "ma3 momentum" && source .venv/bin/activate
python scripts/run_masam.py
```

Expected 출력:
```
==================================================
마삼 엔진 실행
==================================================
^IXIC 다운로드 중...
1등주 시총 조회 중...
1등주: NVDA (or AAPL/MSFT)

masam.json 저장 완료: .../outputs/masam.json
모드: CRISIS_STAKING / panic_type: None
1등주: NVDA / 금리: NON_ZERO / QE: AMBIGUOUS
```

- [ ] **Step 4: masam.json 수동 검증**

```bash
cat outputs/masam.json | python3 -m json.tool | head -40
```

검증 항목:
- `as_of`: 오늘 날짜 (2026-06-10 기준 "2026-06-09" 또는 "2026-06-10")
- `mode`: "CRISIS_STAKING" (이번 달 마삼 1회 있음)
- `masam.month_count`: 1
- `masam.last_masam_date`: "2026-06-05"
- `rate_env`: "NON_ZERO"
- `leader_status.rank1_ticker`: NVDA or AAPL or MSFT (비어있지 않을 것)
- `target_allocation.stock_pct`: 50
- `hedge_allocation.type`: "DOLLAR" (WALCL AMBIGUOUS이므로)

- [ ] **Step 5: Commit**

```bash
git add scripts/run_masam.py outputs/.gitkeep
git commit -m "feat: run_masam — 마삼 엔진 실행 진입점 + masam.json 산출"
```

---

## Task 7: 전체 테스트 suite 정리 + Phase 1A 완료 검증

**Files:**
- No new files

- [ ] **Step 1: 전체 테스트 실행**

```bash
pytest tests/ -v --tb=short
```
Expected: 모든 테스트 PASS (48개 이상), FAIL 0

- [ ] **Step 2: masam.json 스키마 검증**

```bash
python3 - << 'EOF'
import json
from pathlib import Path
data = json.loads(Path("outputs/masam.json").read_text())

required_keys = [
    "as_of", "mode", "panic_type", "rate_env", "qe_active",
    "masam", "leader_status", "target_allocation", "hedge_allocation",
    "distance_to_triggers", "all_in_conditions", "additional_buy_signal",
    "panic_reentry", "recommended_action", "alerts",
]
missing = [k for k in required_keys if k not in data]
assert not missing, f"누락 키: {missing}"
assert data["masam"]["month_count"] >= 0
assert data["target_allocation"]["stock_pct"] + data["target_allocation"]["hedge_pct"] + data["target_allocation"]["cash_pct"] == 100
assert len(data["all_in_conditions"]) == 4
print("✅ masam.json 스키마 검증 통과")
print(f"모드: {data['mode']} | 1등주: {data['leader_status']['rank1_ticker']} | 비중: 주식{data['target_allocation']['stock_pct']}%")
EOF
```

- [ ] **Step 3: Phase 1A 완료 commit**

```bash
git add -A
git commit -m "feat: phase1a 완료 — 마삼 엔진 + masam.json 산출 검증"
```

---

## 자기 검토 (Self-Review)

### 스펙 커버리지

| CLAUDE.md 요구사항 | 구현 Task |
|---|---|
| 3-모드 상태머신 (REBALANCING/CRISIS_STAKING/PANIC) | Task 4 |
| PANIC_EMERGENCY (전년 +45% AND 4회↑) | Task 4 |
| 비제로/제로 금리별 말뚝박기 비중 (50%/25%) | Task 4 |
| 헤지 배치 (TLT/IAU_GLD_TIP/DOLLAR) | Task 4 |
| 올인 조건 4종 | Task 5 |
| RSI14 (1등주 기준) | Task 5 |
| masam.json 전체 필드 | Task 5 |
| 1등주 판정 (시총 top 10) | Task 3 |
| 금리환경 + QE 컨텍스트 | Task 2 |
| 실제 실행 + JSON 저장 | Task 6 |

### 미포함 (의도적)
- MFI14: yfinance에서 volume 데이터 추가 필요 → Phase 2에서 추가
- 리밸런싱 단계별 현금화 단계 계산: 사용자 포지션 데이터 없이 서버사이드 산출 불가 → UI 레이어(Phase 3)에서 처리
- 공황 재진입 트랜치 진행상황 (stage): 사용자 실행 이력 필요 → Phase 3 포지션 추적과 연동
