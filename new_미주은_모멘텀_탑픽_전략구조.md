# 미주은 모멘텀 탑픽 전략 — 구현 기준 명세서 (v3, Implementation Spec)

> **문서 성격**: 투자 전략 모니터링/시스템 서비스를 **Claude Code로 구현할 때 직접 참조하는 기준 문서**.
> v2(전략 명세)의 모든 "결정 필요" 항목을 **기본값으로 확정**하고, 데이터 스키마·설정 파일·상태 전이표·알고리즘·수용 기준까지 구현 가능한 수준으로 채웠다.
>
> **확정값 원칙**: 모든 수치는 `config`로 분리된 **기본값(DEFAULT)** 이며 사용자가 override 가능하다. 출처가 불명확한 재량 파라미터는 "합리적 기본값"임을 명시한다.
>
> **태그**: 🔹전략 원칙(미주은 공개 철학 기반) · ⚙️확정 기본값(조정 가능) · 🧪검증/예외.

---

## 0. 목차

1. [전략 철학 및 시스템 목표](#1-전략-철학-및-시스템-목표)
2. [전체 아키텍처](#2-전체-아키텍처)
3. [데이터 모델 (스키마)](#3-데이터-모델-스키마)
4. [설정 파일 (config) — 확정 기본값](#4-설정-파일-config--확정-기본값)
5. [유니버스: 탑픽 선정 엔진](#5-유니버스-탑픽-선정-엔진)
6. [시장 국면(Regime) 엔진](#6-시장-국면regime-엔진)
7. [지표 계산 엔진](#7-지표-계산-엔진)
8. [매수 로직 (3분할 줍줍)](#8-매수-로직-3분할-줍줍)
9. [매도 로직 (리스크 관리)](#9-매도-로직-리스크-관리)
10. [포지션 상태 머신](#10-포지션-상태-머신)
11. [메인 평가 루프 (의사코드)](#11-메인-평가-루프-의사코드)
12. [알림(Alert) 명세](#12-알림alert-명세)
13. [데이터 파이프라인 / 소스](#13-데이터-파이프라인--소스)
14. [예외 처리 규칙](#14-예외-처리-규칙)
15. [백테스팅 하니스](#15-백테스팅-하니스)
16. [수용 기준 (Acceptance Criteria)](#16-수용-기준-acceptance-criteria)
17. [용어집](#17-용어집)

---

## 1. 전략 철학 및 시스템 목표

### 1.1 핵심 원칙 🔹

- **펀더멘털로 선별, 추세로 대응**: 탑픽(우량 성장주)만 유니버스에 두고, 이동평균선·지지선은 *매수/매도 타이밍 대응 도구*로만 쓴다.
- **타이밍 예측 포기, 추세 추종**: 바닥/꼭지를 맞히지 않는다.
- **무한 보유(익절 금지)**: 단순 상승률로 익절하지 않고, 추세가 유지되는 한 비중을 유지한다.
- **감정 배제 / FOMO 통제**: 모든 액션은 사전 정의 트리거에서만 발생한다.
- **리스크 우선**: 매도(방어) 판정을 매수보다 항상 먼저 평가한다.

### 1.2 시스템 목표

이 서비스는 **자동 주문 집행기가 아니라 "규칙 기반 모니터링·알림" 시스템**이다.

- ✅ 사전 정의 규칙으로 트리거를 감지하고 **알림**을 보낸다.
- ✅ 종목별 상태/평단/비중/대기선을 **시각화**한다.
- ⛔ (기본값) 실거래 주문을 자동 집행하지 않는다. (주문 연동은 별도 옵트인 모듈)
- ⛔ 실시간 손익을 과도하게 강조해 감정 개입을 유도하지 않는다.

### 1.3 비목표 (Non-goals)

- 데이 트레이딩/스캘핑, 옵션·레버리지 자동화, 종목 자동 발굴(스크리닝은 보조).

---

## 2. 전체 아키텍처

```
                ┌────────────────────────────┐
   (스케줄러)   │  Data Pipeline (EOD batch)  │  ← 13장
 GitHub Actions │  가격/지표/펀더멘털 수집     │
                └──────────────┬─────────────┘
                               ▼
   ┌──────────┐   ┌────────────────────┐   ┌──────────────┐
   │ Regime    │   │ Indicator Engine    │   │ Universe /   │
   │ Engine(6) │   │ (50MA/200MA/ATR…) 7 │   │ TopPick(5)   │
   └────┬─────┘   └─────────┬──────────┘   └──────┬───────┘
        └──────────┬────────┴───────────────┬─────┘
                   ▼                         ▼
          ┌──────────────────────────────────────┐
          │   Strategy Core (State Machine, 8~11)  │
          │   매수/매도 판정 → 상태 전이 → 액션     │
          └───────────────┬──────────────────────┘
                          ▼
              ┌────────────────────────┐
              │  Alerts(12) + UI/PWA    │
              └────────────────────────┘
```

- **엔진은 일봉(EOD) 기준으로 결정론적**이어야 한다(동일 입력 → 동일 출력). 인트라데이는 보조 트리거.
- 각 엔진은 순수 함수에 가깝게 분리(테스트·백테스트 재사용).

---

## 3. 데이터 모델 (스키마)

TypeScript 인터페이스 형태로 표기(언어 무관, 구현 시 매핑).

```ts
// 일봉 OHLCV
interface Bar {
  date: string;      // ISO 'YYYY-MM-DD'
  open: number; high: number; low: number; close: number;
  volume: number;
  adjClose?: number; // 분할/배당 조정가
}

// 종목 펀더멘털 (탑픽 스코어용)
interface Fundamentals {
  symbol: string;
  revenueGrowthYoY: number;   // %
  fcfMargin: number;          // %
  epsRevisionTrend: -1|0|1;   // 하향/중립/상향
  // 정성 점수 (0~5), 운영자 입력 또는 데이터 매핑
  growthScore: number;        // 2.1 4요소 평균
  moatScore: number;          // 2.2 6요소 평균
  fundamentalsBroken: boolean;// 펀더 훼손 플래그
  updatedAt: string;
}

// 포지션 상태
type PositionStatus =
  | 'WATCH' | 'ENTRY_1' | 'ENTRY_2' | 'ENTRY_3' | 'TRIM' | 'EXIT' | 'REMOVED';

interface Position {
  symbol: string;
  status: PositionStatus;
  avgPrice: number | null;     // 평단 (미보유 시 null)
  weight: number;              // 포트폴리오 내 비중 0~1
  deployedTranches: (1|2|3)[]; // 집행된 분할 단계
  recentHigh: number | null;   // 보유/추적 기간 내 최고가
  trailingStopLine: number | null;
  horizontalSupport: number | null;
  cooldownUntil: string | null;// 재진입 쿨다운 종료일
  lastActionAt: string | null;
}

// 시장 국면
type Regime = 'GREEN' | 'YELLOW' | 'RED';
interface MarketState {
  date: string;
  spx: { close: number; ma50: number; ma200: number };
  ndx: { close: number; ma50: number; ma200: number };
  regime: Regime;
}

// 일별 종목 지표 스냅샷
interface Indicators {
  symbol: string; date: string;
  price: number; ma50: number; ma200: number;
  atr14: number; atrPct: number;        // atr14 / price
  recentHigh: number; horizontalSupport: number | null;
  vol20ma: number;                      // 최근 20일 평균 거래량
  volRatio: number;                     // 당일 거래량 / vol20ma (1.0=평균)
}

// 엔진 출력 액션
type ActionType =
  | 'HOLD' | 'BUY_1' | 'BUY_2' | 'BUY_3' | 'TRIM_HALF' | 'EXIT';
interface Action {
  symbol: string; type: ActionType;
  reason: string; sizePct?: number;     // 투입/축소 비중
  triggeredAt: string;
}
```

---

## 4. 설정 파일 (config) — 확정 기본값 ⚙️

> 아래는 **합리적 기본값**이며 모두 조정 가능. 출처가 불명확한 재량 수치는 그대로 쓰지 말고 백테스트로 검증할 것.

```yaml
strategy:
  # --- 이동평균 정의 ---
  ma:
    method: SMA            # SMA | EMA  (기본 SMA, 일봉 종가 기준)
    short: 50
    long: 200

  # --- 유니버스/탑픽 ---
  universe:
    max_symbols: 15        # 동시 추적 종목 수
    rescore_cadence: quarterly  # 정기 재선정 주기
    toppick_threshold: 70  # 0~100, 이상만 편입
    score_weights:         # 합=1.0
      growth: 0.30
      moat: 0.30
      earnings_momentum: 0.20
      financial_health: 0.20

  # --- 시장 국면 (지수 이동평균 기반, 독립 동작) ---
  regime:
    indices: [SPX, NDX]    # 둘 다 평가
    red_if: any_break      # any_break | all_break (하나라도 200MA 이탈 시 RED)

  # --- 매수: 3분할 줍줍 비중 (합 + reserve = 1.0) ---
  allocation:
    tranche_1: 0.30        # 추세 확인 진입
    tranche_2: 0.40        # 50MA 지지 (최고 확신 구간, 가장 크게)
    tranche_3: 0.20        # 50MA 붕괴 후 수평지지 (역추세, 작게)
    reserve:   0.10        # 극단 패닉 예비
    ma50_support_band: 0.03  # 50MA ±3% 이내를 "지지 부근"으로 판정

  # --- 매도: 트레일링 스탑 (변동성 연동 + 상·하한) ---
  exit:
    trail_mode: hybrid     # fixed | atr | hybrid
    trail_fixed_pct: 0.20  # fixed/hybrid 기본 하락허용
    trail_atr_mult: 5.0    # atr 모드 승수 (trail% = atr_mult * atrPct)
    trail_floor_pct: 0.15  # 하한 (너무 타이트 방지)
    trail_ceiling_pct: 0.30# 상한 (너무 느슨 방지)
    trim_on_first_touch: true  # 1차 터치 시 절반 축소
    exit_needs_fundamental_break: true # 지지선 붕괴 + 펀더 훼손 동시일 때만 전량

  # --- 재진입 ---
  reentry:
    cooldown_days: 5       # EXIT 후 재진입 금지 거래일
    require_fresh_tranche1: true

  # --- 어닝/이벤트 ---
  earnings:
    policy: hold_through   # hold_through | reduce_before (기본: 무한보유 철학)
    warn_within_days: 5    # 발표 임박 경고

  # --- 실행 모드 ---
  execution:
    mode: alert_only       # alert_only | semi_auto | auto (기본 알림만)
    bar: daily             # daily | intraday (엔진 기준봉)
```

### 4.1 기본값 근거 (설계 메모)

- **tranche 2를 가장 크게(0.40)**: 50MA 지지는 추세 유지 중 고확신 구간 → 공격적 매수. 50MA 붕괴(3차)는 역추세라 작게(0.20).
- **reserve 0.10**: 시장 전체가 패닉에 빠진 극단적 급락 구간에서의 마지막 카드.
- **trail = hybrid**: 변동성 큰 성장주에 고정 -20%는 종목별로 과도/과소할 수 있어 ATR 연동하되 15~30%로 clamp.
- **earnings = hold_through**: "익절·예측 금지" 철학과 일치. 단, 발표 임박은 경고만.

### 4.2 설정 탭(Settings) — 사용자 노출 옵션 ⚙️

> 위 config 기본값은 **앱의 설정 탭에서 사용자가 선택지 안에서 직접 고르도록** 노출한다. 사용자는 자유 입력이 아니라 **검증된 선택지(preset) 중 선택**하는 것을 기본으로 한다(잘못된 값으로 인한 전략 붕괴 방지). 고급 사용자에게만 "직접 입력"을 옵션으로 연다.
>
> 각 항목은 `→ config 키`로 매핑된다. **굵게** 표시된 것이 기본 선택값.

**A. 줍줍(분할 매수) 설정**

| 설정 항목 | 선택지 | → config |
| :--- | :--- | :--- |
| 분할 투입 비중 방식 | **점증형(1차30·2차40·3차20·예비10)** / 지지집중형(25·50·15·10) / 균등형(30·30·30·10) / 직접입력 | `allocation.*` |
| 50일선 지지 인정 범위 | ±2% / **±3%** / ±5% | `allocation.ma50_support_band` |

**B. 매도 설정 (고점 대비 하락 · 트레일링 스탑)**

| 설정 항목 | 선택지 | → config |
| :--- | :--- | :--- |
| 하락 허용 방식 | 고정 비율 / 변동성 연동(ATR) / **혼합** | `exit.trail_mode` |
| 고정 하락 허용폭 | -15% / **-20%** / -25% / -30% | `exit.trail_fixed_pct` |
| 변동성 연동 민감도 | 보수(×4) / **표준(×5)** / 공격(×7) | `exit.trail_atr_mult` |
| 첫 매도 신호 시 | **절반 축소 후 관망** / 전량 매도 | `exit.trim_on_first_touch` |
| 추세 이탈(지지선 붕괴) 매도 | **펀더 훼손 동반 시에만 전량** / 붕괴 즉시 전량 | `exit.exit_needs_fundamental_break` |

**C. 탑픽(종목 선정) 설정**

| 설정 항목 | 선택지 | → config |
| :--- | :--- | :--- |
| 탑픽 편입 점수 기준 | **70점** / 75점 / 80점 | `universe.toppick_threshold` |
| 재선정 주기 | 매월 / **분기** / 반기 | `universe.rescore_cadence` |
| 동시 추적 종목 수 | 10 / **15** / 20 | `universe.max_symbols` |

**D. 시장 국면 설정**

| 설정 항목 | 선택지 | → config |
| :--- | :--- | :--- |
| 국면 판정 지수 | S&P500만 / 나스닥100만 / **둘 다** | `regime.indices` |
| 위험(RED) 전환 기준 | **한 지수라도 200일선 이탈** / 모든 지수 이탈 | `regime.red_if` |
| 위험 구간 신규 매수 | **차단** / 경고 후 수동 허용 | (3차 수동 허용 플래그) |

**E. 이동평균 · 지표 설정**

| 설정 항목 | 선택지 | → config |
| :--- | :--- | :--- |
| 이동평균 방식 | **단순(SMA)** / 지수(EMA) | `ma.method` |
| 수평 지지선 | **자동 검출** / 수동 입력 | (7장 검출/override) |

**F. 실적 · 이벤트 설정**

| 설정 항목 | 선택지 | → config |
| :--- | :--- | :--- |
| 실적 발표 대응 | **그대로 보유(무한 보유)** / 발표 전 일부 축소 | `earnings.policy` |
| 실적 임박 경고 | 3일 전 / **5일 전** / 끄기 | `earnings.warn_within_days` |

**G. 실행 모드**

| 설정 항목 | 선택지 | → config |
| :--- | :--- | :--- |
| 실행 모드 | **알림만** / 반자동 / 자동 | `execution.mode` |

> 🧪 **설정 검증 규칙**: ① 분할 비중 + 예비 = 100%가 아니면 저장 차단, ② 하락 허용 하한 < 상한, ③ 직접 입력은 허용 범위(예: 하락폭 10~40%) 밖이면 경고. 설정 변경은 **다음 평가 주기부터 적용**하고, 이미 보유 중인 포지션의 기준선(평단·트레일링 기준)은 소급 변경하지 않는다.

---

## 5. 유니버스: 탑픽 선정 엔진

### 5.1 선정 기준 🔹

**(A) 시장 지배력·성장성 — 4요소**

| 요소 | 점검 |
| :--- | :--- |
| TAM | 잠재 시장이 크고 확장 중인가 |
| 침투율 | 초기 단계일수록 가점 |
| 점유율 | 1위 또는 압도적 격차 |
| 성장률 | 매출·FCF·순이익 추세적 우상향 |

**(B) 경제적 해자 — 6요소**: 규모의 경제 · 네트워크 효과 · 브랜드 · 전환비용 · 무형자산 · 데이터 우위.

**(C) 재무·이익 모멘텀 보조**: 매출 성장률, FCF 마진, EPS 추정치 방향, 부채 구조.

### 5.2 스코어링 (0~100)

```
TopPickScore =
    100 * ( w_growth   * norm(growthScore)
          + w_moat     * norm(moatScore)
          + w_earn     * norm(earningsMomentum)   // EPS revision 등
          + w_finance  * norm(financialHealth) )

norm(x) = x / 5          // 0~5 입력을 0~1로
편입: TopPickScore >= toppick_threshold (기본 70)
```

### 5.3 운영 규칙 🧪

- 정기 재선정: `rescore_cadence`(기본 분기).
- **이벤트 강등**: `fundamentalsBroken == true`면 즉시 `REMOVED` 후보, 보유 시 매도 로직과 연계(9.2).
- 신규 편입 종목은 `WATCH`로 시작.

---

## 6. 시장 국면(Regime) 엔진 🔸+⚙️

> 미주은이 강조하는 "연준·경제지표·시장 흐름 읽기"를 시스템화한 상위 레이어. 개별 종목 로직만으로는 시스템 리스크(전체 시장 급락)에 무방비이므로, **지수의 장기 추세(200MA)·중기 추세(50MA)로 시장 국면을 판정**해 신규 진입을 통제한다.
>
> ⚠️ 이 국면 필터는 미주은이 공식 수치로 공개한 규칙이 아니라, "시장 흐름을 보고 대응하라"는 원칙을 구현용으로 구체화한 **보완(🔸)** 이다. 본 전략은 독립적으로 동작하며 다른 외부 시스템에 의존하지 않는다.

### 6.1 판정 규칙

```
GREEN  : (SPX.close > SPX.ma200) AND (NDX.close > NDX.ma200)
         AND (지수 50MA 정배열: ma50 > ma200)
RED    : (red_if == any_break  AND 어느 지수든 close < ma200)
         OR (red_if == all_break  AND 모든 지수 close < ma200)
YELLOW : 그 외 (50MA 아래지만 200MA 위 등 중립 구간)
```

### 6.2 국면별 행동

| 국면 | 신규 매수 | 보유 | 비고 |
| :--- | :--- | :--- | :--- |
| 🟢 GREEN | 허용 | 유지 | 정상 운용 |
| 🟡 YELLOW | 1차 진입 보수적(허용하되 경고) | 유지 | 변동성 주의 |
| 🔴 RED | **차단** | 개별 매도 규칙만 적용 | 지수 200MA 이탈 |

- RED라도 **기존 포지션의 3차 줍줍**은 펀더 확신(5.2 통과) + 수평지지 근접 시 *수동 확인 옵션*으로만 허용(기본 자동 차단).

---

## 7. 지표 계산 엔진

```
ma50  = SMA(close, 50)            // config.ma.method
ma200 = SMA(close, 200)
atr14 = ATR(high, low, close, 14) // Wilder
atrPct = atr14 / close

recentHigh = max(high) over 추적기간(진입 후 누적, 신고가 시 갱신)

// 수평 지지선 자동 검출 (스윙 저점/고점 피벗)
horizontalSupport = detectPivotSupport(bars, lookback=20, strength=3)
  // strength=양옆 3봉보다 낮은 국소 저점 → 직전 유의미 지지
  // 운영자 수동 override 필드 우선

// 거래량 지표
vol20ma  = SMA(volume, 20)        // 최근 20일 평균 거래량
volRatio = volume[today] / vol20ma // 1.0=평균, 1.3=+30%, 1.5=+50%
```

### 7.2 거래량 해석 규칙 ⚙️

거래량은 주가 움직임의 진위를 판별하는 보조 지표다. 단독 트리거가 아니라 **다른 조건의 신뢰도를 높이거나 낮추는 필터**로 쓴다.

| 상황 | volRatio | 해석 | 대응 |
| :--- | :--- | :--- | :--- |
| 가격 상승·돌파 | ≥ 1.30 | 기관 유입 — 진짜 신호 | ENTRY_1 정상 진행 |
| 가격 상승·돌파 | < 1.30 | 거래량 미확인 — 약한 신호 | ENTRY_1 보류, 경고 알림 |
| 가격 하락·횡보 | < 1.00 | 수익실현 물량 소화 — 정상 | 알림 없음 |
| 가격 하락·횡보 | ≥ 1.50 | 매도압력 급증 — 기관 이탈 의심 | ⚠️ 경보 알림 |

### 7.3 트레일링 스탑 라인 계산 ⚙️

```
trailPct =
  fixed  : trail_fixed_pct
  atr    : clamp(trail_atr_mult * atrPct, trail_floor_pct, trail_ceiling_pct)
  hybrid : clamp(max(trail_fixed_pct, trail_atr_mult * atrPct),
                 trail_floor_pct, trail_ceiling_pct)

trailingStopLine = recentHigh * (1 - trailPct)   // recentHigh 갱신 시 자동 상향
```

---

## 8. 매수 로직 (3분할 줍줍) 🔹

| 단계 | 조건 | 액션 | 투입 |
| :--- | :--- | :--- | :--- |
| **1차** | (저항 돌파 또는 상승 모멘텀) AND `price >= ma50` AND `volRatio >= 1.30` | ENTRY_1 진입 | `tranche_1` |
| **2차** | 보유 중 조정으로 `\|price - ma50\| / ma50 <= ma50_support_band` (50MA 부근) | ENTRY_2 비중확대 | `tranche_2` |
| **3차** | `price < ma50` (붕괴) AND `near(price, horizontalSupport)` AND `TopPickScore >= threshold` | ENTRY_3 비중확대 | `tranche_3` |

- 모든 매수는 `regime != RED`에서만(8장 기본). 1차는 YELLOW에서 경고 동반 허용.
- **1차 거래량 조건**: `volRatio < 1.30`이면 ENTRY_1 보류. "거래량 미확인 돌파 — 관망" 알림 발송 후 다음 봉에서 재평가.
- 2차·3차는 거래량 조건 없음(조정 중 물량 감소가 정상이므로).
- 동일 단계는 1회만 집행(`deployedTranches`로 중복 방지).

---

## 9. 매도 로직 (리스크 관리) 🔹

> **매도는 매수보다 먼저 평가한다.**

### 9.1 트레일링 스탑

```
if price <= trailingStopLine:
    if trim_on_first_touch and status != TRIM:
        → TRIM_HALF (비중 절반 축소, status=TRIM)
    else:
        → EXIT (잔여 청산)
```

### 9.2 추세의 완전한 이탈

```
if status in {ENTRY_2, ENTRY_3} and price < horizontalSupport:
    if exit_needs_fundamental_break:
        if fundamentalsBroken: → EXIT (전량) + REMOVED 후보
        else:                  → TRIM_HALF (방어적 축소)
    else:
        → EXIT
```

### 9.3 매도 후 처리

- `EXIT` → `cooldownUntil = date + cooldown_days`, 포지션 리셋(평단/recentHigh/트랜치 초기화).
- 펀더 훼손 동반 시 → `REMOVED`(유니버스에서 제외, 재선정 시 재평가).

---

## 10. 포지션 상태 머신

### 10.1 전이표

| 현재 | 이벤트 | 다음 | 액션 |
| :--- | :--- | :--- | :--- |
| WATCH | 1차 조건 충족 & regime≠RED | ENTRY_1 | BUY_1 |
| ENTRY_1 | 50MA 부근 조정 | ENTRY_2 | BUY_2 |
| ENTRY_1/2 | 신고가 경신 | (유지) | recentHigh·stop 상향 |
| ENTRY_2 | 50MA 붕괴 & 수평지지 근접 & score≥th | ENTRY_3 | BUY_3 |
| ENTRY_1/2/3 | 트레일링 스탑 1차 터치 | TRIM | TRIM_HALF |
| TRIM | 추가 하락(스탑 재터치/지지붕괴) | EXIT | EXIT |
| ENTRY_2/3 | 수평지지 붕괴 + 펀더훼손 | EXIT(→REMOVED) | EXIT |
| EXIT | 쿨다운 경과 & 1차 재조건 | ENTRY_1 | BUY_1 |
| any | fundamentalsBroken | REMOVED | (보유시 EXIT 후) |

### 10.2 불변식 (Invariants) 🧪

- `deployedTranches`는 단조 증가(같은 단계 재집행 금지).
- `trailingStopLine`은 절대 하향되지 않음(recentHigh 비감소).
- 보유 중이면 `avgPrice != null` 이고 `weight > 0`.

---

## 11. 메인 평가 루프 (의사코드)

```python
def evaluate(symbol, ind, pos, market, cfg) -> Action:
    price = ind.price

    # --- 0. 펀더 훼손 최우선 ---
    if symbol.fundamentalsBroken and pos.status not in {WATCH, EXIT, REMOVED}:
        return Action(symbol, EXIT, "fundamentals_broken")

    # --- 1. 신고가 → recentHigh/stop 갱신 ---
    if pos.recentHigh is None or price > pos.recentHigh:
        pos.recentHigh = price
    pos.trailingStopLine = pos.recentHigh * (1 - trail_pct(ind, cfg))

    # --- 2. 매도(리스크) 먼저 ---
    if pos.status in {ENTRY_1, ENTRY_2, ENTRY_3, TRIM}:
        if price <= pos.trailingStopLine:
            if cfg.trim_on_first_touch and pos.status != TRIM:
                return Action(symbol, TRIM_HALF, "trailing_stop_touch")
            return Action(symbol, EXIT, "trailing_stop_exit")

        if pos.status in {ENTRY_2, ENTRY_3} and pos.horizontalSupport \
           and price < pos.horizontalSupport:
            if cfg.exit_needs_fundamental_break and not symbol.fundamentalsBroken:
                return Action(symbol, TRIM_HALF, "support_break_defensive")
            return Action(symbol, EXIT, "trend_break")

    # --- 2.5. 거래량 경보 (매도 판단 보조, 액션 아님) ---
    if pos.status in {ENTRY_1, ENTRY_2, ENTRY_3, TRIM}:
        price_falling_or_flat = price <= prev_close * 1.005   # 보합 이하
        if price_falling_or_flat and ind.volRatio >= 1.50:
            emit_alert(symbol, "VOL_SPIKE_WARNING", "매도압력 급증 — 기관 이탈 의심")

    # --- 3. 매수 (국면 게이트) ---
    regime = market.regime
    if regime != RED or (regime == RED and cfg.allow_manual_t3):  # 기본 False
        ma50 = ind.ma50
        if pos.status == WATCH and not in_cooldown(pos, market.date):
            if breakout_or_above_ma50(price, ma50) and regime in {GREEN, YELLOW}:
                if ind.volRatio >= cfg.vol_breakout_min:          # 기본 1.30
                    return Action(symbol, BUY_1, "trend_entry", cfg.tranche_1)
                else:
                    emit_alert(symbol, "VOL_UNCONFIRMED", "거래량 미확인 돌파 — 관망")

        if pos.status == ENTRY_1 and within_band(price, ma50, cfg.ma50_support_band):
            return Action(symbol, BUY_2, "ma50_support", cfg.tranche_2)

        if pos.status == ENTRY_2 and price < ma50 \
           and near(price, pos.horizontalSupport) \
           and toppick_score(symbol) >= cfg.toppick_threshold:
            return Action(symbol, BUY_3, "horizontal_support", cfg.tranche_3)

    return Action(symbol, HOLD, "no_trigger")
```

**평가 순서 보장**: 펀더 훼손 → 스탑/추세붕괴 → 매수. 이 순서를 바꾸지 말 것.

---

## 12. 알림(Alert) 명세

| 알림 | 트리거 | 우선순위 | 문구 예시 |
| :--- | :--- | :--- | :--- |
| 🔴 매도(스탑) | `TRIM_HALF`/`EXIT`(stop) | 최상 | "{종목} 트레일링 스탑 도달 — 절반 축소 검토" |
| 🔴 추세 이탈 | 수평지지 붕괴 | 최상 | "{종목} 지지선 붕괴 — 추세 점검" |
| ⚠️ 거래량 경보 | 하락·횡보 중 `volRatio ≥ 1.50` | 상 | "{종목} 매도압력 급증(거래량 +{%}) — 기관 이탈 의심" |
| 🟢 2차 매수 | 50MA 지지 | 상 | "{종목} 50MA 지지 — 2차 줍줍 구간" |
| 🟢 1차 매수 | 추세 진입 + 거래량 확인 | 중 | "{종목} 50MA 안착·거래량 확인 — 1차 진입 후보" |
| ℹ️ 거래량 미확인 돌파 | ENTRY_1 조건 중 `volRatio < 1.30` | 중 | "{종목} 돌파했으나 거래량 미확인(×{ratio}) — 관망" |
| 🟡 3차 매수 | 수평지지 근접(펀더 OK) | 중 | "{종목} 수평지지 근접 — 3차 검토(역추세 주의)" |
| ⚠️ 국면 전환 | regime 변경 | 상 | "시장 국면 {RED} — 신규 매수 차단" |
| ⚠️ 어닝 임박 | `warn_within_days` 이내 | 중 | "{종목} 실적 발표 {D-n}" |

- **중복 억제**: 동일 종목·동일 트리거는 1봉당 1회.
- **국면 RED 시** 매수 알림은 정보성으로만 표시(액션 비활성).
- **거래량 경보**는 매도 액션을 강제하지 않음 — 관찰·주의 신호로만 표시.

---

## 13. 데이터 파이프라인 / 소스

- **기준봉**: 일봉(EOD). 엔진은 EOD 배치로 결정론적 평가(권장: 미 장마감 후 스케줄).
- **스케줄러**: GitHub Actions cron(또는 동급). 산출물(지표/신호/상태)을 저장소(KV/JSON/DB)에 적재.
- **소스 어댑터**: 특정 벤더에 종속되지 않도록 `PriceProvider` 인터페이스로 추상화.
  ```ts
  interface PriceProvider {
    getDailyBars(symbol: string, lookback: number): Promise<Bar[]>;
    getQuote(symbol: string): Promise<number>;        // 인트라데이(옵션)
  }
  ```
- **펀더멘털**: 분기 갱신. 운영자 입력 + 외부 데이터 매핑 혼합 허용.
- **분할/배당 조정**: `adjClose` 사용 또는 조정계수 반영(14.4).

> 🧪 데이터 신뢰성: 결측/지연 시 해당 봉 평가를 보류(stale 플래그)하고 알림하지 말 것(거짓 신호 방지).

---

## 14. 예외 처리 규칙 🧪

1. **슬리피지**: 트리거 가격과 체결 가정 가격 사이 보정 파라미터(`slippage_bps`) 제공. 알림은 트리거 기준, 백테스트 체결은 보정가 기준.
2. **갭(Gap)**: 시초가가 스탑선 아래로 갭다운 시, 체결 가정가 = 시초가(스탑선 통과로 간주). 갭업 시 추격 매수 금지.
3. **데이터 결측/지연**: 해당 봉 평가 보류, `stale=true`. 신호 생성 금지.
4. **분할/배당락**: `recentHigh`, 이평선, 평단을 조정계수로 재계산.
5. **거래정지/상장폐지**: 즉시 `REMOVED`, 알림.
6. **유동성 부족(저거래량)**: 옵션 필터로 진입 제한.
7. **휩쏘(whipsaw)**: 쿨다운 + 단계적 매도(TRIM→EXIT)로 완화.

---

## 15. 백테스팅 하니스

- **룩어헤드 금지**: t일 신호는 t일 종가까지의 정보만 사용. 지지선/국면 판정에 미래 봉 유입 금지.
- **결정론**: 동일 데이터·config → 동일 결과(시드 고정, 부동소수 비교 허용오차 정의).
- **체결 모델**: 신호는 종가, 체결은 익일 시가(또는 종가) + 슬리피지 — 모드 선택 가능.
- **비용**: 수수료·세금·슬리피지 반영 토글.
- **지표(report)**: CAGR, MDD, 승률, 평균 보유기간, 트랜치별 기여도, 트레일링 스탑 발동 횟수.
- **검증 데이터셋**: 최소 1회 이상 큰 조정(예: 2020·2022·2025 변동성 구간) 포함.

---

## 16. 수용 기준 (Acceptance Criteria) 🧪

구현이 "완료"로 간주되려면:

- [ ] 동일 일봉 입력에 대해 엔진 출력이 **결정론적**이다.
- [ ] `volRatio < 1.30`일 때 ENTRY_1 액션이 **생성되지 않는다**.
- [ ] 하락·횡보 중 `volRatio ≥ 1.50`이면 거래량 경보 알림이 **발송된다**(매도 액션은 발생하지 않음).
- [ ] 매도 판정이 매수보다 **항상 먼저** 평가된다(단위 테스트로 보장).
- [ ] `trailingStopLine`이 어떤 경우에도 **하향되지 않는다**.
- [ ] `deployedTranches`가 단조 증가하며 동일 단계 **중복 집행 없음**.
- [ ] regime == RED에서 신규 BUY 액션이 **생성되지 않는다**(수동 옵션 off 기준).
- [ ] EXIT 후 `cooldown_days` 내 재진입이 **차단**된다.
- [ ] 펀더 훼손(`fundamentalsBroken`)이 다른 모든 매수 신호를 **무력화**한다.
- [ ] 갭다운으로 스탑선을 건너뛴 경우 EXIT가 **누락되지 않는다**.
- [ ] 모든 config 기본값이 외부 파일로 분리되어 **override 가능**하다.
- [ ] 백테스트가 룩어헤드 없이 동작하고 위 지표 리포트를 출력한다.

---

## 17. 용어집

> "미주은 확정" = 미주은 공개 도서·채널에서 일관되게 쓰임이 확인된 용어. "일반/보완" = 구현을 위해 채택한 일반 투자 용어(미주은 고유 표현이 따로 있을 수 있으며, 확인되면 교체 권장).

| 용어 | 정의 | 출처 |
| :--- | :--- | :--- |
| 탑픽(Top Pick) | 펀더멘털 기준을 통과해 유니버스에 편입된 우량 성장주 | 미주은 확정 |
| 줍줍 | 조정/하락 시 분할 매수로 비중을 확대하는 행위 | 미주은 확정 |
| 경제적 해자 | 경쟁사 대비 지속 가능한 우위(안전마진) | 미주은 확정 |
| 무한 보유 | 추세 유지 시 단순 상승률로 익절하지 않는 원칙 | 미주은 확정 |
| 50일선 / 200일선 | 50일 / 200일 이동평균선 | 일반 |
| 트레일링 스탑(고점 대비 하락 매도) | 최고가 대비 일정 하락 시 매도, 신고가마다 기준선 상향 | 일반/보완 |
| 수평 지지선 | 직전 파동의 유의미한 고점/저점 가격대 | 일반/보완 |
| 국면(Regime) | 시장 전체 추세 상태(GREEN/YELLOW/RED) | 보완 |

---

## 부록. 출처·한계

- 본 명세는 미주은(최철)의 공개 도서·유튜브에서 일관되게 드러나는 **투자 철학·원칙**(펀더멘털 선별 + 추세 추종, 무한 보유, FOMO 통제, 50MA 기반 대응, 트레일링 스탑)을 기준으로 재구성했다.
- ⚙️로 표기된 **구체 수치**(트레일링 %, 분할 비율, 임계값 등)는 미주은이 재량 운용하는 영역으로 공개 자료만으로 단일 정답을 특정할 수 없어, **합리적 기본값**으로 확정하고 config로 분리했다. 실제 운용·백테스트로 반드시 재검증할 것.
- 본 문서는 개인 백테스팅·모니터링 시스템 설계 자료이며 투자 자문·수익 보장이 아니다. 매매 판단과 책임은 사용자에게 있다.
