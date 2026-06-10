# Phase 0 데이터 PoC 구현 플랜

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ^IXIC 마삼 감지·금리환경·QE 판정·MA50 RS percentile·PMI 소스 가용성을 단일 Python 스크립트로 검증하고, PASS/WARN/FAIL 요약을 출력한다.

**Architecture:** 6개 독립 함수가 각각 데이터를 수집·계산하고 dict를 반환한다. `main()`이 각 함수를 `try/except`로 감싸 실행한 뒤 요약을 출력한다. `check_masam`·`check_drawdown`은 `main()`에서 다운로드한 ^IXIC DataFrame을 공유해 중복 요청을 방지한다. 테스트는 DataFrame·Fred 객체를 파라미터로 주입해 실제 API 호출 없이 계산 로직만 검증한다.

**Tech Stack:** Python 3.11+, yfinance 0.2+, fredapi 0.5+, pandas 2.0+, numpy 1.26+, python-dotenv 1.0+, pytest 8+

---

## 파일 구조

```
ma3 momentum/
├── scripts/
│   └── phase0_poc.py       ← 6개 함수 + main() 전부
├── tests/
│   ├── conftest.py          ← 공통 픽스처 (mock DataFrame)
│   └── test_phase0.py       ← 단위 테스트
├── .env                     ← FRED_API_KEY (git 제외)
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `ma3 momentum/requirements.txt`
- Create: `ma3 momentum/.env.example`
- Create: `ma3 momentum/.gitignore`

- [ ] **Step 1: git 초기화**

```bash
cd "ma3 momentum"
git init
```

Expected: `Initialized empty Git repository in .../ma3 momentum/.git/`

- [ ] **Step 2: requirements.txt 생성**

파일 경로: `ma3 momentum/requirements.txt`

```
yfinance>=0.2.54
fredapi>=0.5.2
pandas>=2.0.0
numpy>=1.26.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 3: .env.example 생성**

파일 경로: `ma3 momentum/.env.example`

```
FRED_API_KEY=your_fred_api_key_here
```

- [ ] **Step 4: .gitignore 생성**

파일 경로: `ma3 momentum/.gitignore`

```
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.DS_Store
```

- [ ] **Step 5: .env 생성 (git 미포함)**

파일 경로: `ma3 momentum/.env`

```
FRED_API_KEY=cb6fb72ffbfb566a4438a4287d451617
```

- [ ] **Step 6: 가상환경 생성 및 의존성 설치**

```bash
cd "ma3 momentum"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: 패키지 설치 완료, 오류 없음

- [ ] **Step 7: scripts/ 및 tests/ 디렉터리 생성**

```bash
mkdir -p scripts tests
touch scripts/__init__.py tests/__init__.py
```

- [ ] **Step 8: 첫 커밋**

```bash
git add requirements.txt .env.example .gitignore scripts/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding for phase0 poc"
```

---

## Task 2: 테스트 픽스처 (conftest.py)

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: conftest.py 작성**

파일 경로: `tests/conftest.py`

```python
import pandas as pd
import numpy as np
import pytest


def make_ixic_df(closes: list, start: str = "2026-06-02") -> pd.DataFrame:
    """비즈니스일 기준 ^IXIC mock DataFrame 생성."""
    dates = pd.bdate_range(start, periods=len(closes))
    close_series = pd.Series(closes, index=dates, name="Close")
    return pd.DataFrame({"Close": close_series})


@pytest.fixture
def ixic_june_2026():
    """
    실제 데이터 기반 mock:
    06/02(기준), 06/03(-0.54%), 06/04(-0.09%), 06/05(-4.18%), 06/08(+0.86%), 06/09(-0.97%)
    마삼: 06/05 1건
    """
    return make_ixic_df(
        closes=[27000.0, 26853.98, 26830.96, 25709.43, 25929.66, 25678.82],
        start="2026-06-02",
    )


@pytest.fixture
def ixic_with_prev_year():
    """
    2025년 전체 + 2026년 상반기 포함 mock (전년도 역년 수익률 테스트용).
    2025-01-02: 19000, 2025-12-31: 23111.46 → +21.6%
    2026-06-09: 25678.82
    """
    dates_2025 = pd.bdate_range("2025-01-02", "2025-12-31", freq="BME")
    # 간단하게 월말 기준 12개 포인트로 선형 보간
    closes_2025 = np.linspace(19000, 23111.46, len(dates_2025))

    dates_2026 = pd.bdate_range("2026-01-02", "2026-06-09", freq="BME")
    closes_2026 = np.linspace(23200, 25678.82, len(dates_2026))

    all_dates = list(dates_2025) + list(dates_2026)
    all_closes = list(closes_2025) + list(closes_2026)
    close_series = pd.Series(all_closes, index=all_dates, name="Close")
    return pd.DataFrame({"Close": close_series})
```

- [ ] **Step 2: conftest import 확인**

```bash
cd "ma3 momentum"
source .venv/bin/activate
python -c "from tests.conftest import make_ixic_df; print('ok')"
```

Expected: `ok`

---

## Task 3: check_masam() — TDD

**Files:**
- Create: `scripts/phase0_poc.py` (이 Task에서 첫 생성)
- Create: `tests/test_phase0.py` (이 Task에서 첫 생성)

- [ ] **Step 1: 실패하는 테스트 작성**

파일 경로: `tests/test_phase0.py`

```python
import pytest
import pandas as pd
from datetime import date


# ── check_masam ──────────────────────────────────────────────


def test_check_masam_detects_masam_day(ixic_june_2026):
    from scripts.phase0_poc import check_masam

    result = check_masam(df_ixic=ixic_june_2026)

    assert result["status"] == "PASS"
    assert result["latest_masam_date"].date() == date(2026, 6, 5)
    assert abs(result["latest_masam_pct"] - (-4.18)) < 0.1


def test_check_masam_month_count_is_calendar_month(ixic_june_2026):
    from scripts.phase0_poc import check_masam

    result = check_masam(df_ixic=ixic_june_2026)

    # 6월 마삼은 06/05 단 1건
    assert result["month_count"] == 1


def test_check_masam_no_masam_returns_none():
    from scripts.phase0_poc import check_masam

    # 모든 등락이 -3% 미만인 데이터
    import pandas as pd
    dates = pd.bdate_range("2026-06-02", periods=5)
    df = pd.DataFrame({"Close": [1000.0, 990.0, 985.0, 988.0, 992.0]}, index=dates)

    result = check_masam(df_ixic=df)

    assert result["status"] == "PASS"
    assert result["latest_masam_date"] is None


def test_check_masam_prev_year_return(ixic_with_prev_year):
    from scripts.phase0_poc import check_masam

    result = check_masam(df_ixic=ixic_with_prev_year)

    # 2025-01-02: 19000 → 2025-12-31: 23111.46 → 약 +21.6%
    assert result["prev_year_return"] is not None
    assert 15.0 < result["prev_year_return"] < 30.0


def test_check_masam_ath_drawdown(ixic_june_2026):
    from scripts.phase0_poc import check_masam

    result = check_masam(df_ixic=ixic_june_2026)

    # 전고점 27000.0 (첫 번째 값) 대비 현재 25678.82 → 약 -4.9%
    assert result["ath_value"] == pytest.approx(27000.0, abs=1.0)
    assert result["ath_drawdown"] < 0  # 반드시 음수
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
cd "ma3 momentum"
source .venv/bin/activate
pytest tests/test_phase0.py -v 2>&1 | head -30
```

Expected: `ImportError` 또는 `ModuleNotFoundError` (아직 phase0_poc.py 없음)

- [ ] **Step 3: check_masam() 구현**

파일 경로: `scripts/phase0_poc.py`

```python
"""Phase 0 데이터 PoC — 6개 독립 검증 함수."""
import os
import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")


def _get_close(df: pd.DataFrame) -> pd.Series:
    """yfinance MultiIndex 또는 단일 컬럼 DataFrame 모두에서 Close 추출."""
    if isinstance(df.columns, pd.MultiIndex):
        return df["Close"].squeeze()
    return df["Close"].squeeze()


def check_masam(df_ixic: pd.DataFrame = None) -> dict:
    """
    ^IXIC 마삼(-3% 이상 하락) 감지.

    Args:
        df_ixic: 테스트용 사전 로드 DataFrame. None이면 yfinance에서 2년 다운로드.

    Returns:
        {
            status: PASS | FAIL,
            latest_masam_date: pd.Timestamp | None,
            latest_masam_pct: float | None,
            month_count: int,           # 현재 달력 월 마삼 횟수
            prev_year_return: float | None,  # 전년 역년 수익률(%)
            ath_value: float,
            ath_date: pd.Timestamp,
            current_close: float,
            ath_drawdown: float,        # 전고점 대비 하락률(%)
        }
    """
    if df_ixic is None:
        df_ixic = yf.download("^IXIC", period="2y", auto_adjust=True, progress=False)

    close = _get_close(df_ixic)
    pct = close.pct_change() * 100

    masam = pct[pct <= -3.0]

    latest_masam_date = masam.index[-1] if not masam.empty else None
    latest_masam_pct = round(float(masam.iloc[-1]), 2) if not masam.empty else None

    # 현재 달력 월 마삼 횟수 (월 독립 집계 — 롤링 아님)
    today = pd.Timestamp.today()
    month_mask = (masam.index.year == today.year) & (masam.index.month == today.month)
    month_count = int(month_mask.sum())

    # 전년도 역년 수익률
    prev_year = today.year - 1
    prev_data = close[close.index.year == prev_year]
    if len(prev_data) >= 2:
        prev_year_return = round(float((prev_data.iloc[-1] / prev_data.iloc[0] - 1) * 100), 1)
    else:
        prev_year_return = None

    # 전고점 대비 하락률
    ath_value = float(close.max())
    ath_date = close.idxmax()
    current_close = float(close.iloc[-1])
    ath_drawdown = round((current_close / ath_value - 1) * 100, 2)

    return {
        "status": "PASS",
        "latest_masam_date": latest_masam_date,
        "latest_masam_pct": latest_masam_pct,
        "month_count": month_count,
        "prev_year_return": prev_year_return,
        "ath_value": round(ath_value, 2),
        "ath_date": ath_date,
        "current_close": round(current_close, 2),
        "ath_drawdown": ath_drawdown,
    }
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/test_phase0.py -v -k "masam"
```

Expected:
```
test_phase0.py::test_check_masam_detects_masam_day PASSED
test_phase0.py::test_check_masam_month_count_is_calendar_month PASSED
test_phase0.py::test_check_masam_no_masam_returns_none PASSED
test_phase0.py::test_check_masam_prev_year_return PASSED
test_phase0.py::test_check_masam_ath_drawdown PASSED
```

- [ ] **Step 5: 커밋**

```bash
git add scripts/phase0_poc.py tests/test_phase0.py tests/conftest.py
git commit -m "feat: check_masam() with tests — 마삼 감지·월별 카운트·전고점 하락"
```

---

## Task 4: check_rate_env() — TDD

**Files:**
- Modify: `scripts/phase0_poc.py`
- Modify: `tests/test_phase0.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_phase0.py` 하단에 추가:

```python
# ── check_rate_env ───────────────────────────────────────────


def test_check_rate_env_non_zero():
    from scripts.phase0_poc import check_rate_env
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [4.5], index=pd.to_datetime(["2026-06-09"])
    )

    result = check_rate_env(fred=mock_fred)

    assert result["status"] == "PASS"
    assert result["rate_env"] == "NON_ZERO"
    assert result["dff"] == pytest.approx(4.5)


def test_check_rate_env_zero():
    from scripts.phase0_poc import check_rate_env
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [0.08], index=pd.to_datetime(["2021-06-09"])
    )

    result = check_rate_env(fred=mock_fred)

    assert result["status"] == "PASS"
    assert result["rate_env"] == "ZERO"


def test_check_rate_env_boundary():
    """DFF = 0.25%는 ZERO_RATE 경계값."""
    from scripts.phase0_poc import check_rate_env
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [0.25], index=pd.to_datetime(["2022-03-15"])
    )

    result = check_rate_env(fred=mock_fred)

    assert result["rate_env"] == "ZERO"  # DFF ≤ 0.25% = ZERO
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/test_phase0.py -v -k "rate_env"
```

Expected: `ImportError` (함수 미정의)

- [ ] **Step 3: check_rate_env() 구현**

`scripts/phase0_poc.py` 하단에 추가:

```python
def check_rate_env(fred: Fred = None) -> dict:
    """
    FRED DFF(연방기금금리 실효치)로 금리환경 판단.
    DFF ≤ 0.25% → ZERO / DFF > 0.25% → NON_ZERO

    Returns:
        {status, rate_env: "ZERO"|"NON_ZERO", dff: float, last_updated: str}
    """
    if fred is None:
        fred = Fred(api_key=FRED_API_KEY)

    series = fred.get_series("DFF")
    latest = series.dropna().iloc[-1]
    last_date = series.dropna().index[-1].strftime("%Y-%m-%d")

    rate_env = "ZERO" if latest <= 0.25 else "NON_ZERO"

    return {
        "status": "PASS",
        "rate_env": rate_env,
        "dff": round(float(latest), 2),
        "last_updated": last_date,
    }
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/test_phase0.py -v -k "rate_env"
```

Expected: 3개 PASS

- [ ] **Step 5: 커밋**

```bash
git add scripts/phase0_poc.py tests/test_phase0.py
git commit -m "feat: check_rate_env() with tests — DFF 금리환경 판단"
```

---

## Task 5: check_drawdown() — TDD

**Files:**
- Modify: `scripts/phase0_poc.py`
- Modify: `tests/test_phase0.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_phase0.py` 하단에 추가:

```python
# ── check_drawdown ───────────────────────────────────────────


def test_check_drawdown_current_is_ath(ixic_june_2026):
    """현재 종가가 전고점이면 하락률 0."""
    from scripts.phase0_poc import check_drawdown
    from tests.conftest import make_ixic_df

    df = make_ixic_df([1000.0, 1010.0, 1020.0, 1030.0])  # 계속 상승

    result = check_drawdown(df_ixic=df)

    assert result["status"] == "PASS"
    assert result["ath_drawdown"] == pytest.approx(0.0, abs=0.01)


def test_check_drawdown_below_ath(ixic_june_2026):
    from scripts.phase0_poc import check_drawdown

    # 전고점 27000(index 0), 현재 25678.82(index -1) → 약 -4.9%
    result = check_drawdown(df_ixic=ixic_june_2026)

    assert result["status"] == "PASS"
    assert result["ath_value"] == pytest.approx(27000.0, abs=1.0)
    assert result["ath_drawdown"] < 0
    assert result["ath_drawdown"] == pytest.approx(-4.89, abs=0.1)
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/test_phase0.py -v -k "drawdown"
```

Expected: `ImportError`

- [ ] **Step 3: check_drawdown() 구현**

`scripts/phase0_poc.py` 하단에 추가:

```python
def check_drawdown(df_ixic: pd.DataFrame = None) -> dict:
    """
    ^IXIC 전고점 대비 현재 하락률.
    main()에서 check_masam과 동일한 df_ixic을 공유해 중복 다운로드 방지.

    Returns:
        {status, ath_value, ath_date, current_close, ath_drawdown(%)}
    """
    if df_ixic is None:
        df_ixic = yf.download("^IXIC", period="2y", auto_adjust=True, progress=False)

    close = _get_close(df_ixic)
    ath_value = float(close.max())
    ath_date = close.idxmax()
    current_close = float(close.iloc[-1])
    ath_drawdown = round((current_close / ath_value - 1) * 100, 2)

    return {
        "status": "PASS",
        "ath_value": round(ath_value, 2),
        "ath_date": ath_date,
        "current_close": round(current_close, 2),
        "ath_drawdown": ath_drawdown,
    }
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/test_phase0.py -v -k "drawdown"
```

Expected: 2개 PASS

- [ ] **Step 5: 커밋**

```bash
git add scripts/phase0_poc.py tests/test_phase0.py
git commit -m "feat: check_drawdown() with tests — 전고점 대비 하락률"
```

---

## Task 6: check_qe() — TDD

**Files:**
- Modify: `scripts/phase0_poc.py`
- Modify: `tests/test_phase0.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_phase0.py` 하단에 추가:

```python
# ── check_qe ────────────────────────────────────────────────


def _make_walcl_series(values: list, start: str = "2026-04-01") -> pd.Series:
    dates = pd.date_range(start, periods=len(values), freq="W-WED")
    return pd.Series(values, index=dates, name="WALCL")


def test_check_qe_off():
    from scripts.phase0_poc import check_qe
    from unittest.mock import MagicMock

    # 8주 감소 추세 → QE_OFF
    mock_fred = MagicMock()
    mock_fred.get_series.return_value = _make_walcl_series(
        [8000, 7980, 7960, 7940, 7920, 7900, 7880, 7860]
    )

    result = check_qe(fred=mock_fred)

    assert result["status"] == "PASS"
    assert result["qe_active"] is False
    assert result["qe_state"] == "QE_OFF"


def test_check_qe_on():
    from scripts.phase0_poc import check_qe
    from unittest.mock import MagicMock

    # 8주 증가 추세 → QE_ON
    mock_fred = MagicMock()
    mock_fred.get_series.return_value = _make_walcl_series(
        [8000, 8020, 8040, 8060, 8080, 8100, 8120, 8140]
    )

    result = check_qe(fred=mock_fred)

    assert result["status"] == "PASS"
    assert result["qe_active"] is True
    assert result["qe_state"] == "QE_ON"


def test_check_qe_ambiguous():
    from scripts.phase0_poc import check_qe
    from unittest.mock import MagicMock

    # 거의 수평 → WARN (모호 구간)
    mock_fred = MagicMock()
    mock_fred.get_series.return_value = _make_walcl_series(
        [8000, 8001, 7999, 8000, 8001, 8000, 7999, 8000]
    )

    result = check_qe(fred=mock_fred)

    assert result["status"] == "WARN"
    assert result["qe_state"] == "AMBIGUOUS"
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/test_phase0.py -v -k "qe"
```

Expected: `ImportError`

- [ ] **Step 3: check_qe() 구현**

`scripts/phase0_poc.py` 하단에 추가:

```python
# WALCL 기울기 모호 판정 임계값 (4주 MA 변화율 절대값 %)
_QE_AMBIGUOUS_THRESHOLD = 0.1


def check_qe(fred: Fred = None) -> dict:
    """
    FRED WALCL(연준 총자산) 4주 이동평균 기울기로 QE 자동 감지.
    기울기 > +0.1% → QE_ON / 기울기 < -0.1% → QE_OFF / 그 사이 → WARN AMBIGUOUS

    Returns:
        {status, qe_active: bool, qe_state: str, slope_pct: float, last_updated: str}
    """
    if fred is None:
        fred = Fred(api_key=FRED_API_KEY)

    series = fred.get_series("WALCL").dropna().tail(8)
    last_date = series.index[-1].strftime("%Y-%m-%d")

    ma4 = series.rolling(4).mean().dropna()
    if len(ma4) < 2:
        return {"status": "FAIL", "error": "WALCL 데이터 부족 (4주 MA 산출 불가)"}

    # 4주 MA 기울기 = 최근값 vs 4주 전 값의 변화율(%)
    slope_pct = round(float((ma4.iloc[-1] / ma4.iloc[-2] - 1) * 100), 4)

    if slope_pct > _QE_AMBIGUOUS_THRESHOLD:
        qe_active, qe_state, status = True, "QE_ON", "PASS"
    elif slope_pct < -_QE_AMBIGUOUS_THRESHOLD:
        qe_active, qe_state, status = False, "QE_OFF", "PASS"
    else:
        qe_active, qe_state, status = False, "AMBIGUOUS", "WARN"

    return {
        "status": status,
        "qe_active": qe_active,
        "qe_state": qe_state,
        "slope_pct": slope_pct,
        "last_updated": last_date,
        "warn_message": "QE 여부 모호 — 수동 확인 필요" if status == "WARN" else None,
    }
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/test_phase0.py -v -k "qe"
```

Expected: 3개 PASS

- [ ] **Step 5: 커밋**

```bash
git add scripts/phase0_poc.py tests/test_phase0.py
git commit -m "feat: check_qe() with tests — WALCL 4주 MA 기울기 QE 자동감지"
```

---

## Task 7: check_rs_percentile() — TDD

**Files:**
- Modify: `scripts/phase0_poc.py`
- Modify: `tests/test_phase0.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_phase0.py` 하단에 추가:

```python
# ── check_rs_percentile ──────────────────────────────────────


def make_price_df(n_days: int, tickers: list, seed: int = 42) -> pd.DataFrame:
    """각 ticker의 일별 종가 mock DataFrame."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-11-01", periods=n_days)
    data = {}
    for i, t in enumerate(tickers):
        # ticker마다 다른 drift → RS 순위 분산
        drift = 0.001 * (i - len(tickers) / 2)
        returns = rng.normal(drift, 0.02, n_days)
        data[t] = 100 * np.cumprod(1 + returns)
    return pd.DataFrame(data, index=dates)


def test_check_rs_percentile_ranking():
    from scripts.phase0_poc import _calc_rs_pct

    tickers = [f"T{i}" for i in range(10)]
    prices = make_price_df(130, tickers)
    spy = prices["T0"]  # SPY mock

    rs_pcts = _calc_rs_pct(prices, spy)

    # 결과는 0~100 사이
    assert all(0 <= v <= 100 for v in rs_pcts.values())
    # 10개 종목 모두 결과 있음
    assert len(rs_pcts) == 10
    # 상위·하위 종목 순위 역전 없음
    vals = sorted(rs_pcts.values())
    assert vals == sorted(vals)


def test_check_rs_percentile_high_performer():
    from scripts.phase0_poc import _calc_rs_pct

    # T9(가장 높은 drift)가 T0보다 RS_pct가 높아야 함
    tickers = [f"T{i}" for i in range(10)]
    prices = make_price_df(130, tickers)
    spy = prices["T0"]

    rs_pcts = _calc_rs_pct(prices, spy)

    assert rs_pcts["T9"] > rs_pcts["T0"]
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/test_phase0.py -v -k "rs_percentile"
```

Expected: `ImportError`

- [ ] **Step 3: _calc_rs_pct() + check_rs_percentile() 구현**

`scripts/phase0_poc.py` 하단에 추가:

```python
# RS percentile 계산용 샘플 종목 (S&P500+NDX 대표 30개)
_RS_SAMPLE_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
    "TSLA", "AVGO", "COST", "ORCL", "AMD", "NFLX",
    "ADBE", "QCOM", "TXN", "AMAT", "INTC", "MU",
    "LRCX", "KLAC", "PANW", "CRWD", "SNPS", "CDNS",
    "MELI", "ASML", "ARM", "SMCI", "PLTR", "COIN",
]


def _calc_rs_pct(prices: pd.DataFrame, spy: pd.Series) -> dict:
    """
    RS_raw = 0.5·r20 + 0.3·r60 + 0.2·r120 (각 종목 vs SPY 초과수익률)
    RS_pct = 샘플 내 percentile rank (0~100)
    """
    rs_raw = {}
    for ticker in prices.columns:
        s = prices[ticker].dropna()
        if len(s) < 121:
            continue
        r20 = float(s.iloc[-1] / s.iloc[-20] - 1) - float(spy.iloc[-1] / spy.iloc[-20] - 1)
        r60 = float(s.iloc[-1] / s.iloc[-60] - 1) - float(spy.iloc[-1] / spy.iloc[-60] - 1)
        r120 = float(s.iloc[-1] / s.iloc[-120] - 1) - float(spy.iloc[-1] / spy.iloc[-120] - 1)
        rs_raw[ticker] = 0.5 * r20 + 0.3 * r60 + 0.2 * r120

    if not rs_raw:
        return {}

    values = list(rs_raw.values())
    rs_pct = {
        t: round(float(np.searchsorted(sorted(values), v) / len(values) * 100), 1)
        for t, v in rs_raw.items()
    }
    return rs_pct


def check_rs_percentile(prices: pd.DataFrame = None, spy: pd.Series = None) -> dict:
    """
    샘플 30종목으로 MA50 RS percentile 계산 로직 검증.
    실제 서비스에서는 S&P500+NDX 전체 롤링 캐시 사용 (Phase 1).

    Returns:
        {status, top3: list[dict], bottom3: list[dict], elapsed_sec: float}
    """
    import time

    start = time.time()

    if prices is None or spy is None:
        raw = yf.download(
            _RS_SAMPLE_TICKERS + ["SPY"],
            period="7mo",
            auto_adjust=True,
            progress=False,
        )
        if isinstance(raw.columns, pd.MultiIndex):
            close_df = raw["Close"]
        else:
            close_df = raw

        spy = close_df["SPY"]
        prices = close_df.drop(columns=["SPY"])

    rs_pcts = _calc_rs_pct(prices, spy)

    if not rs_pcts:
        return {"status": "FAIL", "error": "RS 계산 가능한 종목 없음 (데이터 부족)"}

    sorted_items = sorted(rs_pcts.items(), key=lambda x: x[1], reverse=True)
    top3 = [{"ticker": t, "rs_pct": v} for t, v in sorted_items[:3]]
    bottom3 = [{"ticker": t, "rs_pct": v} for t, v in sorted_items[-3:]]

    elapsed = round(time.time() - start, 1)

    return {
        "status": "PASS",
        "top3": top3,
        "bottom3": bottom3,
        "total_tickers": len(rs_pcts),
        "elapsed_sec": elapsed,
    }
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/test_phase0.py -v -k "rs_percentile"
```

Expected: 2개 PASS

- [ ] **Step 5: 커밋**

```bash
git add scripts/phase0_poc.py tests/test_phase0.py
git commit -m "feat: check_rs_percentile() with tests — RS percentile rank 계산"
```

---

## Task 8: check_pmi_source() — TDD

**Files:**
- Modify: `scripts/phase0_poc.py`
- Modify: `tests/test_phase0.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_phase0.py` 하단에 추가:

```python
# ── check_pmi_source ─────────────────────────────────────────


def test_check_pmi_source_pass_when_recent():
    from scripts.phase0_poc import check_pmi_source
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    # 오늘 날짜 기준 1개월 전 데이터 → 3개월 이내 → PASS
    recent_date = pd.Timestamp.today() - pd.DateOffset(months=1)
    mock_fred.get_series.return_value = pd.Series(
        [49.5], index=[recent_date]
    )

    result = check_pmi_source(fred=mock_fred)

    assert result["status"] == "PASS"


def test_check_pmi_source_warn_when_stale():
    from scripts.phase0_poc import check_pmi_source
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    # 4개월 전 데이터 → 3개월 초과 → WARN
    stale_date = pd.Timestamp.today() - pd.DateOffset(months=4)
    mock_fred.get_series.return_value = pd.Series(
        [48.5], index=[stale_date]
    )

    result = check_pmi_source(fred=mock_fred)

    assert result["status"] == "WARN"
    assert "수동입력" in result["warn_message"]


def test_check_pmi_source_warn_on_error():
    from scripts.phase0_poc import check_pmi_source
    from unittest.mock import MagicMock

    mock_fred = MagicMock()
    mock_fred.get_series.side_effect = Exception("Series not found")

    result = check_pmi_source(fred=mock_fred)

    assert result["status"] == "WARN"
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/test_phase0.py -v -k "pmi"
```

Expected: `ImportError`

- [ ] **Step 3: check_pmi_source() 구현**

`scripts/phase0_poc.py` 하단에 추가:

```python
def check_pmi_source(fred: Fred = None) -> dict:
    """
    FRED NAPM(ISM 제조업 PMI) 가용성 탐색.
    마지막 갱신이 3개월 이내 → PASS / 초과 또는 실패 → WARN (수동입력 폴백 권장).

    Returns:
        {status, series_id, last_updated, last_value, warn_message}
    """
    if fred is None:
        fred = Fred(api_key=FRED_API_KEY)

    series_id = "NAPM"
    try:
        series = fred.get_series(series_id).dropna()
        if series.empty:
            raise ValueError("빈 시리즈")

        last_date = series.index[-1]
        last_value = round(float(series.iloc[-1]), 1)
        months_ago = (pd.Timestamp.today() - last_date).days / 30

        if months_ago <= 3:
            return {
                "status": "PASS",
                "series_id": series_id,
                "last_updated": last_date.strftime("%Y-%m-%d"),
                "last_value": last_value,
                "warn_message": None,
            }
        else:
            return {
                "status": "WARN",
                "series_id": series_id,
                "last_updated": last_date.strftime("%Y-%m-%d"),
                "last_value": last_value,
                "warn_message": f"FRED {series_id} 마지막 갱신 {months_ago:.0f}개월 전 → 수동입력 폴백 권장",
            }
    except Exception as e:
        return {
            "status": "WARN",
            "series_id": series_id,
            "last_updated": None,
            "last_value": None,
            "warn_message": f"FRED {series_id} 조회 실패({e}) → 수동입력 폴백 권장",
        }
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/test_phase0.py -v -k "pmi"
```

Expected: 3개 PASS

- [ ] **Step 5: 커밋**

```bash
git add scripts/phase0_poc.py tests/test_phase0.py
git commit -m "feat: check_pmi_source() with tests — FRED NAPM 가용성 탐색"
```

---

## Task 9: main() 러너 + 전체 실행

**Files:**
- Modify: `scripts/phase0_poc.py`

- [ ] **Step 1: main() 추가**

`scripts/phase0_poc.py` 파일 하단 (함수들 뒤)에 추가:

```python
def _print_result(name: str, result: dict) -> None:
    status = result.get("status", "FAIL")
    label = f"[{status}]"
    print(f"{label} {name}")

    if status == "FAIL":
        print(f"       오류: {result.get('error', '알 수 없음')}")
        return

    if name == "^IXIC 마삼 감지":
        masam_date = result["latest_masam_date"]
        masam_str = f"{masam_date.date()} ({result['latest_masam_pct']}%)" if masam_date else "없음"
        print(f"       최근 마삼: {masam_str}")
        print(f"       이번 달 마삼: {result['month_count']}회")
        prev = result["prev_year_return"]
        print(f"       전년 역년 수익률: {prev}%" if prev is not None else "       전년 역년 수익률: 데이터 없음")
        print(f"       전고점 대비: {result['ath_drawdown']}%  (전고점: {result['ath_date'].date()} {result['ath_value']:,.2f})")

    elif name == "금리환경":
        print(f"       DFF: {result['dff']}% → {result['rate_env']}  ({result['last_updated']})")

    elif name == "전고점 대비 하락":
        print(f"       전고점: {result['ath_date'].date()} {result['ath_value']:,.2f}")
        print(f"       현재: {result['current_close']:,.2f}  하락률: {result['ath_drawdown']}%")

    elif name == "WALCL QE 자동감지":
        msg = f"기울기 {result['slope_pct']}% → {result['qe_state']}"
        if result.get("warn_message"):
            msg += f"  ⚠ {result['warn_message']}"
        print(f"       {msg}  ({result['last_updated']})")

    elif name == "MA50 RS percentile":
        top = result.get("top3", [])
        top_str = "  ".join(f"{r['ticker']}={r['rs_pct']}" for r in top)
        print(f"       상위 3: {top_str}")
        print(f"       종목 수: {result['total_tickers']}  처리시간: {result['elapsed_sec']}s")

    elif name == "PMI 소스":
        if result.get("warn_message"):
            print(f"       {result['warn_message']}")
        else:
            print(f"       FRED NAPM 최신: {result['last_updated']}  값: {result['last_value']}")


def main() -> None:
    print("=" * 60)
    print("MA3 MOMENTUM — Phase 0 데이터 PoC")
    print(f"실행일시: {pd.Timestamp.today().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    # ^IXIC 데이터를 한 번만 다운로드해 두 함수가 공유
    print("^IXIC 데이터 다운로드 중...")
    df_ixic = yf.download("^IXIC", period="2y", auto_adjust=True, progress=False)

    # FRED 클라이언트 공유
    fred = Fred(api_key=FRED_API_KEY)

    checks = [
        ("^IXIC 마삼 감지",       lambda: check_masam(df_ixic=df_ixic)),
        ("금리환경",               lambda: check_rate_env(fred=fred)),
        ("전고점 대비 하락",       lambda: check_drawdown(df_ixic=df_ixic)),
        ("WALCL QE 자동감지",     lambda: check_qe(fred=fred)),
        ("MA50 RS percentile",    check_rs_percentile),
        ("PMI 소스",               lambda: check_pmi_source(fred=fred)),
    ]

    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}

    for name, fn in checks:
        try:
            result = fn()
        except Exception as e:
            result = {"status": "FAIL", "error": str(e)}

        _print_result(name, result)
        counts[result.get("status", "FAIL")] += 1
        print()

    print("=" * 60)
    print(f"결과: PASS {counts['PASS']} / WARN {counts['WARN']} / FAIL {counts['FAIL']}")
    phase1_ok = counts["FAIL"] == 0 and counts["PASS"] >= 4
    print("Phase 1 진입 가능 ✓" if phase1_ok else "⚠ FAIL 항목 확인 후 Phase 1 진입")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 전체 단위 테스트 실행 → 모두 PASS 확인**

```bash
pytest tests/ -v
```

Expected: 전체 PASS (WARN 항목은 테스트에서 정상 처리됨)

- [ ] **Step 3: 실제 실행 (API 호출 포함)**

```bash
python scripts/phase0_poc.py
```

Expected 출력 형태:
```
============================================================
MA3 MOMENTUM — Phase 0 데이터 PoC
실행일시: 2026-06-10 ...
============================================================

^IXIC 데이터 다운로드 중...
[PASS] ^IXIC 마삼 감지
       최근 마삼: 2026-06-05 (-4.18%)
       이번 달 마삼: 1회
       ...
[WARN] PMI 소스
       FRED NAPM 조회 실패(...) → 수동입력 폴백 권장

============================================================
결과: PASS X / WARN X / FAIL 0
============================================================
```

- [ ] **Step 4: 출력 결과 확인 — 이상값 체크**

아래 항목을 눈으로 검증:
- 최근 마삼 날짜가 실제 -3% 이하인 날인지 확인
- 이번 달 마삼 횟수가 달력 월 기준인지 확인 (이전 달 카운트 누적 없음)
- 전고점이 현재 종가보다 높거나 같은지 확인
- QE 상태가 현재 시장 상황과 부합하는지 확인
- RS percentile에서 성과 좋은 종목이 상위인지 직관 검증

- [ ] **Step 5: 최종 커밋**

```bash
git add scripts/phase0_poc.py
git commit -m "feat: main() runner — phase0 poc 완성"
```

---

## 성공 기준

| 항목 | 기준 |
|---|---|
| 단위 테스트 | 전체 PASS (API 호출 없이 로직 검증) |
| 실행 결과 | FAIL 0건 |
| 마삼 날짜 | 실제 -3% 이하 날짜와 일치 |
| 이번 달 카운트 | 달력 월 독립 집계 (롤링 누적 아님) |
| 전고점 | 현재 종가 이상 |
| RS 순위 | 직관적으로 타당 (성과 좋은 종목이 상위) |
| PMI | WARN이면 수동입력 구조로 확정, PASS면 자동화 유지 |

**PASS 5 + WARN 1(PMI) 이상 → Phase 1 진입 가능**
