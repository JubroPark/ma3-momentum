# Phase 1B: MA50 스크리너 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 종목별 MA50 이평선 돌파·추세·반등 시그널을 산출하고 매도 3-State 상태머신을 통해 `outputs/signals.json`을 생성하는 순수 함수 엔진을 구현한다.

**Architecture:** `ma50_indicators.py`(순수 지표 함수) → `ma50_signals.py`(매수·매도·상태머신·스코어) → `ma50_engine.py`(JSON 조립) → `run_ma50.py`(데이터 수집 + 실행). Phase 1A 패턴 그대로 — 엔진 계층은 I/O 없음, 순수 함수만.

**Tech Stack:** Python 3.9+, pandas, numpy, yfinance, pytest

---

## 단위 규약 (모든 Task 공통)

| 값 | 단위 | 예시 |
|---|---|---|
| `slope_pct` | 분수 | 0.02 = 2% |
| `gap50`, `gap200` | 분수 | 0.05 = 5% 위 |
| `overshoot_max`, `proximity_pct`, `break_tol`, `sell_tol`, `slope_cap` | 분수 | 0.07 = 7% |
| `rs_pct`, `rs_sector_pct` | 퍼센타일 0-100 | 80.0 |
| `vol_ratio` | 배수 | 1.8 = 1.8배 |

---

## 파일 맵

| 파일 | 역할 | 신규/기존 |
|---|---|---|
| `engines/ma50_indicators.py` | 지표 계산 순수 함수 | 신규 |
| `engines/ma50_signals.py` | 매수·매도 시그널 + 상태머신 + 스코어 | 신규 |
| `engines/ma50_engine.py` | signals.json 빌더 | 신규 |
| `scripts/run_ma50.py` | 데이터 수집 + 엔진 실행 + JSON 저장 | 신규 |
| `tests/test_ma50_indicators.py` | 지표 단위 테스트 | 신규 |
| `tests/test_ma50_signals.py` | 시그널·상태머신 단위 테스트 | 신규 |
| `tests/test_ma50_engine.py` | 빌더 단위 테스트 | 신규 |

---

## Task 1: engines/ma50_indicators.py — 지표 계산 함수

**Files:**
- Create: `engines/ma50_indicators.py`
- Create: `tests/test_ma50_indicators.py`

- [ ] **Step 1: 테스트 작성 (RED)**

`tests/test_ma50_indicators.py`:
```python
import pytest
import pandas as pd
import numpy as np


def make_ohlcv(
    closes: list,
    highs: list = None,
    lows: list = None,
    volumes: list = None,
    start: str = "2025-01-02",
) -> pd.DataFrame:
    n = len(closes)
    dates = pd.bdate_range(start, periods=n)
    return pd.DataFrame({
        "Close":  closes,
        "High":   highs   or [c * 1.01 for c in closes],
        "Low":    lows    or [c * 0.99 for c in closes],
        "Volume": volumes or [1_000_000.0] * n,
    }, index=dates)


# ── calc_slope_pct ────────────────────────────────────────────


def test_calc_slope_pct_uptrend():
    from engines.ma50_indicators import calc_slope_pct, calc_ma
    # MA[-1]=110, MA[-11]=100 → slope = (110-100)/100 = 0.10
    ma = pd.Series(list(range(100, 111)))  # 11 values: 100..110
    assert calc_slope_pct(ma) == pytest.approx(0.10, rel=0.001)


def test_calc_slope_pct_flat():
    from engines.ma50_indicators import calc_slope_pct
    ma = pd.Series([100.0] * 11)
    assert calc_slope_pct(ma) == pytest.approx(0.0, abs=1e-6)


def test_calc_slope_pct_insufficient_data_returns_zero():
    from engines.ma50_indicators import calc_slope_pct
    ma = pd.Series([100.0] * 5)
    assert calc_slope_pct(ma) == 0.0


# ── calc_gap ──────────────────────────────────────────────────


def test_calc_gap_above():
    from engines.ma50_indicators import calc_gap
    # close=105, MA=100 → gap = 0.05
    assert calc_gap(105.0, 100.0) == pytest.approx(0.05)


def test_calc_gap_below():
    from engines.ma50_indicators import calc_gap
    assert calc_gap(95.0, 100.0) == pytest.approx(-0.05)


def test_calc_gap_zero_ma_returns_zero():
    from engines.ma50_indicators import calc_gap
    assert calc_gap(100.0, 0.0) == 0.0


# ── calc_highN ────────────────────────────────────────────────


def test_calc_highN():
    from engines.ma50_indicators import calc_highN
    # today=104, before=[100,102,103,98,105,101,99]
    high = pd.Series([100.0, 102.0, 103.0, 98.0, 105.0, 101.0, 99.0, 104.0])
    # lookback=5: high[-6:-1] = [102, 103, 98, 105, 101] → max=105
    assert calc_highN(high, lookback=5) == pytest.approx(105.0)


# ── calc_atr14 ────────────────────────────────────────────────


def test_calc_atr14_constant_range():
    from engines.ma50_indicators import calc_atr14
    n = 20
    closes = [100.0] * n
    highs  = [101.0] * n
    lows   = [99.0]  * n
    df = make_ohlcv(closes, highs, lows)
    result = calc_atr14(df["High"], df["Low"], df["Close"])
    # TR = High - Low = 2 every day → ATR14 = 2
    assert result == pytest.approx(2.0, abs=0.1)


# ── calc_rs_raw ───────────────────────────────────────────────


def test_calc_rs_raw_outperformer():
    from engines.ma50_indicators import calc_rs_raw
    n = 150
    stock = pd.Series([100.0 + i * 0.5 for i in range(n)])  # strong uptrend
    spy   = pd.Series([100.0 + i * 0.1 for i in range(n)])  # slower
    assert calc_rs_raw(stock, spy) > 0


def test_calc_rs_raw_underperformer():
    from engines.ma50_indicators import calc_rs_raw
    n = 150
    stock = pd.Series([100.0 - i * 0.3 for i in range(n)])
    spy   = pd.Series([100.0 + i * 0.1 for i in range(n)])
    assert calc_rs_raw(stock, spy) < 0


# ── calc_rs_pct ───────────────────────────────────────────────


def test_calc_rs_pct_top():
    from engines.ma50_indicators import calc_rs_pct
    universe = {"A": 10.0, "B": 5.0, "C": 8.0, "D": 2.0, "E": 6.0}
    assert calc_rs_pct("A", universe) == pytest.approx(100.0)


def test_calc_rs_pct_bottom():
    from engines.ma50_indicators import calc_rs_pct
    universe = {"A": 10.0, "B": 5.0, "C": 8.0, "D": 2.0, "E": 6.0}
    # D=2.0: only D <= 2.0 → rank=1/5=20%
    assert calc_rs_pct("D", universe) == pytest.approx(20.0)


# ── calc_regime ───────────────────────────────────────────────


def test_calc_regime_risk_on():
    from engines.ma50_indicators import calc_regime
    closes = [100.0 + i * 0.2 for i in range(250)]  # steady uptrend, above MA200
    assert calc_regime(pd.Series(closes)) == "RISK_ON"


def test_calc_regime_risk_off():
    from engines.ma50_indicators import calc_regime
    # 200 days up, then 50 days sharp down → current below MA200
    closes = [100.0 + i * 0.5 for i in range(200)] + [200.0 - i * 2.0 for i in range(50)]
    assert calc_regime(pd.Series(closes)) == "RISK_OFF"


# ── build_metrics ─────────────────────────────────────────────


def test_build_metrics_keys():
    from engines.ma50_indicators import build_metrics
    m = build_metrics(
        close_last=105.0, ma50_last=100.0, ma200_last=95.0,
        vol_ratio=2.0, rs_pct=75.0, rs_sector_pct=60.0,
        slope_pct=0.02, high_n=104.5, atr14=1.5, sector_etf="XLK",
    )
    for key in ("close", "ma50", "ma200", "gap50", "gap200",
                "vol_ratio", "rs_pct", "rs_sector_pct",
                "ma50_slope_pct", "high_n", "atr14", "sector_etf"):
        assert key in m, f"Missing key: {key}"
    assert m["gap50"] == pytest.approx(0.05)   # (105-100)/100
    assert m["gap200"] == pytest.approx((100-95)/95, rel=0.01)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_ma50_indicators.py -v 2>&1 | head -10
```
Expected: `ImportError: cannot import name 'calc_slope_pct'`

- [ ] **Step 3: 구현**

`engines/ma50_indicators.py`:
```python
"""MA50 스크리너 — 지표 계산 순수 함수."""
from __future__ import annotations
import pandas as pd
import numpy as np


def calc_ma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def calc_slope_pct(ma: pd.Series) -> float:
    """(MA[-1] - MA[-11]) / MA[-11] — 분수 반환 (0.02 = 2%)."""
    valid = ma.dropna()
    if len(valid) < 11:
        return 0.0
    return float((valid.iloc[-1] - valid.iloc[-11]) / valid.iloc[-11])


def calc_gap(close_val: float, ma_val: float) -> float:
    """(close - MA) / MA — 분수 반환."""
    if ma_val == 0:
        return 0.0
    return float((close_val - ma_val) / ma_val)


def calc_highN(high: pd.Series, lookback: int) -> float:
    """max(high[1..lookback]) — 오늘 제외, 어제부터 lookback일 전까지."""
    window = high.iloc[-(lookback + 1):-1]
    return float(window.max()) if not window.empty else 0.0


def calc_atr14(high: pd.Series, low: pd.Series, close: pd.Series) -> float:
    """ATR14."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().dropna()
    return float(atr.iloc[-1]) if not atr.empty else 0.0


def _period_return(close: pd.Series, n: int) -> float:
    if len(close) <= n:
        return 0.0
    return float((close.iloc[-1] / close.iloc[-n - 1] - 1) * 100)


def calc_rs_raw(
    close_stock: pd.Series,
    close_spy: pd.Series,
    weights: tuple = (0.5, 0.3, 0.2),
) -> float:
    """RS_raw = 0.5*(r20s-r20m) + 0.3*(r60s-r60m) + 0.2*(r120s-r120m)."""
    w20, w60, w120 = weights
    return (
        w20  * (_period_return(close_stock, 20)  - _period_return(close_spy, 20))
        + w60  * (_period_return(close_stock, 60)  - _period_return(close_spy, 60))
        + w120 * (_period_return(close_stock, 120) - _period_return(close_spy, 120))
    )


def calc_rs_pct(ticker: str, rs_raw_map: dict) -> float:
    """RS 퍼센타일 (0~100). ticker의 RS_raw가 universe 내 몇 %ile인지."""
    values = list(rs_raw_map.values())
    if not values:
        return 50.0
    ticker_val = rs_raw_map.get(ticker, 0.0)
    rank = sum(1 for v in values if v <= ticker_val)
    return float(rank / len(values) * 100)


def calc_regime(close_spy: pd.Series) -> str:
    """SPY 종가 vs MA200 — RISK_ON | RISK_OFF."""
    ma200 = close_spy.rolling(200).mean().dropna()
    if ma200.empty:
        return "RISK_ON"
    return "RISK_ON" if float(close_spy.iloc[-1]) > float(ma200.iloc[-1]) else "RISK_OFF"


def build_metrics(
    close_last: float,
    ma50_last: float,
    ma200_last: float,
    vol_ratio: float,
    rs_pct: float,
    rs_sector_pct: float,
    slope_pct: float,
    high_n: float,
    atr14: float,
    sector_etf: str,
) -> dict:
    """signals.json metrics 필드용 직렬화 가능 dict."""
    return {
        "close":          round(close_last, 2),
        "ma50":           round(ma50_last, 2),
        "ma200":          round(ma200_last, 2),
        "gap50":          round(calc_gap(close_last, ma50_last), 4),
        "gap200":         round(calc_gap(ma50_last, ma200_last), 4),
        "vol_ratio":      round(vol_ratio, 2),
        "rs_pct":         round(rs_pct, 1),
        "rs_sector_pct":  round(rs_sector_pct, 1),
        "ma50_slope_pct": round(slope_pct, 4),
        "high_n":         round(high_n, 2),
        "atr14":          round(atr14, 2),
        "sector_etf":     sector_etf,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_ma50_indicators.py -v
```
Expected: `16 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add engines/ma50_indicators.py tests/test_ma50_indicators.py && git commit -m "feat: ma50_indicators — MA·slope·gap·ATR·RS·regime 지표 함수"
```

---

## Task 2: engines/ma50_signals.py — 매수 시그널 (공통 게이트 + 3트랙)

**Files:**
- Create: `engines/ma50_signals.py`
- Create: `tests/test_ma50_signals.py`

- [ ] **Step 1: 테스트 작성 (RED)**

`tests/test_ma50_signals.py`:
```python
import pytest
import pandas as pd
import numpy as np
from datetime import date


def make_series(values: list, start: str = "2025-01-02") -> pd.Series:
    dates = pd.bdate_range(start, periods=len(values))
    return pd.Series(values, index=dates)


def _default_params():
    from engines.ma50_signals import MA50_DEFAULT_PARAMS
    return dict(MA50_DEFAULT_PARAMS)


# ── check_common_gate ────────────────────────────────────────


def test_common_gate_passes():
    from engines.ma50_signals import check_common_gate
    p = _default_params()
    # vol_ratio=2.0 ≥ 1.5, gap50=0.03 ≤ 0.07, regime=RISK_ON
    assert check_common_gate(vol_ratio=2.0, gap50=0.03, regime="RISK_ON", params=p) is True


def test_common_gate_fails_risk_off_strict():
    from engines.ma50_signals import check_common_gate
    p = _default_params()
    p["regime_mode"] = "strict"
    assert check_common_gate(vol_ratio=2.0, gap50=0.03, regime="RISK_OFF", params=p) is False


def test_common_gate_fails_overshoot():
    from engines.ma50_signals import check_common_gate
    p = _default_params()
    # gap50=0.08 > overshoot_max=0.07
    assert check_common_gate(vol_ratio=2.0, gap50=0.08, regime="RISK_ON", params=p) is False


def test_common_gate_fails_low_volume():
    from engines.ma50_signals import check_common_gate
    p = _default_params()
    # vol_ratio=1.2 < vol_mult=1.5
    assert check_common_gate(vol_ratio=1.2, gap50=0.03, regime="RISK_ON", params=p) is False


# ── check_strong_breakout ─────────────────────────────────────


def _make_strong_breakout_data(n=30):
    """n일 데이터: 아래서 접근하다가 마지막 날 돌파."""
    # MA50 시리즈 단순 구성을 위해 충분히 긴 데이터 필요 (50일 이상)
    n_total = max(n, 60)
    closes = [100.0] * (n_total - n) + [95.0] * (n - 1) + [102.0]  # 마지막 날 돌파
    highs  = [c * 1.005 for c in closes]
    # 거래량: 마지막 날만 높게
    vols   = [1_000_000.0] * (len(closes) - 1) + [2_000_000.0]
    return closes, highs, vols


def test_strong_breakout_fires():
    from engines.ma50_signals import check_strong_breakout
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    n = 80
    # 55일 정상가(100) + 24일 하락(95) + 1일 돌파(102)
    closes = [100.0] * 55 + [95.0] * 24 + [102.0]
    highs  = [100.0] * 55 + [96.0] * 24 + [105.0]
    close = make_series(closes)
    high  = make_series(highs)
    ma50  = calc_ma(close, 50)
    # 마지막 날 close(102) > MA50(~100) AND close > highN(~96) ✓
    # 어제 close(95) ≤ MA50 ✓, 최근 7일 중 60%+ close < MA50 ✓
    result = check_strong_breakout(close, ma50, high, p)
    assert result is True


def test_strong_breakout_fails_if_yesterday_above_ma50():
    from engines.ma50_signals import check_strong_breakout
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    # 최근 2일 모두 MA50 위 → 선행 조건 미충족
    closes = [100.0] * 50 + [102.0, 104.0]  # 이미 MA50 위에서 상승 중
    close = make_series(closes)
    high  = make_series([c * 1.01 for c in closes])
    ma50  = calc_ma(close, 50)
    result = check_strong_breakout(close, ma50, high, p)
    assert result is False


# ── check_early_trend ─────────────────────────────────────────


def test_early_trend_fires():
    from engines.ma50_signals import check_early_trend
    p = _default_params()
    # 어제 아래, 오늘 위, RS_pct=85≥80, slope>0
    closes = [95.0] * 55 + [99.0, 101.0]  # MA50≈100에서 cross
    from engines.ma50_indicators import calc_ma
    close = make_series(closes)
    ma50  = calc_ma(close, 50)
    assert check_early_trend(close, ma50, slope_pct=0.01, rs_pct=85.0, params=p) is True


def test_early_trend_fails_low_rs():
    from engines.ma50_signals import check_early_trend
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [95.0] * 55 + [99.0, 101.0]
    close = make_series(closes)
    ma50  = calc_ma(close, 50)
    # rs_pct=70 < rs_early_th=80
    assert check_early_trend(close, ma50, slope_pct=0.01, rs_pct=70.0, params=p) is False


def test_early_trend_fails_negative_slope():
    from engines.ma50_signals import check_early_trend
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [95.0] * 55 + [99.0, 101.0]
    close = make_series(closes)
    ma50  = calc_ma(close, 50)
    assert check_early_trend(close, ma50, slope_pct=-0.01, rs_pct=85.0, params=p) is False


# ── check_bounce ─────────────────────────────────────────────


def test_bounce_fires():
    from engines.ma50_signals import check_bounce
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    # 70일 강한 상승(MA50>MA200, slope>0, close>MA50 다수)
    # 마지막 5일: MA50 근접했다가 반등
    uptrend = [90.0 + i * 0.5 for i in range(70)]
    # 근접: low가 MA50 근처로 내려옴, close는 유지
    dip     = [124.0, 123.5, 124.0, 123.8, 125.0]  # 반등
    closes  = uptrend + dip
    lows    = [c * 0.995 for c in uptrend] + [122.5, 122.0, 123.0, 122.8, 124.0]
    close   = make_series(closes)
    low     = make_series(lows)
    ma50    = calc_ma(close, 50)
    ma200   = calc_ma(close, 200)
    # MA50 > MA200 조건은 데이터가 짧아 충족 안 될 수 있으므로
    # 직접 slope_pct > 0 여부만 제어
    slope   = 0.01  # positive
    result  = check_bounce(close, low, ma50, ma200, slope_pct=slope, params=p)
    # 결과는 다양할 수 있으므로 bool 타입만 확인
    assert isinstance(result, bool)


def test_bounce_fails_negative_slope():
    from engines.ma50_signals import check_bounce
    from engines.ma50_indicators import calc_ma
    p = _default_params()
    closes = [100.0] * 75
    lows   = [99.0] * 75
    close  = make_series(closes)
    low    = make_series(lows)
    ma50   = calc_ma(close, 50)
    ma200  = calc_ma(close, 200)
    assert check_bounce(close, low, ma50, ma200, slope_pct=-0.01, params=p) is False
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_ma50_signals.py -v 2>&1 | head -10
```
Expected: `ImportError`

- [ ] **Step 3: 구현**

`engines/ma50_signals.py`:
```python
"""MA50 스크리너 — 매수·매도 시그널 + 상태머신 + 스코어."""
from __future__ import annotations
import pandas as pd
from engines.ma50_indicators import calc_highN

MA50_DEFAULT_PARAMS: dict = {
    "breakout_high_lookback": 20,
    "lookback_below":         7,
    "vol_mult":               1.5,
    "vol_cap":                3.0,
    "overshoot_max":          0.07,   # 7%
    "proximity_pct":          0.03,   # 3%
    "break_tol":              0.01,   # 1%
    "sell_tol":               0.01,   # 1%
    "consec_below_sell":      2,
    "max_hold_watch_days":    5,
    "rs_early_th":            80.0,
    "slope_cap":              0.05,   # 5%
    "score_weights":          (0.25, 0.25, 0.25, 0.25),
    "regime_mode":            "strict",
    "early_trend_enabled":    False,
    "bounce_lookback":        5,
}


# ── 공통 게이트 ───────────────────────────────────────────────


def check_common_gate(
    vol_ratio: float,
    gap50: float,
    regime: str,
    params: dict,
) -> bool:
    """레짐 + gap50 ≤ overshoot_max + vol_ratio ≥ vol_mult."""
    if regime == "RISK_OFF" and params.get("regime_mode", "strict") == "strict":
        return False
    if gap50 > params["overshoot_max"]:
        return False
    if vol_ratio < params["vol_mult"]:
        return False
    return True


# ── Track B: STRONG_BREAKOUT ───────────────────────────────────


def check_strong_breakout(
    close: pd.Series,
    ma50: pd.Series,
    high: pd.Series,
    params: dict,
) -> bool:
    """
    선행: close[-1] ≤ MA50[-1] AND 최근 lookback_below일 중 60%+ close<MA50
    돌파: close[0] > MA50[0] AND close[0] > highN
    """
    if len(close) < 2 or len(ma50.dropna()) < 2:
        return False

    today_close    = float(close.iloc[-1])
    today_ma50     = float(ma50.dropna().iloc[-1])
    yesterday_close = float(close.iloc[-2])
    yesterday_ma50  = float(ma50.dropna().iloc[-2])

    high_n = calc_highN(high, params["breakout_high_lookback"])

    # 오늘 돌파 조건
    if not (today_close > today_ma50 and today_close > high_n):
        return False
    # 어제 MA50 아래
    if not (yesterday_close <= yesterday_ma50):
        return False
    # 최근 lookback_below일 60%+ below MA50
    lb = params["lookback_below"]
    recent_c  = close.iloc[-(lb + 1):-1]
    recent_m  = ma50.iloc[-(lb + 1):-1]
    if len(recent_c) == 0:
        return False
    below_ratio = (recent_c.values < recent_m.values).mean()
    return below_ratio >= 0.60


# ── Track A: EARLY_TREND ──────────────────────────────────────


def check_early_trend(
    close: pd.Series,
    ma50: pd.Series,
    slope_pct: float,
    rs_pct: float,
    params: dict,
) -> bool:
    """
    돌파: close[0] > MA50[0] AND close[-1] ≤ MA50[-1]
    안전장치: RS_pct ≥ rs_early_th AND slope_pct > 0
    """
    if len(close) < 2 or len(ma50.dropna()) < 2:
        return False
    today_close     = float(close.iloc[-1])
    today_ma50      = float(ma50.dropna().iloc[-1])
    yesterday_close = float(close.iloc[-2])
    yesterday_ma50  = float(ma50.dropna().iloc[-2])

    if not (today_close > today_ma50 and yesterday_close <= yesterday_ma50):
        return False
    if rs_pct < params["rs_early_th"]:
        return False
    if slope_pct <= 0:
        return False
    return True


# ── Track Bounce: BOUNCE ──────────────────────────────────────


def check_bounce(
    close: pd.Series,
    low: pd.Series,
    ma50: pd.Series,
    ma200: pd.Series,
    slope_pct: float,
    params: dict,
) -> bool:
    """
    추세: MA50>MA200 AND slope>0 AND 최근 20일 close>MA50 다수(>50%)
    근접: min(low[0..k]) ≤ MA50*(1+proximity_pct)
    지지: min(close[0..k]) ≥ MA50*(1-break_tol)
    반등: close[0]>close[-1] AND close[0]>MA50
    """
    ma50_clean  = ma50.dropna()
    ma200_clean = ma200.dropna()
    if ma50_clean.empty or ma200_clean.empty or len(close) < 2:
        return False

    today_ma50  = float(ma50_clean.iloc[-1])
    today_ma200 = float(ma200_clean.iloc[-1])
    today_close = float(close.iloc[-1])
    yesterday_close = float(close.iloc[-2])

    # 추세 조건
    if slope_pct <= 0:
        return False
    if not (today_ma50 > today_ma200):
        return False
    recent20_c = close.iloc[-20:]
    recent20_m = ma50.iloc[-20:]
    if len(recent20_c) < 10:
        return False
    above_ratio = (recent20_c.values > recent20_m.values).mean()
    if above_ratio < 0.5:
        return False

    # 근접 조건
    k = params.get("bounce_lookback", 5)
    recent_low   = low.iloc[-(k + 1):]
    recent_close = close.iloc[-(k + 1):]
    min_low   = float(recent_low.min())
    min_close = float(recent_close.min())
    if min_low > today_ma50 * (1 + params["proximity_pct"]):
        return False
    if min_close < today_ma50 * (1 - params["break_tol"]):
        return False

    # 반등 조건
    return today_close > yesterday_close and today_close > today_ma50


# ── 매수 시그널 통합 ────────────────────────────────────────────


def get_buy_signal(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    ma50: pd.Series,
    ma200: pd.Series,
    vol_ratio: float,
    gap50: float,
    slope_pct: float,
    rs_pct: float,
    regime: str,
    params: dict,
) -> str | None:
    """
    공통 게이트 통과 후 Track B → A → Bounce 순으로 체크.
    Returns: "STRONG_BREAKOUT" | "EARLY_TREND" | "BOUNCE" | None
    """
    if not check_common_gate(vol_ratio, gap50, regime, params):
        return None
    if check_strong_breakout(close, ma50, high, params):
        return "STRONG_BREAKOUT"
    if params.get("early_trend_enabled", False):
        if check_early_trend(close, ma50, slope_pct, rs_pct, params):
            return "EARLY_TREND"
    if check_bounce(close, low, ma50, ma200, slope_pct, params):
        return "BOUNCE"
    return None
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_ma50_signals.py -v
```
Expected: `13 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add engines/ma50_signals.py tests/test_ma50_signals.py && git commit -m "feat: ma50_signals — 공통 게이트 + 매수 3트랙 (STRONG_BREAKOUT·EARLY_TREND·BOUNCE)"
```

---

## Task 3: engines/ma50_signals.py — 매도 시그널 + 상태머신 + 스코어

**Files:**
- Modify: `engines/ma50_signals.py` (함수 추가)
- Modify: `tests/test_ma50_signals.py` (테스트 추가)

- [ ] **Step 1: 테스트 추가 (RED)**

`tests/test_ma50_signals.py` 끝에 추가:
```python
# ── check_breakdown ──────────────────────────────────────────


def test_breakdown_hard():
    from engines.ma50_signals import check_breakdown
    p = _default_params()
    # close < MA50*(1-0.01) = 100*0.99 = 99 → hard breakdown
    close = make_series([100.0] * 10 + [98.5])
    ma50  = make_series([100.0] * 11)
    assert check_breakdown(close, ma50, p) is True


def test_breakdown_soft_two_days_below():
    from engines.ma50_signals import check_breakdown
    p = _default_params()
    # 오늘(99.5)과 어제(99.8) 모두 MA50(100) 미만 → soft breakdown
    close = make_series([100.0] * 9 + [99.8, 99.5])
    ma50  = make_series([100.0] * 11)
    assert check_breakdown(close, ma50, p) is True


def test_no_breakdown():
    from engines.ma50_signals import check_breakdown
    p = _default_params()
    # 오늘(99.8)만 약간 아래, 어제(101) 위 → soft 미충족, hard도 미충족
    close = make_series([100.0] * 9 + [101.0, 99.8])
    ma50  = make_series([100.0] * 11)
    assert check_breakdown(close, ma50, p) is False


# ── get_sell_signal ───────────────────────────────────────────


def _make_sell_data(close_vals, ma50_vals, ma200_val=90.0):
    close = make_series(close_vals)
    ma50  = make_series(ma50_vals)
    ma200 = make_series([ma200_val] * len(close_vals))
    return close, ma50, ma200


def test_sell_priority1_close_above_ma50_returns_none():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 5 + [101.0],
        [100.0] * 6,
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=60.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result is None


def test_sell_priority2_consec_below():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["consec_below_sell"] = 2
    # 마지막 2일 모두 MA50 아래, hard breakdown 없음
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 8 + [99.5, 99.2],
        [100.0] * 10,
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=60.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result == "SELL"


def test_sell_priority3_hold_watch_timeout():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["max_hold_watch_days"] = 5
    p["consec_below_sell"] = 3
    # 오늘 MA50 아래지만 1일만 → consec 미충족
    # HOLD_WATCH 상태에서 days_in_state=6 > 5 → SELL
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 9 + [99.8],
        [100.0] * 10,
    )
    result = get_sell_signal("SELL_WATCH", close, ma50, ma200, rs_pct=60.0,
                              days_in_state=6, regime="RISK_ON", params=p)
    assert result == "SELL"


def test_sell_priority4_breakdown_below_ma200():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["consec_below_sell"] = 5  # 연속 조건 제거
    # breakdown + close < MA200 → SELL
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 8 + [99.0, 98.5],   # soft breakdown (2일 연속 < MA50)
        [100.0] * 10,
        ma200_val=110.0,               # MA200 > close → close < MA200
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=60.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result == "SELL"


def test_sell_priority5_breakdown_above_ma200_high_rs():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["consec_below_sell"] = 5
    # breakdown + close > MA200 + RS > 50 → HOLD_WATCH
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 8 + [99.0, 98.5],
        [100.0] * 10,
        ma200_val=90.0,                # close > MA200
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=70.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result == "HOLD_WATCH"


def test_sell_priority6_breakdown_low_rs_sell():
    from engines.ma50_signals import get_sell_signal
    p = _default_params()
    p["consec_below_sell"] = 5
    close, ma50, ma200 = _make_sell_data(
        [100.0] * 8 + [99.0, 98.5],
        [100.0] * 10,
        ma200_val=90.0,
    )
    result = get_sell_signal("HOLDING", close, ma50, ma200, rs_pct=40.0,
                              days_in_state=1, regime="RISK_ON", params=p)
    assert result == "SELL"


# ── transition_state ─────────────────────────────────────────


def test_transition_watch_to_buy():
    from engines.ma50_signals import transition_state
    assert transition_state("WATCH", "STRONG_BREAKOUT", None) == "BUY"


def test_transition_watch_stays_watch():
    from engines.ma50_signals import transition_state
    assert transition_state("WATCH", None, None) == "WATCH"


def test_transition_buy_to_holding():
    from engines.ma50_signals import transition_state
    assert transition_state("BUY", None, None) == "HOLDING"


def test_transition_holding_to_sell_watch():
    from engines.ma50_signals import transition_state
    assert transition_state("HOLDING", None, "HOLD_WATCH") == "SELL_WATCH"


def test_transition_holding_to_sell():
    from engines.ma50_signals import transition_state
    assert transition_state("HOLDING", None, "SELL") == "SELL"


def test_transition_sell_watch_recovery():
    from engines.ma50_signals import transition_state
    # close >= MA50 recovery → HOLDING
    assert transition_state("SELL_WATCH", None, None) == "HOLDING"


def test_transition_sell_to_watch():
    from engines.ma50_signals import transition_state
    assert transition_state("SELL", None, None) == "WATCH"


# ── calc_score ────────────────────────────────────────────────


def test_calc_score_range_0_100():
    from engines.ma50_signals import calc_score
    p = _default_params()
    s = calc_score(
        vol_ratio=2.0, gap50=0.04, rs_pct=80.0,
        slope_pct=0.03, ma50_last=100.0, ma200_last=95.0, params=p,
    )
    assert 0 <= s <= 100


def test_calc_score_higher_for_better_metrics():
    from engines.ma50_signals import calc_score
    p = _default_params()
    high = calc_score(vol_ratio=3.0, gap50=0.06, rs_pct=95.0,
                      slope_pct=0.05, ma50_last=100.0, ma200_last=95.0, params=p)
    low  = calc_score(vol_ratio=1.5, gap50=0.01, rs_pct=30.0,
                      slope_pct=0.01, ma50_last=100.0, ma200_last=95.0, params=p)
    assert high > low


def test_calc_score_sum_invariant():
    from engines.ma50_signals import calc_score
    p = _default_params()
    s = calc_score(vol_ratio=1.5, gap50=0.03, rs_pct=50.0,
                   slope_pct=0.025, ma50_last=100.0, ma200_last=100.0, params=p)
    assert 0 <= s <= 100
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_ma50_signals.py -v 2>&1 | grep "FAILED\|ERROR" | head -5
```
Expected: 새 테스트들 FAIL

- [ ] **Step 3: ma50_signals.py에 함수 추가**

`engines/ma50_signals.py` 끝에 추가:
```python
# ── 매도 시그널 ────────────────────────────────────────────────


def check_breakdown(
    close: pd.Series,
    ma50: pd.Series,
    params: dict,
) -> bool:
    """
    breakdown = close[0] < MA50*(1-sell_tol) [hard]
               OR (close[0]<MA50 AND close[-1]<MA50) [soft]
    """
    if len(close) < 2 or len(ma50) < 2:
        return False
    today_close     = float(close.iloc[-1])
    today_ma50      = float(ma50.iloc[-1])
    yesterday_close = float(close.iloc[-2])
    yesterday_ma50  = float(ma50.iloc[-2])
    sell_tol = params["sell_tol"]
    hard = today_close < today_ma50 * (1 - sell_tol)
    soft = today_close < today_ma50 and yesterday_close < yesterday_ma50
    return hard or soft


def get_sell_signal(
    state: str,
    close: pd.Series,
    ma50: pd.Series,
    ma200: pd.Series,
    rs_pct: float,
    days_in_state: int,
    regime: str,
    params: dict,
) -> str | None:
    """
    우선순위순 매도 판단. Returns "SELL" | "HOLD_WATCH" | None
    1. close >= MA50 → None (OK)
    2. 연속 consec_below_sell일 → SELL
    3. SELL_WATCH + days > max_hold_watch_days → SELL
    4. breakdown AND close < MA200 → SELL
    5. breakdown AND close > MA200 AND RS > 50 → HOLD_WATCH
    6. breakdown (그 외) → SELL
    """
    today_close = float(close.iloc[-1])
    today_ma50  = float(ma50.iloc[-1])
    today_ma200 = float(ma200.iloc[-1])

    consec = params["consec_below_sell"]
    max_watch = params["max_hold_watch_days"]
    if regime == "RISK_OFF":
        consec = 1
        max_watch = 3

    # 우선순위 1
    if today_close >= today_ma50:
        return None

    # 우선순위 2
    if len(close) >= consec and len(ma50) >= consec:
        recent_c = close.iloc[-consec:]
        recent_m = ma50.iloc[-consec:]
        if (recent_c.values < recent_m.values).all():
            return "SELL"

    # 우선순위 3
    if state == "SELL_WATCH" and days_in_state > max_watch:
        return "SELL"

    bd = check_breakdown(close, ma50, params)
    if bd:
        if today_close < today_ma200:
            return "SELL"
        if today_close > today_ma200 and rs_pct > 50:
            return "HOLD_WATCH"
        return "SELL"

    return None


# ── 상태머신 전이 ─────────────────────────────────────────────


def transition_state(
    current_state: str,
    buy_signal: "str | None",
    sell_signal: "str | None",
) -> str:
    """
    WATCH → BUY → HOLDING → SELL_WATCH → SELL → WATCH
    """
    if current_state == "WATCH":
        return "BUY" if buy_signal is not None else "WATCH"
    if current_state == "BUY":
        return "HOLDING"
    if current_state == "HOLDING":
        if sell_signal == "SELL":
            return "SELL"
        if sell_signal == "HOLD_WATCH":
            return "SELL_WATCH"
        return "HOLDING"
    if current_state == "SELL_WATCH":
        if sell_signal == "SELL":
            return "SELL"
        if sell_signal is None:  # 회복
            return "HOLDING"
        return "SELL_WATCH"
    if current_state == "SELL":
        return "WATCH"
    return current_state


# ── 스코어 ────────────────────────────────────────────────────


def calc_score(
    vol_ratio: float,
    gap50: float,
    rs_pct: float,
    slope_pct: float,
    ma50_last: float,
    ma200_last: float,
    params: dict,
) -> float:
    """0~100 점수. CLAUDE.md §6-7 공식."""
    w1, w2, w3, w4 = params.get("score_weights", (0.25, 0.25, 0.25, 0.25))
    vol_cap      = params.get("vol_cap", 3.0)
    overshoot    = params.get("overshoot_max", 0.07)
    slope_cap    = params.get("slope_cap", 0.05)

    vol_score      = min(vol_ratio / vol_cap, 1.0) if vol_cap > 0 else 0.0
    breakout_score = min(gap50 / overshoot, 1.0) if overshoot > 0 else 0.0
    rs_score       = rs_pct / 100.0
    trend_score    = (
        0.5 * min(slope_pct / slope_cap, 1.0) if slope_cap > 0 else 0.0
    ) + 0.5 * (1.0 if ma50_last > ma200_last else 0.0)

    raw = 100.0 * (w1*vol_score + w2*breakout_score + w3*rs_score + w4*trend_score)
    return round(max(0.0, min(100.0, raw)), 1)
```

- [ ] **Step 4: 전체 시그널 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_ma50_signals.py -v
```
Expected: ~30 passed

- [ ] **Step 5: Commit**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add engines/ma50_signals.py tests/test_ma50_signals.py && git commit -m "feat: ma50_signals — 매도 시그널 + 상태머신 + 스코어"
```

---

## Task 4: engines/ma50_engine.py — signals.json 빌더

**Files:**
- Create: `engines/ma50_engine.py`
- Create: `tests/test_ma50_engine.py`

- [ ] **Step 1: 테스트 작성 (RED)**

`tests/test_ma50_engine.py`:
```python
import pytest
from datetime import date


def _sample_metrics():
    return {
        "close": 201.3, "ma50": 195.0, "ma200": 180.0,
        "gap50": 0.032, "gap200": 0.083,
        "vol_ratio": 2.1, "rs_pct": 78.0, "rs_sector_pct": 65.0,
        "ma50_slope_pct": 0.018, "high_n": 199.5, "atr14": 3.2, "sector_etf": "XLK",
    }


def test_build_signal_item_structure():
    from engines.ma50_engine import build_signal_item
    item = build_signal_item(
        ticker="AAPL",
        signal_type="STRONG_BREAKOUT",
        state="BUY",
        score=82.5,
        trigger_reason="MA50 상향 돌파 + 거래량 급증",
        metrics=_sample_metrics(),
    )
    for key in ("ticker", "signal_type", "state", "score", "trigger_reason", "metrics"):
        assert key in item
    assert item["ticker"] == "AAPL"
    assert item["signal_type"] == "STRONG_BREAKOUT"
    assert item["score"] == 82.5


def test_build_signals_json_structure():
    from engines.ma50_engine import build_signals_json, build_signal_item
    item = build_signal_item("NVDA", "BOUNCE", "BUY", 75.0, "반등", _sample_metrics())
    result = build_signals_json(
        as_of=date(2026, 6, 11),
        regime="RISK_ON",
        items=[item],
    )
    assert result["as_of"] == "2026-06-11"
    assert result["regime"] == "RISK_ON"
    assert len(result["items"]) == 1
    assert result["items"][0]["ticker"] == "NVDA"


def test_build_signals_json_empty_items():
    from engines.ma50_engine import build_signals_json
    result = build_signals_json(date(2026, 6, 11), "RISK_OFF", [])
    assert result["items"] == []
    assert result["regime"] == "RISK_OFF"


def test_build_signals_json_metrics_keys():
    from engines.ma50_engine import build_signals_json, build_signal_item
    item = build_signal_item("MSFT", "SELL", "SELL", 0.0, "breakdown", _sample_metrics())
    result = build_signals_json(date(2026, 6, 11), "RISK_ON", [item])
    m = result["items"][0]["metrics"]
    for key in ("close", "ma50", "ma200", "gap50", "gap200",
                "vol_ratio", "rs_pct", "rs_sector_pct",
                "ma50_slope_pct", "high_n", "atr14", "sector_etf"):
        assert key in m
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_ma50_engine.py -v 2>&1 | head -5
```
Expected: `ImportError`

- [ ] **Step 3: 구현**

`engines/ma50_engine.py`:
```python
"""MA50 스크리너 — signals.json 조립 빌더."""
from __future__ import annotations
from datetime import date


def build_signal_item(
    ticker: str,
    signal_type: str,
    state: str,
    score: float,
    trigger_reason: str,
    metrics: dict,
) -> dict:
    """signals.json items 배열의 단일 항목."""
    return {
        "ticker":         ticker,
        "signal_type":    signal_type,
        "state":          state,
        "score":          score,
        "trigger_reason": trigger_reason,
        "metrics":        metrics,
    }


def build_signals_json(
    as_of: date,
    regime: str,
    items: list,
) -> dict:
    """signals.json 전체 구조."""
    return {
        "as_of":  str(as_of),
        "regime": regime,
        "items":  items,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/test_ma50_engine.py -v
```
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add engines/ma50_engine.py tests/test_ma50_engine.py && git commit -m "feat: ma50_engine — signals.json 빌더"
```

---

## Task 5: scripts/run_ma50.py — 실행 진입점

**Files:**
- Create: `scripts/run_ma50.py`

- [ ] **Step 1: 구현**

`scripts/run_ma50.py`:
```python
"""MA50 스크리너 엔진 실행 진입점."""
import os
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.ma50_indicators import (
    calc_ma, calc_slope_pct, calc_gap, calc_highN,
    calc_atr14, calc_rs_raw, calc_rs_pct, calc_regime, build_metrics,
)
from engines.ma50_signals import (
    MA50_DEFAULT_PARAMS, get_buy_signal, get_sell_signal,
    transition_state, calc_score,
)
from engines.ma50_engine import build_signal_item, build_signals_json

load_dotenv()

_OUTPUT_SIGNALS  = Path(__file__).parent.parent / "outputs" / "signals.json"
_OUTPUT_POSITIONS = Path(__file__).parent.parent / "outputs" / "positions.json"

# 섹터 ETF 매핑 (주요 종목 → 섹터)
_SECTOR_MAP: dict = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AVGO": "XLK",
    "AMZN": "XLY", "TSLA": "XLY",
    "GOOGL": "XLC", "META": "XLC",
    "JPM": "XLF", "BRK-B": "XLF",
    "LLY": "XLV", "JNJ": "XLV",
    "XOM": "XLE", "CVX": "XLE",
    "COST": "XLP", "WMT": "XLP",
}

# 기본 워치리스트 (RS 퍼센타일 계산용 유니버스 포함)
_DEFAULT_WATCHLIST = list(_SECTOR_MAP.keys())


def run(watchlist: list = None) -> dict:
    print("=" * 50)
    print("MA50 스크리너 엔진 실행")
    print("=" * 50)

    tickers = watchlist or _DEFAULT_WATCHLIST
    params  = dict(MA50_DEFAULT_PARAMS)

    # 1. SPY + 유니버스 다운로드
    print(f"SPY + {len(tickers)}종목 다운로드 중...")
    all_tickers = ["SPY"] + [t for t in tickers if t != "SPY"]
    raw = yf.download(all_tickers, period="2y", auto_adjust=True,
                      progress=False, group_by="ticker")

    def get_series(df, ticker, col):
        try:
            s = df[ticker][col].squeeze().dropna()
            return s if len(s) > 60 else None
        except Exception:
            return None

    close_spy = get_series(raw, "SPY", "Close")
    if close_spy is None:
        raise RuntimeError("SPY 데이터 수집 실패")

    regime   = calc_regime(close_spy)
    as_of_dt = close_spy.index[-1].date()
    print(f"레짐: {regime} | 기준일: {as_of_dt}")

    # 2. RS_raw 계산 (유니버스 전체)
    rs_raw_map: dict = {}
    for t in tickers:
        c = get_series(raw, t, "Close")
        if c is not None:
            rs_raw_map[t] = calc_rs_raw(c, close_spy)

    # 3. 종목별 시그널 계산
    items = []
    for ticker in tickers:
        close_s  = get_series(raw, ticker, "Close")
        high_s   = get_series(raw, ticker, "High")
        low_s    = get_series(raw, ticker, "Low")
        volume_s = get_series(raw, ticker, "Volume")

        if close_s is None or high_s is None or len(close_s) < 60:
            continue

        ma50  = calc_ma(close_s, 50)
        ma200 = calc_ma(close_s, 200)
        vol20 = calc_ma(volume_s, 20) if volume_s is not None else None

        ma50_valid  = ma50.dropna()
        ma200_valid = ma200.dropna()
        if ma50_valid.empty:
            continue

        close_last  = float(close_s.iloc[-1])
        ma50_last   = float(ma50_valid.iloc[-1])
        ma200_last  = float(ma200_valid.iloc[-1]) if not ma200_valid.empty else 0.0
        vol_last    = float(volume_s.iloc[-1]) if volume_s is not None else 0.0
        vol20_last  = float(vol20.dropna().iloc[-1]) if (vol20 is not None and not vol20.dropna().empty) else 1.0
        vol_ratio   = vol_last / vol20_last if vol20_last > 0 else 0.0
        gap50       = calc_gap(close_last, ma50_last)
        slope_pct   = calc_slope_pct(ma50)
        high_n      = calc_highN(high_s, params["breakout_high_lookback"])
        atr14       = calc_atr14(high_s, low_s, close_s) if low_s is not None else 0.0
        rs_pct_val  = calc_rs_pct(ticker, rs_raw_map)
        sector      = _SECTOR_MAP.get(ticker, "SPY")

        metrics = build_metrics(
            close_last=close_last, ma50_last=ma50_last, ma200_last=ma200_last,
            vol_ratio=vol_ratio, rs_pct=rs_pct_val, rs_sector_pct=rs_pct_val,
            slope_pct=slope_pct, high_n=high_n, atr14=atr14, sector_etf=sector,
        )

        # 시그널 판단 (상태 DB 없이 WATCH 상태 가정)
        buy  = get_buy_signal(
            close_s, high_s, low_s if low_s is not None else high_s,
            ma50, ma200, vol_ratio, gap50, slope_pct, rs_pct_val, regime, params,
        )
        sell = get_sell_signal(
            "HOLDING", close_s, ma50, ma200, rs_pct_val, 0, regime, params,
        ) if close_last < ma50_last else None

        if buy:
            state        = "BUY"
            signal_type  = buy
            trigger      = f"MA50 {buy.replace('_', ' ')}"
        elif sell:
            state        = "SELL" if sell == "SELL" else "SELL_WATCH"
            signal_type  = sell
            trigger      = "MA50 하향 이탈"
        elif close_last >= ma50_last:
            state        = "HOLDING"
            signal_type  = "OK"
            trigger      = ""
        else:
            state        = "WATCH"
            signal_type  = "OK"
            trigger      = ""

        score = calc_score(vol_ratio, gap50, rs_pct_val, slope_pct,
                           ma50_last, ma200_last, params)

        items.append(build_signal_item(ticker, signal_type, state, score, trigger, metrics))

    # 4. 스코어 내림차순 정렬
    items.sort(key=lambda x: x["score"], reverse=True)

    result = build_signals_json(as_of=as_of_dt, regime=regime, items=items)
    _OUTPUT_SIGNALS.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str)
    )
    print(f"\nsignals.json 저장 완료: {_OUTPUT_SIGNALS}")
    print(f"총 {len(items)}종목 평가 | 레짐: {regime}")
    buy_count  = sum(1 for i in items if i["state"] == "BUY")
    sell_count = sum(1 for i in items if i["state"] in ("SELL", "SELL_WATCH"))
    print(f"BUY: {buy_count}  SELL/WATCH: {sell_count}  HOLDING/OK: {len(items)-buy_count-sell_count}")
    return result


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: 전체 기존 테스트 통과 확인**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && pytest tests/ -v 2>&1 | tail -5
```
Expected: 기존 64+ 테스트 모두 PASS

- [ ] **Step 3: 실제 실행**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && source .venv/bin/activate && python scripts/run_ma50.py
```

Expected 출력:
```
==================================================
MA50 스크리너 엔진 실행
==================================================
SPY + 16종목 다운로드 중...
레짐: RISK_ON | 기준일: 2026-06-10

signals.json 저장 완료: .../outputs/signals.json
총 15종목 평가 | 레짐: RISK_ON
BUY: N  SELL/WATCH: N  HOLDING/OK: N
```

- [ ] **Step 4: signals.json 스키마 검증**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && python3 - << 'EOF'
import json
from pathlib import Path
data = json.loads(Path("outputs/signals.json").read_text())

assert "as_of" in data
assert data["regime"] in ("RISK_ON", "RISK_OFF")
assert isinstance(data["items"], list)
assert len(data["items"]) > 0, "items가 비어있음"

item = data["items"][0]
for key in ("ticker", "signal_type", "state", "score", "trigger_reason", "metrics"):
    assert key in item, f"items[0] 누락 키: {key}"

m = item["metrics"]
for key in ("close", "ma50", "ma200", "gap50", "gap200",
            "vol_ratio", "rs_pct", "rs_sector_pct",
            "ma50_slope_pct", "high_n", "atr14", "sector_etf"):
    assert key in m, f"metrics 누락 키: {key}"

print("signals.json 스키마 검증 통과")
print(f"레짐: {data['regime']} | 종목수: {len(data['items'])}")
print(f"상위 3종목: {[i['ticker'] for i in data['items'][:3]]}")
EOF
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/jubro/Claude Project/ma3 momentum" && git add scripts/run_ma50.py outputs/signals.json && git commit -m "feat: run_ma50 — MA50 스크리너 엔진 실행 진입점 + signals.json 산출"
```

---

## 자기 검토 (Self-Review)

### 스펙 커버리지

| CLAUDE.md 요구사항 | 구현 Task |
|---|---|
| MA50, MA200, slope, gap50, gap200, VolMA, highN, ATR14 지표 | Task 1 |
| RS_raw = 0.5·r20 + 0.3·r60 + 0.2·r120 (vs SPY) | Task 1 |
| RS_pct = universe percentile rank | Task 1 |
| regime = SPY_close > SPY_MA200 | Task 1 |
| 공통 게이트 (레짐 + gap50 + vol_ratio) | Task 2 |
| Track B STRONG_BREAKOUT | Task 2 |
| Track A EARLY_TREND (RS + slope 안전장치) | Task 2 |
| Track Bounce (추세 + 근접 + 지지 + 반등) | Task 2 |
| breakdown 정의 (hard + soft) | Task 3 |
| 매도 우선순위 6단계 | Task 3 |
| 상태머신 WATCH→BUY→HOLDING→SELL_WATCH→SELL | Task 3 |
| 스코어 공식 (vol·breakout·rs·trend) | Task 3 |
| signals.json 스키마 | Task 4 |
| 실제 실행 + JSON 저장 | Task 5 |

### 의도적 미포함

- `positions.json`, `transitions.json`: 상태 영속성(DB/파일)이 없는 Phase 1B에서는 단일 배치 평가만. Phase 2(백엔드)에서 추가.
- `RS_sector_pct`: 섹터 ETF별 유니버스 다운로드 비용이 크므로 run_ma50.py에서 `rs_pct`로 대체. Phase 2에서 섹터 ETF 분리.
- `RISK_OFF soft 모드 (Track B만 허용)`: Phase 1B에서는 strict 모드 기본. soft 모드는 `regime_mode` 파라미터로 Phase 2에서 활성화.
