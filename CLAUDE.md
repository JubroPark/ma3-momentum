# CLAUDE.md — 통합 투자 전략 모바일 서비스 (ma3 momentum)

> 이 파일은 Claude가 본 프로젝트 작업 시 반드시 숙지해야 할 컨텍스트, 설계 결정, 구현 규칙을 담고 있다.
> 설계 원본: `통합_전략_서비스_설계안_v3.md`, `나스닥_마삼_매뉴얼_A/B.md`, `모멘텀_스크리너.md`, `ux-ui_mockup.html`

---

## 프로젝트 한 줄 요약

하나의 PWA에서 **마삼 대응**(나스닥 -3% 룰북 기반 국면 모니터)과 **MA50 스크리너**(50일 이평선 기반 종목 스크리닝) 두 전략을 상단 토글로 전환해 사용하는 모바일 투자 보조 서비스.
데이터·인프라(공통 코어)는 공유, 전략별 엔진·화면은 분리. **전면 무료 스택**. ⚠️ 투자 권유 아님, 스크리닝·의사결정 보조 도구.

---

## 1. 기술 스택 (확정)

| 영역 | 기술 |
|---|---|
| 프레임워크 | Next.js 14+ App Router · TypeScript · Tailwind CSS |
| 차트 | lightweight-charts (통일) |
| 배포 | Vercel Hobby (무료) |
| 배치 | GitHub Actions cron (매일 18:00 ET) |
| 알림 | Web Push / VAPID (무료) |
| 저장 | repo JSON + Gist (공개 신호) / Supabase·Upstash free (사용자별) |
| 데이터 수집 | yfinance + Stooq (무료) / FRED API |
| 폰트 | Pretendard |

**PWA 렌더링 원칙**: 서버 API 없음 — 정적 JSON을 fetch해 렌더. 서버 비용 0.

---

## 2. 전체 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                   PWA App Shell                      │
│   상단 세그먼트: [ 마삼 대응 ] [ MA50 스크리너 ]      │
│   (선택 상태 영구 저장 · 알림 센터 공유)              │
└───────────────┬──────────────────┬──────────────────┘
                │                  │
        ┌───────▼──────┐    ┌──────▼────────┐
        │  마삼 엔진     │    │  MA50 엔진     │
        │ (룰북 상태머신)│    │ (2트랙/3-state)│
        └───────┬──────┘    └──────┬────────┘
                │                  │
        ┌───────▼──────────────────▼────────┐
        │          공통 코어 (Shared Core)    │
        │  데이터 수집 · 지표 · 저장 · 알림    │
        │  GitHub Actions cron (1일 1배치)    │
        └────────────────────────────────────┘
```

- 하루 1번 cron이 두 엔진을 모두 평가 → 각자 JSON 산출물 생성
- PWA는 정적 JSON을 fetch해 렌더
- **두 전략은 완전 독립** — 자본·신호 비연동. 마삼 PANIC(현금화) 중에도 MA50 매수 신호는 그대로 산출되며, 두 전략 간 자본 배분은 사용자 판단 (엔진 간 가드 없음).

---

## 3. 데이터 수집 규칙

### 수집 대상 (무료 소스)

| 데이터 | 소스 | 용도 |
|---|---|---|
| 나스닥 지수 | `^IXIC` — yfinance/Stooq | 마삼 감지 (단일 기준, 변경 불가) |
| S&P500 | `^GSPC` / SPY | MA50 레짐 필터 |
| VIX | `^VIX` | 레짐·보조 |
| 헤지 자산 4종 | `TLT`, `IAU`, `GLD`, `TIP` — yfinance | 매도물량 배치처 안내 |
| 1등주 시총 | yfinance `ticker.info['marketCap']` (대형주 상위 10개) | 마삼 1등주 자동 판정 |
| 섹터 ETF | SPDR 11개 | MA50 RS 섹터 |
| FRED | `DFF`(기준금리), `DGS10`(10Y) | 금리환경 판단 |
| PMI (제조업·서비스업) | 대체 무료 소스 탐색 (S&P Global 등) · Phase 0 확정 | 시장환경 보조 |
| Fear & Greed | CNN 비공식 API | 마지막 성공값 최대 24h 캐시, 실패 시 N/A |
| WALCL | FRED | QE 여부 (4주 이동평균 기울기 자동 판정) |
| 참조 유니버스 | S&P500 + NDX 일별 종가 롤링 캐시 | MA50 RS percentile |

### 수집 규칙

- 나스닥 기준: `^IXIC` 원지수만 사용. S&P500·QQQ 혼용 금지.
- 금리 환경: `DFF ≤ 0.25%` = 제로금리 / `DFF > 0.25%` = 비제로금리
- QE 감지: WALCL 4주 이동평균 기울기 상승 → QE_ON, 하락 → QE_OFF. 모호 구간 → "QE 여부 수동 확인" 알림.
- 공황 카운트(마삼 4회) 윈도우: **같은 달**(월 단위) — MODE 3 PANIC 트리거.
- 공황 +45% 판정 윈도우: **전년 역년**(1/1~12/31) `^IXIC` 수익률 — 매년 1/1 갱신, PANIC_EMERGENCY 등급용.
- 참조 유니버스: 종가만 롤링 캐시 (전체 히스토리 매일 재수집 금지 — 무료 한도 유지).
- 이상치(±20%/일): 자동폐기 금지 → 검수 플래그 후 코퍼레이트 액션 대조.

---

## 4. 공통 파이프라인 (GitHub Actions · 18:00 ET)

```
1. EOD 수집: ^IXIC·^GSPC·^VIX + 1등주 mcap(상위 10개) + TLT·IAU·GLD·TIP
           + 워치/보유 + 참조유니버스 + SPY + 섹터ETF + FRED(DFF·DGS10·WALCL) + PMI(대체소스·미확정) + F&G
2. 공통 지표: MA50/MA200 · VolMA · ATR14 · slope · gap · highN · regime · 금리환경
3-A. 마삼 엔진 평가  → masam.json
3-B. MA50 엔진 평가  → signals.json / positions.json / transitions.json
4. 전일 스냅샷 대조 → 신규 트리거 추출
5. 트리거 → Web Push (알림 배지: [마삼] / [MA50])
6. 저장: repo JSON / Gist / Supabase·Upstash free
[PWA] 정적 JSON fetch → 렌더
```

---

## 5. 전략 A — 마삼 대응 엔진

### 5-1. 핵심 원칙

- **모든 신호는 EOD 종가 기준**으로 산출
- **앱 역할**: 국면 판정 + 행동 안내. 실제 매수·매도는 사용자가 직접 판단·실행
- 원본 룰북 최우선. 보완 옵션(B·C·D)은 기본값 OFF, 설정에서 수동 활성화

### 5-2. 3-모드 상태머신

```
MODE 1 : REBALANCING  ── 마삼 없음 + 1등주 전고점 대비 하락 감지
MODE 2 : CRISIS        ── 나스닥 -3% 발생 (마삼 발생)
MODE 3 : PANIC         ── 같은 달 마삼 4회↑ (공황 확정)
                           └─ PANIC_EMERGENCY: 전년 ^IXIC 역년 ≥ +45% AND 마삼 4회↑
```

**MODE 1 — REBALANCING**
- 마삼 無 + 1등주 전고점 대비 하락 시 진입
- -2.5% 하락마다 1등주 10% 매도 (현금화)
- 현금화 상한: 25% or 50% (사용자 설정 `max_rebalancing_pct`)
- 개별 종목 이슈 시 → QQQ 10% 매수
- 전체 시장 위기 시 → 현금 보유 → 마삼 발생 시 MODE 2 전환
- 반등 재매수: 최종 구간에서 2구간 상승 → 전량 재매수 (비QE: +5% / QE: +2.5%)

**MODE 2 — CRISIS (말뚝박기)**
- 비제로금리: 초기 50%, -5% 하락마다 +10%
- 제로금리: 초기 25%, -2.5% 하락마다 +10%
- [수익 중] 말뚝 비중 제외 전량 매도 / [손실 중] 전량 매도 후 말뚝 재진입
- 헤지 배치: 비제로+QE이전 → TLT / 제로or QE시작 → IAU+GLD/TIP 1:1 / 방향 불명 → 달러
- V자 올인 조건: 비제로 +10%(2구간) / 제로 +5%(2구간)
- 긴급 올인: 고점 대비 -30%
- 올인 조건 4종: 한달+1일 무마삼① / 8거래일 연속 상승② / 1등주 전고 돌파③ / 나스닥 전고 돌파④
- 위기 해제(월 3회↓): 마지막 마삼+1개월+1일 / (월 4회↑): +2개월+1일
- 즉시 해제: 1등주 2단계 V자 / 1등주 최고점 갱신 / 나스닥 8일 연속 상승 / 나스닥 최고가 갱신

**MODE 3 — PANIC**
- PANIC_EMERGENCY (전년 +45% AND 4회↑):
  - 말뚝박기 즉시 중단 → 전량 매도 → 현금 100%
  - ❌ 고점 -30% 몰빵 없음 / ❌ 1등주 -30% 몰빵 없음
  - V자 기준 강화: 비제로 6구간(+30%) / 제로 6구간(+15%)
- PANIC_BASIC: 레거시 매뉴얼 기준, TLT/IAU+GLD+TIP 헤지 운용 유지
- 공황 재진입 분할: 35% / 35% / 30% 3트랜치
- 추가 자금 투입: RSI14 ≤ 50 AND MFI14 ≤ 50 동시 충족 시 (1등주 기준)

### 5-3. 1등주 판정

- 대형주 상위 10개 리스트 → yfinance 순차 조회 → mcap 자동 1위 결정
- 1등-2등 격차 <10% → 1:1:1(1·2·3등주) 편입
- 2등주 mcap > 1등주 mcap → 1:1 전환 알림 (`overtake_detected`)
- 2등주 격차 15% 초과 벌어지면 → 2등주 매도, 1등주 집중
- 대형주 리스트: 분기 1회 수동 갱신

### 5-4. 보완 옵션 레이어 (기본 OFF)

| 옵션 | 충돌 | 기본값 |
|---|---|---|
| B-4 트리거 등급 약/중/강 표시 | 없음 | ON |
| D-2-1 VIX·F&G 참고 패널 | 없음 | ON |
| B-1 마삼 동적기준(VIX/ATR) | 원본 -3% 고정 변경 | OFF |
| C-1 -30% 분할 투입 | 원본 전량 올인 변경 | OFF |
| C-2 올인 구조 완화 | 원본 단일신호=올인 변경 | OFF |
| C-3 V자 진입 강화 | 원본 2구간=올인 변경 | OFF |
| C-4 손절 규칙 | **원본 6번(말뚝박기 고수)과 정면 충돌** | OFF |
| C-5 공황 단계 청산 | 원본 4회 일괄 매도 변경 | OFF |

충돌 옵션 ON 시 → "원본 룰 변경 — 백테스트 검증 권장" 경고 배너 표시.

### 5-5. 서비스 범위 제외 규칙 (의도적 제외 — 누락 아님)

매뉴얼 A에 존재하나 자동 판정이 불가능하거나 무료 데이터로 신뢰도를 확보할 수 없어 **서비스 자동화 범위에서 제외**한다. "룰북 무결성"은 자동화 가능한 규칙에 한해 적용되며, 아래는 사용자 자체 판단 영역으로 남긴다.

| 제외 규칙 | 원본 | 사유 |
|---|---|---|
| 팬덤/천재 CEO 보유 시 전체 10% 투자 | A §1 | 정성 판단 — 자동화 불가, 사용자 자체 결정 |
| "불노 하락" 어닝 룰 (발표 전 1·2주 추세 + 어닝쇼크 후 매도·재매수) | A §2 | 어닝 캘린더·서프라이즈의 무료 데이터 신뢰도 부족 |
| 헤지 금리방향 3분기 자동 분기 (10Y 추세 ↑→달러/↓→TLT/불명→달러) | A §3 | 제외. 헤지 타입은 **QE/금리환경 기준만** 사용 (미QE·방향 미상 시 달러 기본) |

---

## 6. 전략 B — MA50 스크리너 엔진

### 6-1. 지표 정의

```
MA50, MA200, VolMA20, VolMA3
MA50_slope_pct = (MA50[0]−MA50[10]) / MA50[10]
gap50 = (close−MA50) / MA50
gap200 = (MA50−MA200) / MA200
highN = max(high[1..breakout_high_lookback])
ATR14 (사이징·이상치용)

RS_raw = 0.5·(r20ₛ−r20ₘ) + 0.3·(r60ₛ−r60ₘ) + 0.2·(r120ₛ−r120ₘ)  (vs SPY)
RS_pct = 참조유니버스(S&P500+NDX) 내 RS_raw의 percentile rank (0~100)  ← 주 지표
RS_sector_pct = 섹터 ETF 기준 동일
```

### 6-2. 레짐 필터

```
regime = (SPY_close > SPY_MA200) ? RISK_ON : RISK_OFF
```

RISK_OFF 시: strict 모드 = BUY 전면 비활성 / soft 모드 = Track B만 허용, vol_mult↑, overshoot_max↓

### 6-3. 매수 — 2트랙

공통 게이트: 레짐 통과 + `gap50 ≤ overshoot_max` + `volume[0] ≥ vol_mult·VolMA20`

**Track B — STRONG_BREAKOUT (기본)**
```
선행: close[1] ≤ MA50[1]  AND  최근 lookback_below일 close<MA50 ≥ 60%
돌파: close[0] > MA50[0]  AND  close[0] > highN
```

**Track A — EARLY_TREND (옵션·공격형)**
```
돌파: close[0] > MA50[0]  AND  close[1] ≤ MA50[1]
안전장치(필수): RS_pct ≥ rs_early_th  AND  MA50_slope_pct > 0
```

**Track Bounce — BOUNCE**
```
추세: 최근~20일 close>MA50 다수  AND  slope_pct>0  AND  MA50>MA200
근접: min(low[0..k]) ≤ MA50·(1+proximity_pct)
지지: min(close[0..k]) ≥ MA50·(1−break_tol)
반등: close[0]>close[1]  AND  close[0]>MA50
```

### 6-4. 매도 — 3-State (우선순위 순)

`breakdown = close[0] < MA50·(1−sell_tol) OR (close[0]<MA50 AND close[1]<MA50)`

| 우선순위 | 조건 | 결과 |
|---|---|---|
| 1 | `close ≥ MA50` | OK (리셋) |
| 2 | `close<MA50` 연속 `consec_below_sell`일 | SELL (강제) |
| 3 | HOLD-WATCH `days_in_state > max_hold_watch_days` | SELL (강제) |
| 4 | `breakdown` AND `close < MA200` | SELL |
| 5 | `breakdown` AND `close>MA200` AND `RS_pct>50` | HOLD-WATCH |
| 6 | `breakdown` (그 외) | SELL |

RISK_OFF 시 `consec_below_sell`, `max_hold_watch_days` 자동 축소.

### 6-5. 스크리닝 상태머신 (ticker 단위)

```
WATCH → BUY → HOLDING → SELL-WATCH → SELL → WATCH
```

저장 필드: `state`, `prev_state`, `entered_at`, `days_in_state`, `last_signal_date`
전이 시 `days_in_state = 0`. 전이 기록은 `transitions.json`에 append-only.

### 6-6. 포지션 레이어 (스크리닝 state와 분리)

동일 종목 재진입 = 새 `position_id`. HOLD-WATCH 경과일·손익은 포지션 단위 추적.

```json
{
  "position_id": "AAPL-20260605-001",
  "ticker": "AAPL",
  "status": "OPEN",
  "entry_date": "2026-06-05",
  "entry_price": 201.3,
  "size": 0.1,
  "stop_level": 193.5,
  "exit_date": null,
  "exit_price": null,
  "realized_pnl": null
}
```

`stop_level` = entry 기준 ATR 배수 또는 MA50 하단 (둘 중 보수적).

### 6-7. 스코어 공식

```
vol_score      = min(vol_ratio / vol_cap, 1)
breakout_score = min(gap50 / overshoot_max, 1)
rs_score       = RS_pct / 100
trend_score    = 0.5·min(MA50_slope_pct / slope_cap, 1) + 0.5·(MA50>MA200 ? 1 : 0)

score = 100 · (w1·vol_score + w2·breakout_score + w3·rs_score + w4·trend_score)
보너스(옵션): VolMA3 상승 +b, 이격수렴+확신태그 +c   # HOLD 랭킹용
```

기본 가중 `w1..w4 = 0.25`, `slope_cap = 0.05`, `vol_cap = 3`

### 6-8. 파라미터 기본값

| 파라미터 | 기본값 |
|---|---|
| `breakout_high_lookback` | 20 |
| `vol_mult` / `vol_cap` | 1.5 / 3 |
| `rs_early_th` | 80 |
| `lookback_below` | 7 |
| `overshoot_max` | 7% |
| `proximity_pct` / `break_tol` / `sell_tol` | 3% / 1% / 1% |
| `consec_below_sell` | 2~3 (RISK_OFF: 1) |
| `max_hold_watch_days` | 5~10 (RISK_OFF: 3) |
| `conv_th` | 4% |
| `rs_weights` | .5 / .3 / .2 |
| `score_w1..4` | .25 each |
| `slope_cap` | 5% |
| `regime_mode` | strict |
| `risk_per_trade` | 10% |
| `atr_mult` | 2.0 |

---

## 7. JSON 산출물 스키마

| 파일 | 내용 | 전략 |
|---|---|---|
| `masam.json` | 3-모드 상태·비중·헤지배치·트리거거리·알림 | A |
| `mcap_daily.json` | 대형주 상위 10개 시총·1등주 판정 | A |
| `hedge_prices.json` | TLT·IAU·GLD·TIP 일봉 종가 | A |
| `signals.json` | 매수후보·3-state·score·metrics | B |
| `positions.json` | 포지션 OPEN/CLOSED·손익 | B |
| `transitions.json` | append-only 상태 전이 기록 | B |
| `market.json` | regime·금리·VIX·F&G·PMI | 공통 |
| `params.json` | 전략별 파라미터·옵션 토글 상태 | 공통 |

### masam.json 핵심 필드

```json
{
  "as_of": "YYYY-MM-DD",
  "mode": "REBALANCING | CRISIS_STAKING | PANIC",
  "panic_type": "null | BASIC | EMERGENCY",
  "rate_env": "ZERO | NON_ZERO",
  "qe_active": false,
  "masam": { "month_count": 0, "cumulative_count": 0, "last_masam_date": null },
  "leader_status": { "rank1_ticker": "NVDA", "rank1_mcap": 0, "rank2_ticker": "AAPL",
    "rank2_mcap": 0, "gap_pct": 0, "overtake_detected": false, "gap_below_10pct": false },
  "target_allocation": { "stock_pct": 0, "hedge_pct": 0, "cash_pct": 0, "label": "" },
  "hedge_allocation": { "type": "TLT | IAU_GLD_TIP | DOLLAR | NONE", "rationale": "", "exit_trigger": "" },
  "distance_to_triggers": { "v_allin_pct_needed": 0, "emergency_allin_pct_away": 0 },
  "all_in_conditions": [{ "id": 1, "label": "한달+1일 무마삼", "met": false, "grade": "약" }],
  "additional_buy_signal": { "rsi14": 0, "mfi14": 0, "both_below_50": false, "label": "" },  // rsi14/mfi14 = 1등주 종가 기준
  "panic_reentry": { "stage": 0, "next_tranche_pct": 35, "tranches": [35, 35, 30] },
  "recommended_action": "",
  "alerts": []
}
```

### signals.json 핵심 필드

```json
{
  "as_of": "YYYY-MM-DD",
  "regime": "RISK_ON | RISK_OFF",
  "items": [{
    "ticker": "AAPL",
    "signal_type": "EARLY_TREND | STRONG_BREAKOUT | BOUNCE | SELL | HOLD_WATCH | OK",
    "state": "BUY",
    "score": 82,
    "trigger_reason": "",
    "metrics": {
      "close": 0, "ma50": 0, "ma200": 0, "gap50": 0, "gap200": 0,
      "vol_ratio": 0, "rs_pct": 0, "rs_sector_pct": 0,
      "ma50_slope_pct": 0, "high_n": 0, "atr14": 0, "sector_etf": "XLK"
    }
  }]
}
```

---

## 8. UX / IA 구조

### 전체 앱 셸

- 상단 세그먼트 토글: `[마삼 대응]` `[MA50 스크리너]` — 선택 상태 영구 저장
- 면책 Footer: `position: fixed; bottom: 0` 전 화면 하단 상시 노출
  - "⚠️ 투자 권유 아님 · 실거래 전 백테스트 검증 필수"
- 알림 센터: 두 전략 공유 (`[마삼]` / `[MA50]` 배지로 구분)

### 마삼 대응 모드 (대시보드형 · 3탭)

| 탭 | 내용 |
|---|---|
| 현재 국면 | 모드 배지 · 비중 카드(주식/헤지/현금%) · 다음 트리거까지 거리 · RSI·MFI 배지(1등주) · 1등주 현황 |
| 행동 가이드 | 모드별: REBALANCING=현금화 단계 / CRISIS=올인조건 체크리스트+헤지배치 / PANIC=해제 카운트다운+재진입 트래커 |
| 시장환경/설정 | 금리·QE·VIX·F&G·PMI · 헤지자산 현재가 · 리밸런싱 한도 토글(25%/50%) · 옵션 토글 |

PANIC_EMERGENCY 시 경고 배너 표시: "고점 -30% 몰빵 없음 · V자 6구간 기준 적용 중"

### MA50 스크리너 모드 (스크리너형 · 4탭)

| 탭 | 내용 |
|---|---|
| 매수 후보 | 점수순 · STRONG/EARLY/BOUNCE 배지 · RISK_OFF 배너 |
| 보유 관리 | 포지션 단위 상태칩·경과일·손익·손절선 |
| 시장 환경 | regime·금리·PMI·VIX·F&G ← **마삼 탭3 컴포넌트 공유** |
| 종목 상세/설정 | 차트·펀더멘털 체크리스트·파라미터·전이기록 |

"시장 환경" 탭은 두 전략 공통 컴포넌트 하나로 공유.

### 디자인 시스템 (ux-ui_mockup.html 기준)

```css
--bg: #16161a
--card: #1e1f24
--card-sub: #1b1c20
--inset: #26272d
--t1: #f3f3f5  /* 기본 텍스트 */
--t2: #8b8d94  /* 보조 텍스트 */
--t3: #5a5b63  /* 3차 텍스트 */
--up: #f04452  /* 상승 (한국 관례: 빨강=상승) */
--down: #4593fc /* 하락 (파랑=하락) */
--accent: #3182f6
--green: #15c47a
--amber: #f7a93b
--teal: #3fc8a9
```

- 폰트: Pretendard (font-weight 500 기본, 700·800 헤딩)
- 카드 radius: 16px
- 패딩: 20px (좌우)
- 차트: lightweight-charts 통일

---

## 9. 구현 단계 (Phase)

| Phase | 내용 | 체크 |
|---|---|---|
| **0 데이터 PoC** | ^IXIC 마삼 감지·금리환경·전고점 + MA50 RS percentile·신고가 + PMI 소스 후보 검증 동시 검증 스크립트 | [ ] |
| **1 엔진** | 마삼 3-모드 상태머신 + MA50 2트랙/3-state 시그널 + 백테스트(익일시가·사이징) | [ ] |
| **2 백엔드** | GitHub Actions cron + ticker state/position persistence + 저장 + API | [ ] |
| **3 모바일 UI** | 전략 토글 + 마삼 3탭 + MA50 4탭 + 시장환경 공유 컴포넌트 + 면책 Footer | [ ] |
| **4 알림/설정** | Web Push + 파라미터·옵션 토글·펀더멘털 체크리스트 | [ ] |
| **5 검증/최적화** | MA50 워크포워드 + 마삼 룰/옵션 백테스트 | [ ] |

---

## 10. 구현 제약 사항 (반드시 준수)

### 룰북 무결성

- 마삼 엔진의 원본 룰(A·B 매뉴얼)은 코드에서 하드코딩으로 구현. 임의 변경 금지.
- 보완 옵션(B·C·D)은 `params.json`의 옵션 토글로만 활성화. 항상 기본값 OFF.
- 원본 충돌 옵션 ON 시 반드시 경고 배너 표시.

### 데이터 정확성

- 나스닥 기준은 `^IXIC` 단일. QQQ·SPY·^GSPC로 마삼 판단 금지.
- 수정주가 반드시 사용 (분할·배당 조정 포함).
- 이상치(±20%/일) 자동 폐기 금지 — 검수 플래그 부착 후 사용자에게 표시.

### 비용·인프라

- 서버리스 렌더링 유지 — 런타임 API 서버 추가 금지.
- 무료 한도 초과 소스 사용 금지.
- 참조 유니버스 전체 히스토리 매일 재수집 금지 (롤링 캐시만).

### 면책

- 면책 Footer는 `position: fixed; bottom: 0` — 어떤 화면에서도 숨김 처리 금지.
- 앱 내 어디서도 "투자 추천", "수익 보장" 류의 문구 사용 금지.

### 백테스트

- 체결 기준: 시그널 = 종가 산출 → **익일 시가 체결** (look-ahead 방지).
- 생존편향 제거: point-in-time 유니버스 (상폐·교체 포함).
- 포지션 사이징: fixed-fractional(`risk_per_trade`) 기본, ATR 옵션 — 미적용 시 성과 왜곡 주의.

---

## 11. 워크플로우 오케스트레이션

### 플랜 모드 기본값

- 비자명한 작업(3단계 이상 또는 아키텍처 결정)에는 반드시 플랜 모드 진입
- 일이 틀어지면 즉시 STOP하고 재계획 — 계속 밀어붙이지 말 것

### 서브에이전트 전략

- 메인 컨텍스트 윈도우를 깨끗하게 유지하기 위해 서브에이전트를 적극 활용
- 리서치, 탐색, 병렬 분석은 서브에이전트에 위임
- 서브에이전트당 하나의 작업만 배정

### 자기개선 루프

- 사용자로부터 수정 받을 때마다 이 `CLAUDE.md`에 패턴 업데이트
- 동일한 실수를 방지하는 규칙을 스스로 작성
- 세션 시작 시 이 파일 검토

### 완료 전 검증

- 작동을 증명하지 않고는 절대 작업 완료로 표시하지 말 것
- "시니어 엔지니어가 이걸 승인할까?" 자문하기

---

## 12. 태스크 관리

1. **계획 우선:** 구현 시작 전 체크 가능한 항목으로 계획 작성
2. **계획 검증:** 구현 전 사용자 확인
3. **진행 추적:** 진행하면서 항목 완료 표시
4. **변경 설명:** 각 단계에서 고수준 요약 제공
5. **레슨 캡처:** 수정 후 이 `CLAUDE.md` 업데이트

---

## 13. 핵심 원칙

- **단순함 우선:** 모든 변경을 최대한 단순하게. 최소한의 코드 영향.
- **게으름 금지:** 근본 원인을 찾아라. 임시 수정 없음. 시니어 개발자 기준.
- **최소 영향:** 변경은 필요한 부분만. 새로운 버그 도입 금지.
- **룰북 우선:** 엔진 로직은 설계안이 정답. 임의 해석·단순화 금지.

---

## 14. 소프트웨어 구축 워크플로우 (7단계)

참고: https://github.com/obra/superpowers.git

1. **brainstorming** — 코드 작성 전 활성화. 거친 아이디어를 질문으로 다듬고, 대안 탐색, 설계를 섹션별로 검증받음. 설계 문서 저장.
2. **using-git-worktrees** — 설계 승인 후. 새 브랜치에 격리된 워크스페이스 생성, 프로젝트 셋업, 테스트 베이스라인 확인.
3. **writing-plans** — 승인된 설계와 함께. 작업을 2~5분 분량의 태스크로 분해. 정확한 파일 경로·완전한 코드·검증 단계 포함.
4. **subagent-driven-development / executing-plans** — 계획 완성 후. 태스크마다 서브에이전트 투입, 2단계 리뷰(스펙 준수→코드 품질).
5. **test-driven-development** — 구현 중. RED-GREEN-REFACTOR 강제. 테스트 먼저.
6. **requesting-code-review** — 태스크 사이. 계획 대비 코드 리뷰, 심각도별 이슈 보고. Critical 이슈는 진행 차단.
7. **finishing-a-development-branch** — 모든 태스크 완료 후. 테스트 검증, 선택지 제시, 워크트리 정리.

---

## 15. 디자인 가이드

1. **스케치 먼저:** `ux-ui_mockup.html` 구조를 기준으로 삼을 것. 변경 전 승인 필요.
2. **스크린샷 참고:** 특정 섹션 스크린샷 첨부 시 해당 스타일을 따를 것.
3. **디자인 시스템 준수:** 섹션 8의 색상 팔레트·폰트·radius 규칙 엄수. 변형 시 승인 필요.
4. **빌드 전 확인:** 폰트(Pretendard 확정)·아이콘(lucide-react 또는 SVG 직접) UI 구현 전 승인.
5. **ui-ux-pro-max 스킬 활용:** UI 코드 작성 전 추론 엔진 실행.
