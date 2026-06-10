# Phase 0 데이터 PoC 설계

**날짜:** 2026-06-10  
**범위:** ma3 momentum — Phase 0 (데이터 검증 스크립트)  
**목적:** 서비스 구현 전 무료 데이터 소스의 실재성·정확성을 검증하고, Phase 1 엔진 구현의 전제 조건을 확인한다.

---

## 1. 파일 구조

```
ma3 momentum/
├── scripts/
│   └── phase0_poc.py       ← 검증 스크립트 (이번 Phase 산출물)
├── .env                    ← FRED_API_KEY (git 제외)
├── .env.example            ← 키 없는 템플릿 (git 포함)
├── .gitignore
├── requirements.txt
└── docs/
    └── superpowers/specs/
        └── 2026-06-10-phase0-data-poc-design.md
```

---

## 2. 의존성

```
yfinance>=0.2
fredapi>=0.5
pandas>=2.0
numpy>=1.26
python-dotenv>=1.0
```

---

## 3. 검증 항목 (6개 독립 함수)

각 함수는 독립 실행. 하나가 실패해도 나머지는 계속 진행. 결과는 `PASS / WARN / FAIL` 중 하나.

### 3-1. `check_masam()` — ^IXIC 마삼 감지

**소스:** yfinance `^IXIC`  
**기간:** 최근 2년 (롤링 max용 충분한 기간)

```
1. ^IXIC 일별 종가 다운로드
2. 일별 등락률 = (close[i] - close[i-1]) / close[i-1]
3. 마삼 날짜 = 등락률 ≤ -3.0% 인 날
4. 최근 마삼: 마삼 날짜 중 가장 최근
5. 이번 달 마삼 횟수: 현재 달력 월 내 마삼 날짜 수 (월 독립 집계, 롤링 아님)
6. 전년도 역년 수익률: 전년 12/31 종가 vs 전년 1/1 이후 첫 거래일 종가
7. 전고점 대비 하락률: rolling max(전체) vs 현재 종가
```

**공황 카운트 규칙 (중요):**
- 같은 달력 월 내 마삼 4회↑ = PANIC 트리거
- 3월 3회 + 4월 1회 = 공황 아님 (월별 독립)
- 전년 역년 +45% AND 마삼 4회↑ = PANIC_EMERGENCY

**예상 출력:**
```
[PASS] ^IXIC 마삼 감지
       최근 마삼: 2026-06-05 (-4.18%)
       이번 달(6월) 마삼: 1회 (공황 기준 4회까지 여유)
       전년(2025) 역년 수익률: +XX.X%
       전고점 대비: -X.X% (전고점: 2026-XX-XX XXXXX.XX)
```

---

### 3-2. `check_rate_env()` — 금리환경 판단

**소스:** FRED `DFF` (연방기금금리 실효치)

```
1. FRED DFF 최근값 조회
2. DFF ≤ 0.25% → ZERO_RATE
   DFF > 0.25% → NON_ZERO_RATE
```

**예상 출력:**
```
[PASS] 금리환경
       DFF: 4.50% → NON_ZERO_RATE
       마지막 갱신: 2026-06-09
```

---

### 3-3. `check_drawdown()` — 전고점 대비 하락

**소스:** yfinance `^IXIC` (check_masam과 데이터 공유)

```
1. rolling max(close) over 전체 기간
2. 현재 종가 / rolling max - 1 = 하락률
3. 전고점 날짜 = rolling max가 가장 최근에 달성된 날
```

**예상 출력:**
```
[PASS] 전고점 대비 하락
       전고점: 2026-XX-XX XXXXX.XX
       현재(2026-06-09): 25,678.82
       하락률: -X.X%
```

---

### 3-4. `check_qe()` — WALCL QE 자동감지

**소스:** FRED `WALCL` (연준 총자산)

```
1. WALCL 주간 데이터 최근 8주 조회
2. 4주 이동평균 기울기 계산
3. 기울기 > 0 → QE_ON
   기울기 < 0 → QE_OFF
   |기울기| < 임계값(0.1%) → WARN (모호 구간 → 수동 확인 알림)
```

**예상 출력:**
```
[PASS] WALCL QE 자동감지
       4주 MA 기울기: -0.3% → QE_OFF
       마지막 갱신: 2026-06-05
```

---

### 3-5. `check_rs_percentile()` — MA50 RS percentile

**소스:** yfinance (샘플 30종목 + SPY)

```
샘플 종목: S&P500·NDX 대표 30종목 (AAPL, MSFT, NVDA, AMZN, GOOGL, META,
           TSLA, AVGO, COST, ORCL, AMD, NFLX, ADBE, QCOM, TXN,
           AMAT, INTC, MU, LRCX, KLAC, PANW, CRWD, SNPS, CDNS,
           MELI, ASML, ARM, SMCI, PLTR, COIN)

1. 각 종목 + SPY 최근 180일 일별 종가 다운로드
2. r20 = 20일 수익률, r60 = 60일, r120 = 120일 (vs SPY 대비)
3. RS_raw = 0.5·r20 + 0.3·r60 + 0.2·r120
4. RS_pct = 샘플 내 RS_raw의 percentile rank (0~100)
5. 상위 3개 종목 출력으로 로직 검증
```

> PoC 목적: 계산 로직 검증. 실제 서비스에서는 S&P500+NDX 전체(~580종목) 롤링 캐시 사용 (Phase 1).

**예상 출력:**
```
[PASS] MA50 RS percentile (샘플 30종목)
       NVDA: RS_raw=+0.142 → RS_pct=93
       AAPL: RS_raw=+0.031 → RS_pct=57
       INTC: RS_raw=-0.089 → RS_pct=10
       처리시간: XX.Xs
```

---

### 3-6. `check_pmi_source()` — PMI 소스 탐색

**소스:** FRED `NAPM` (ISM 제조업) 시도

```
1. FRED NAPM 최근 데이터 조회
2. 마지막 갱신일이 현재 기준 3개월 이내 → PASS
3. 3개월 초과 or 조회 실패 → WARN (수동입력 폴백 권장)
```

**예상 출력:**
```
[WARN] PMI 소스
       FRED NAPM 마지막 갱신: XXXX-XX-XX
       → 3개월 초과 or 조회 실패: 수동입력 폴백 권장
```

---

## 4. 실행 방법

```bash
# 환경 설정
cd "ma3 momentum"
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# .env 설정
cp .env.example .env
# .env에 FRED_API_KEY=cb6fb... 입력

# 실행
python scripts/phase0_poc.py
```

---

## 5. 성공 기준

| 항목 | 성공 기준 |
|---|---|
| ^IXIC 마삼 감지 | 실제 -3% 이하 날짜와 일치, 월별 독립 카운트 정상 |
| 금리환경 | DFF 최신값 조회 성공 |
| 전고점 | 현재 종가보다 높거나 같은 값 (전고점 ≤ 현재가면 오류) |
| WALCL QE | 데이터 조회 성공, 기울기 정상 계산 |
| RS percentile | 30종목 중 순위가 직관적으로 타당 (NVDA > INTC 등) |
| PMI | PASS면 자동화 유지 / WARN이면 수동입력 구조 확정 |

**PASS 5 + WARN 1(PMI)** 이상이면 Phase 1 진입 가능.

---

## 6. Phase 1 연결

Phase 0에서 검증된 각 함수는 Phase 1 엔진 모듈의 뼈대가 된다:
- `check_masam()` → `engines/masam_engine.py`
- `check_rate_env()` + `check_qe()` → `engines/market_context.py`
- `check_rs_percentile()` → `engines/ma50_engine.py`
