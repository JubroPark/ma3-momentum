# CLAUDE.md — 통합 투자 전략 모바일 서비스 (ma3 momentum) · v2

> 이 파일은 Claude(및 Claude Code)가 본 프로젝트 작업 시 반드시 숙지해야 할 컨텍스트·설계 결정·구현 규칙을 담는다.
>
> **단일 진실원천(Source of Truth)**: 엔진 규칙의 정답은 아래 두 매뉴얼이다. 이 CLAUDE.md는 그것을 **통합·요약·연결**하고 구현 규칙을 정의할 뿐, 규칙을 재해석·재서술해 원본과 어긋나게 만들지 않는다. 충돌 시 매뉴얼이 우선한다.
>
> - 마삼 엔진 정답: `new_조던_마삼룰_통합매뉴얼.md` (v3)
> - 모멘텀 엔진 정답: `new_미주은_모멘텀_탑픽_전략구조.md` (v3, Implementation Spec)
> - 프론트 기준: `ux-ui_mockup_v2.html` (디자인 시스템·IA의 토대)

---

## v2 주요 변경 (v1 대비)

1. 전략 B를 **MA50 스크리너 → 미주은 모멘텀 탑픽**(탑픽·줍줍·무한보유)으로 전면 교체.
2. 마삼 공황 단순화: `전년 +45%` 전제·`PANIC_EMERGENCY/BASIC` 구분 **제거** → 공황 = "달력 월 마삼 4회" 단일 트리거.
3. 긴급 올인 = 고점 대비 6구간 하락(비제로 **-30%** / 제로 **-15%**)을 **평시·공황 공통 정식 룰**로. V자 올인은 항상 2구간(+10%/+5%), 공황 전용 6구간 반등 룰 제거.
4. **공황 후 올인 → 최고점 경신까지 완전 홀드**(리밸런싱·말뚝박기 모두 중단) 신규 반영.
5. 어닝(불노)·팬덤/천재 CEO 10% 규칙 **제거**.
6. 헤지 선택 **완전 자동화**(금리환경·QE + 10Y 국채금리 추세까지 자동) — v1의 "10Y 추세 제외"를 뒤집음.
7. 데이터 정리: 섹터 ETF·RS percentile 참조유니버스 **제거**. VIX·F&G·PMI는 **경제지표 화면 표시용**으로 유지(엔진 신호 아님 / VIX·F&G는 부록 Z 옵션).
8. 1등주 = **투자 가능 글로벌 시총 상위 큐레이트 리스트(분기 수동) 중 자동 1위**. companiesmarketcap.com 레퍼런스.
9. 데이터 시점: **판정용 = EOD(종가) 고정 / 표시용 = 준실시간**(장중 live 배치, 무료·무서버).
10. 시장 화면 **전략별 분리**(공유 "시장 환경" 탭 폐기).

---

## 1. 프로젝트 한 줄 요약

하나의 PWA에서 **마삼룰**(나스닥 -3% 룰 기반 국면 대응)과 **모멘텀**(미주은 탑픽·3분할 줍줍·무한보유) 두 전략을 상단 토글로 전환해 쓰는 모바일 투자 보조 서비스. 데이터·저장·알림(공통 코어)은 공유하되, **전략별 엔진·시장 화면은 분리**한다. **전면 무료 스택**. ⚠️ 투자 권유 아님, 규칙 기반 모니터링·알림 도구.

---

## 2. 기술 스택 (확정)

| 영역 | 기술 |
|---|---|
| 프레임워크 | Next.js 14+ App Router · TypeScript · Tailwind CSS |
| 차트 | lightweight-charts (시계열) + 커스텀 게이지/바(공포탐욕·구간 등) |
| 배포 | Vercel Hobby (무료) |
| 저장소 | **공개(public) GitHub repo** — Actions 무료 실행이 핵심 전제 |
| 배치 | GitHub Actions cron — ① EOD 1일 1배치(신호) ② 장중 live 배치(표시, 5~15분) |
| 영구 캐시 | repo JSON / Gist (공개 신호) · Vercel KV/Upstash·Supabase free (사용자별) |
| 알림 | Web Push / VAPID (무료) |
| 데이터 | yfinance + Stooq(가격) · FRED(금리·QE·10Y) · companiesmarketcap(분기 1등주 레퍼런스) |
| 폰트 | Pretendard (Variable, jsDelivr CDN) |

**PWA 렌더링 원칙**: 서버 API 없음. PWA는 **자기 정적 JSON만 fetch**(외부 API 직접 호출 금지 → CORS·rate limit 회피). 서버 비용 0.

---

## 3. 전체 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                        PWA App Shell                       │
│   상단 토글: [ 마삼룰 ] [ 모멘텀 ]  (선택 상태 영구 저장)    │
│   하단 4-탭: 앞 2칸 전략별 교체 · 뒤 2칸(경제지표·설정) 공유 │
│   알림 센터: 두 전략 공유([마삼]/[모멘텀] 배지로 구분)      │
└───────────────┬──────────────────────┬────────────────────┘
                │                      │
        ┌───────▼──────┐      ┌────────▼─────────┐
        │  마삼 엔진     │      │  모멘텀 탑픽 엔진  │
        │ (3-모드 상태기) │      │ (탑픽·줍줍·트레일) │
        └───────┬──────┘      └────────┬─────────┘
                │   (자본·신호 비연동, 시장 국면도 전략별)  │
        ┌───────▼──────────────────────▼─────────┐
        │            공통 코어 (Shared Core)        │
        │   데이터 수집 · 저장 · 알림 · 준실시간 표시  │
        │   GitHub Actions: EOD 배치 + 장중 live 배치 │
        └──────────────────────────────────────────┘
```

- 두 전략은 **완전 독립** — 자본·신호 비연동, 시장 국면 개념도 분리(마삼=금리/QE, 모멘텀=GREEN/YELLOW/RED). 엔진 간 가드 없음, 자본 배분은 사용자 판단.
- **판정용 데이터는 EOD 종가 기준 결정론적**(동일 입력→동일 출력). 장중 값으로 신호·상태전이를 절대 발동하지 않는다.

---

## 4. 데이터 수집 규칙

### 4-1. 수집 대상

| 데이터 | 소스 | 용도 | 비고 |
|---|---|---|---|
| 나스닥 종합 `^IXIC` | yfinance/Stooq | 마삼 감지(단일 기준, 변경 불가) | 코어 |
| S&P500 `^GSPC`/SPY, 나스닥100 `^NDX`/QQQ | yfinance | 모멘텀 국면(GREEN/YELLOW/RED) | 코어 |
| 1등주 후보 mcap | yfinance `ticker.info['marketCap']` (큐레이트 리스트) | 1등주 자동 판정 | 코어 (4-3) |
| 탑픽 가격 OHLCV | yfinance/Stooq | 모멘텀 지표(MA50/200·ATR·수평지지) | 코어 |
| 탑픽 펀더멘털 | 운영자 입력 + 외부 매핑 | 탑픽 스코어(0~100) | 분기 갱신 |
| 헤지 4종 `TLT`·`IAU`·`GLD`·`TIP` | yfinance | 마삼 헤지 배치 | 코어 |
| FRED `DFF`·`DGS10`·`WALCL` | FRED API | 금리환경·10Y 추세·QE 판정 | 코어 (헤지 완전자동) |
| VIX `^VIX` | yfinance | 경제지표 **표시** + 부록 Z 옵션 | 표시용 |
| Fear & Greed | CNN 비공식 API | 경제지표 **표시** + 부록 Z 옵션 | 표시용·캐시 24h·실패 시 N/A |
| ~~PMI(제조·서비스)~~ | ~~무료 자동 소스 없음~~ | ~~제거됨~~ | 자동화 불가로 경제지표 탭에서 제거 |
| 환율(USD/KRW) | 무료 소스 | 표시(시총·관심 화면 롤) | 표시용 |

> **제거(v1 대비)**: 섹터 ETF, S&P500+NDX RS percentile 참조유니버스 — 모멘텀이 RS percentile을 더 이상 쓰지 않음.

### 4-2. 수집·판정 규칙

- 마삼 기준: `^IXIC` 원지수만. QQQ·SPY·`^GSPC`로 마삼 판단 금지. 수정주가 필수.
- 금리환경: `DFF ≤ 0.25%` = 제로 / `DFF > 0.25%` = 비제로.
- QE: `WALCL` 4주 이동평균 기울기 ↑ → QE_ON / ↓ → QE_OFF / 모호 → "수동 확인" 알림.
- **10Y 추세(헤지 완전자동)**: `DGS10`의 N거래일 기울기 부호로 추세 결정론적 산출(하락↓ → TLT / 상승↑ → 달러 / 미상 → 달러). N은 `params.json`에 둠.
- **마삼 카운팅 = 달력 월 기준**, 월 변경 시 0으로 리셋(30일 롤링 아님). 위기 종료 = 마지막 마삼 +1개월+1일 / 공황 = 같은 달력 월 4회+, 종료 = +2개월+1일. 월말 엣지(예: 1/31+1개월)는 "말일+1일" 달력 관례로 고정.
- 이상치(±20%/일): 자동 폐기 금지 → 검수 플래그 후 코퍼레이트 액션 대조.
- 결측/지연: 해당 봉 평가 보류(`stale=true`), 거짓 신호 금지.

### 4-3. 1등주 소싱 (큐레이트 리스트)

- **분기 1회 수동 갱신**: companiesmarketcap.com을 레퍼런스로, **투자 가능(미국 상장 등 실제 매수 가능) 글로벌 시총 상위 N**만 추려 큐레이트 리스트 확정. 사우디 아람코(2222.SR)·중국 A주·접근 불가 종목은 여기서 제외.
- **일별 자동 1위 판정**: 리스트 종목들의 mcap을 **yfinance로 조회**해 1위 결정(사이트 일일 스크래핑 의존 금지 — 안정성·무료 한도·ToS 회피).
- 1·2등 격차·역전 판정도 동일 mcap 소스로 계산(1·2장 규칙).
- (옵션·기본 OFF) cron이 분기 1회 `?download=csv`로 신규 진입 후보를 플래그해 수동 갱신 보조.

### 4-4. 데이터 시점 — EOD / 준실시간 2-트랙

- **판정용 = EOD(종가) 고정**. 신호·모드·상태전이는 EOD 배치만 산출(단일 진실원천).
- **표시용 = 준실시간**: 장중 live 배치(5~15분 cron)가 현재가·등락률·거리(마삼/트리거/스탑선까지)·헤지 시세만 `live.json`에 갱신. PWA는 `live.json`(자기 정적 JSON)만 fetch.
- `live.json`은 **표시값만** 갱신 — 신호/상태/전이는 절대 손대지 않음.
- 장중 알림은 트리거가 아니라 **"잠정/근접"** 라벨로만(예: "장중 나스닥 -2.8% · 마삼 근접"). 확정은 종가에.

---

## 5. 공통 파이프라인 (GitHub Actions · 공개 repo)

```
[EOD 배치 · 22:00 UTC (미 장마감 후, EDT+2h / EST+1h)]
1. EOD 수집: ^IXIC·^GSPC·^NDX·^VIX + 큐레이트 mcap + 탑픽 OHLCV·펀더 + TLT·IAU·GLD·TIP
            + FRED(DFF·DGS10·WALCL) + (표시)F&G·환율
2. 공통 지표: MA50/MA200 · ATR14 · 수평지지 · 금리환경 · QE · 10Y 추세
3-A. 마삼 엔진 평가 → masam.json / mcap_daily.json / masam_market.json / hedge_prices.json
3-B. 모멘텀 엔진 평가 → positions.json / indicators.json / actions.json / transitions.json / momentum_market.json
4. 전일 스냅샷 대조 → 신규 트리거 추출 → Web Push([마삼]/[모멘텀] 배지)
5. 저장: repo JSON / Gist / KV

[유니버스 스크리닝 · 23:00 UTC · 소요 ~40~45분]
- NASDAQ+NYSE 전체 스크리닝 → universe.json 갱신
- 완료 직후 fetch_momentum.py 재실행 → positions.json sync (REMOVED→WATCH 복귀 당일 반영)
- EOD 배치(22:00)는 전날 universe.json 기준으로 sync → 유니버스 스크리닝 후 재sync로 1일 래그 해소

[장중 live 배치 · 15분 주기 · 표시용만 · UTC 13:00~20:15]
- 현재가·등락률·거리·헤지 시세 → live.json (표시값 전용)
```

> **GitHub Actions cron 주의**: scheduled workflow가 active 상태임에도 cron이 조용히 멈추는 버그 발생 이력 있음(2026-06-22 확인). 워크플로우 파일 변경 푸시로 재등록. push 충돌 방지를 위해 커밋 후 `git pull --rebase origin main && git push` 사용.
>
> **수동 갱신 버튼**: `POST /api/refresh` → GitHub workflow_dispatch(live.yml + eod.yml 동시 트리거) → 35초 후 앱 자동 새로고침. 모든 탭 topbar 우측 원형 버튼(`mdi-light:refresh`, 23px).

---

## 6. 전략 A — 마삼룰 (요약 · 정답: `new_조던_마삼룰_통합매뉴얼.md`)

### 6-1. 핵심 원칙

- 모든 판정은 **EOD 종가** 기준. 앱 역할 = 국면 판정 + 행동 안내. 실매매는 사용자.
- 원본 룰 최우선. 보완(부록 Z)은 기본 OFF, 설정에서 항목별 토글.

### 6-2. 3-모드 상태머신 (용어: 평상시/위기/공황)

```
평상시 (NORMAL)  ── 마삼 無. 핵심 운용 = 리밸런싱
위기   (CRISIS)  ── 마삼 1회+ (말뚝박기)
공황   (PANIC)   ── 같은 달력 월 마삼 4회+
```

**평상시(리밸런싱) — 곧 운용 국면이다(쉬는 상태 아님)**
- 1·2등 격차: 10% 초과 → 1등 집중 / 10% 이내 → 1:1(:1) / 2등 추월 → 1:1 / 2등 15% 밖 → 2등 시가매도 → 1등.
- 25% 현금화 리밸런싱: 전고점 대비 1구간(QE -2.5% / 그 외 -5%) 하락마다 1등주 10% 매도, 최대 25%(설정 시 50%). 개별 이슈 → QQQ 10% 매수. 시장 위기 조짐 → 현금 보유 → 마삼 발생 시 위기 전환. 막바지 2구간 상승 → 전량 재매수.
- QQQ 갈아타기(7장): 1등주 단독 급락(마삼 無) + 1·2등 격차 10% 초과 시 → -10%/-20%/…/-50%에 QQQ 20%씩, 회복(전고 돌파/ MDD +10%) 시 역전환.

**위기(말뚝박기)**
- -3% 당일: [수익 중] 말뚝 제외 매도 / [손실 중] 전량 매도 후 말뚝 재진입.
- 비제로: ~50% 말뚝, -5%마다 주식10%+TLT10% / 제로: ~25% 말뚝, -2.5%마다 주식10%+IAU10%(금선물 제재 시 IAU 대신 현금10%).
- 헤지(완전자동): 제로금리 → IAU_GLD_TIP / 비제로+QE+DFF하락(인하경로) → IAU_GLD_TIP / 비제로+QE+DFF상승·불명확(인상리스크) → DOLLAR / 비제로+QE_OFF+10Y하락 → TLT / 비제로+QE_OFF+10Y상승·불명확 → DOLLAR. **임계값 20bp**(±20bp 미만 = UNKNOWN → DOLLAR).
- 위기 종료 = 마지막 마삼 +1개월+1일(또는 조기 트리거).

**공황 (4회+)**
- 말뚝 즉시 중단 → 전량 매도 → 현금 100% 대기.
- 재진입(올인): 긴급 올인(고점 대비 -30%/-15%) / 2구간 V자(+10%/+5%) / 8거래일 상승 / 전고 돌파 / 2개월+1일.
- **올인 후 → 최고점 경신까지 리밸런싱·말뚝박기 모두 중단(완전 홀드)** → 경신 시 평상시 복귀.
- 재진입 분할: 개별 종목 당일 -1~-2% → 3 하락일 35/35/30 / -2%↓ → 당일 3분할 35/35/30.

### 6-3. 올인 트리거 6종 (원본: 단일 신호 충족 = 올인)

① 한달+1일 무마삼(공황 시 2달+1일) · ② 나스닥 8거래일 연속 상승 · ③ 1등주 전고 돌파 · ④ 나스닥 전고 돌파 · ⑤ 2구간 V자 반등(비제로 +10% / 제로 +5%) · ⑥ 긴급 올인(고점 대비 6구간 = 비제로 -30% / 제로 -15%).
- **⑤ V자 반등 기준점**: 마지막 마삼 발생일 이후 최저 종가(`ixic_crisis_low`). 1년 최저 사용 금지 — 이전 하락장 저점이 기준이 되면 오판 발생.
- 구간 그리드: 제로 2.5% / 비제로 5%(상승·하락 동일 자).
- 추가 자금 투입: RSI14 ≤ 50 AND MFI14 ≤ 50(1등주 기준) 동시 충족 시. 2·9월은 조정의 달.

### 6-4. 서비스 자동화 제외(의도적 — 정보/수동 영역)

| 제외 규칙 | 사유 |
|---|---|
| 과열 시 20% 선제 현금화("이평선 크게 상회") | 임계 모호 → 정보성 알림(기본 OFF 옵션), 자동 판정 안 함 |
| 말뚝 워시세일 절세(실현이익 250만 원 초과 시 손절·재매수) | 세무 정성 판단 — 정보 표시만 |
| 공황 시 환율 대응(달러↔원화) | 정성 판단 — 정보 표시만 |

### 6-5. 보완 옵션 레이어 (부록 Z · 기본 OFF · 설정 토글)

- B-4 트리거 등급(약/중/강) 표시, D-2-1 VIX·F&G 참고 패널 → 충돌 없음, ON 가능.
- B-1 마삼 동적기준(VIX/ATR), C-1 긴급올인 분할, C-2 올인 완화, C-3 V자 강화, C-4 손절(원본 충돌), C-5 공황 단계 청산, D-1/D-2/D-3 → **원본 변경 → 백테스트 필수**, ON 시 경고 배너.

---

## 7. 전략 B — 미주은 모멘텀 탑픽 (요약 · 정답: `new_미주은_모멘텀_탑픽_전략구조.md`)

### 7-1. 핵심 원칙

펀더멘털로 선별(탑픽) → 추세로 대응(이평선·지지선) → **무한 보유**(상승률 익절 금지) → **매도(방어)를 매수보다 먼저 평가**. 알림·시각화 시스템(기본 자동 주문 X).

### 7-2. 탑픽 유니버스

- 스코어 0~100 = 100·(growth .30 + moat .30 + earnings_momentum .30 + financial_health .10). 편입 임계 **70**, 분기 재선정, 동시 추적 **15**.
- `fundamentalsBroken == true` → 즉시 REMOVED 후보(매도 로직 연계). 신규 편입은 WATCH.

### 7-3. 시장 국면 (GREEN/YELLOW/RED · 모멘텀 전용)

```
GREEN  : SPX·NDX 모두 close>MA200 AND 정배열(MA50>MA200)
RED    : red_if=any_break(기본) → 어느 지수든 close<MA200
YELLOW : 그 외(중립)
```
GREEN 정상 / YELLOW 1차 보수적·경고 / RED 신규 매수 차단(기존 3차 줍줍만 수동 옵션).

### 7-4. 매수 (3분할 줍줍) · regime≠RED에서만

| 단계 | 조건 | 투입 |
|---|---|---|
| 1차 ENTRY_1 | (저항 돌파/모멘텀) AND `price ≥ MA50` AND `volRatio ≥ 1.30` | tranche_1 = .30 |
| 2차 ENTRY_2 | `|price-MA50|/MA50 ≤ band(.03)` (50MA 지지) | tranche_2 = .40 (최고 확신) |
| 3차 ENTRY_3 | `price < MA50` AND 수평지지 근접 AND 탑픽점수 ≥ 70 | tranche_3 = .20 (역추세, 작게) |

- `volRatio` = 당일 거래량 / 20일 평균 거래량. 1차 미달 시 ENTRY_1 보류 + "거래량 미확인 돌파" 알림.
- 하락·횡보 중 `volRatio ≥ 1.50` → ⚠️ 거래량 경보(기관 이탈 의심, 매도 강제 아님).

예비 reserve = .10(극단 패닉). 동일 단계 1회만(`deployedTranches`).

### 7-5. 매도 (먼저 평가) · 무한 보유

- 트레일링 스탑: `trailingStopLine = recentHigh·(1-trailPct)`, hybrid = `clamp(max(.20, atr×5·atrPct), .15, .30)`. 1차 터치 → TRIM_HALF(`momtTrimSet`에 기록), 재터치 → EXIT. (recentHigh 비감소 → 스탑선 하향 금지)
- `recentHigh`는 **진입 후 누적** 최고가. 진입 전 52주 고점 미포함 (WATCH 상태에서는 참고용으로만 표시).
- 추세 이탈: ENTRY_2/3에서 `price < 수평지지` → 펀더 훼손 동반 시 EXIT(→REMOVED), 아니면 TRIM_HALF.
- EXIT 후 쿨다운 5거래일. 어닝 hold_through(임박 5일 경고만).

### 7-6. 상태 머신

`WATCH → ENTRY_1 → ENTRY_2 → ENTRY_3 → TRIM → EXIT → (cooldown) → WATCH` / `any → REMOVED(펀더 훼손)`.
- 평가 순서(불변): **펀더 훼손 → 스탑/추세붕괴 → 매수**. 바꾸지 말 것.

### 7-7. 설정(preset)

줍줍 비중 방식(점증형 30/40/20+예비10 기본)·50MA 지지 범위(±3%)·트레일링(혼합·-20%·×5·1차 절반축소)·추세이탈 매도(펀더 훼손 동반 시 전량)·탑픽 임계(70)·재선정(분기)·동시추적(15)·국면 판정 지수(SPX·NDX, any_break)·어닝(hold_through)·실행 모드(alert_only). 검증된 선택지(preset) 중 선택 기본, 고급만 직접 입력. (합=100% 등 저장 검증)

### 7-8. 구현 확정 사항 (현재 운영 중)

- **universe.json**: NASDAQ+NYSE 전체 스크리닝(시총 $1B 이상), TOP_N=60, score≥60 저장. NASDAQ 스크리너 API(`api.nasdaq.com/api/screener/stocks`)로 사전 필터링 후 yfinance 호출
- **positions.json 편입**: score≥70인 종목만 WATCH로 자동 편입
- **REMOVED 임계**: score<40 (펀더 완전 붕괴 수준만) → WATCH→REMOVED
- **moat_score 자동 계산**: 4요소 프록시 — Pricing Power(매출이익률)·Scale(OPM+ROE)·Innovation(R&D/Revenue, income_stmt에서 추출)·Market Premium(PBR). 수동 설정값(≠3.0) 우선
- **EPS 일관성**: `ticker.income_stmt`의 Diluted EPS 연간 추세 → 0~1.0 → earnings_momentum에 ×2.0 반영
- **상태 자동 전이**: `next_action` 신호 → status 자동 전이(`_TRANSITIONS` 테이블). BUY_1→ENTRY_1, BUY_2→ENTRY_2, BUY_3→ENTRY_3, TRIM_HALF→TRIM, EXIT→EXIT
- **하트(♥) = 보유 가정**: `momtFavSet`(localStorage). 최대 15개 UX 가이드 (초과 시 토스트)
- **2단계 트레일링 스탑**: `momtTrimSet`(localStorage) — 1차 터치→비중 축소+기록, 스탑 위 회복→초기화, 2차 터치→전량 매도
- **뱃지 신호**: `next_action` 기반. REMOVED+하트→추세 탈락, 비하트 REMOVED→조건 대기. **진입 임박**: WATCH + `item.metrics.steps_count ≥ 5` + `toppick_score ≥ 75` → 조건 대기보다 상위 뱃지, 추천 비중 base=50 적용
- **종목 정렬**: steps 내림차순 → score 내림차순 (모멘텀 없는 종목이 펀더멘털 점수만으로 상위 노출되는 문제 방지)
- **`calc_weight()` 자동 비중 산출**: `deployed_tranches`(수동 집행 기록) 우선, 없으면 status 기반 fallback(ENTRY_1=30%/ENTRY_2=70%/ENTRY_3=90%/TRIM=45%). MA50 이격 +50%↑ →×0.7, +80%↑ →×0.4 과열 보정. TRIM_HALF 신호 →×0.5, EXIT →0%. 결과는 `weight`(0~1)·`weight_note`(문자열)로 positions.json에 기록 (백엔드 참고값)
- **ATH 계산**: `fetch_live.py`·`fetch_eod.py`의 ATH(`ath`, `prev_high`) 산출 시 `auto_adjust=False` 사용. 배당 조정을 제거한 원본 종가 기준. `auto_adjust=True`(배당 조정)는 상대 비교(MA·수익률)에만 사용
- **관심종목 탭 추천 비중 (프론트 동적 계산)**: 진입 임박(WATCH+steps≥5+score≥75) 및 ENTRY_x 종목을 active로 간주(그 외 WATCH=0%). base 가중치: 진입 임박=50 / ENTRY_1=30 / ENTRY_2=70 / ENTRY_3=90 / TRIM=45. 종합점수(toppick_score 50% + steps/6×100 50%) 비례 정규화. 마삼 모드별 주식 한도: BULL 100% / NORMAL 90% / CRISIS 80% / PANIC 70%. 현금 카드 = 100% - 합산. 종목 추가·삭제 시 즉시 재계산
- **6단계 충족(steps/stepsList)**: 배치 실행마다 `calc_criteria_count()`가 자동 재계산 → positions.json 갱신
- **로고**: Google Favicon API (`t2.gstatic.com/faviconV2`)
- **한국어 종목명**: 네이버 금융 API — `.O`→`.K`→접미사 없음 순 fallback

### 7-9. 미구현 / 다음 작업 예정

- **마삼 `panic_hold` 연결**: masam.json에 필드 존재하나 fetch_eod.py 미연결. 공황 후 올인 집행 신호 입력(UI) + 전고점 경신 자동 감지 → 홀드 해제 로직 필요

---

## 8. JSON 산출물 스키마

| 파일 | 내용 | 전략 |
|---|---|---|
| `masam.json` | 3-모드 상태·비중·헤지·트리거 거리·올인 체크리스트·알림 | A |
| `mcap_daily.json` | 큐레이트 리스트 mcap·1등주 판정·격차·역전 | A |
| `hedge_prices.json` | TLT·IAU·GLD·TIP 일봉 | A |
| `masam_market.json` | 금리환경·QE·10Y 추세·연준총자산(T)·DFF등락·나스닥시장심리·(표시)VIX·F&G·환율 | A |
| `positions.json` | 모멘텀 포지션(상태·평단·비중·트랜치·스탑·수평지지·쿨다운) | B |
| `indicators.json` | 종목별 MA50/200·ATR·atrPct·recentHigh·수평지지 | B |
| `actions.json` | 엔진 출력 액션(HOLD/BUY_1~3/TRIM_HALF/EXIT) | B |
| `transitions.json` | append-only 상태 전이 기록 | B |
| `momentum_market.json` | 국면 GREEN/YELLOW/RED·SPX·NDX 추세·매수 게이트 | B |
| `params.json` | 전략별 파라미터 · 부록 Z 옵션 토글 상태 | 공통 |
| `live.json` | 준실시간 표시값(현재가·등락률·거리·헤지 시세) — 표시 전용 | 공통 |

### masam.json 핵심 필드

```json
{
  "as_of": "YYYY-MM-DD",
  "mode": "NORMAL | CRISIS | PANIC",
  "rate_env": "ZERO | NON_ZERO",
  "qe_active": false,
  "treasury_10y_trend": "DOWN | UP | UNKNOWN",
  "masam": { "month_count": 0, "last_masam_date": null,
    "crisis_end_dday": null, "panic_end_dday": null },
  "leader_status": { "rank1_ticker": "NVDA", "rank2_ticker": "MSFT",
    "gap_pct": 0, "overtake_detected": false, "gap_within_10pct": false },
  "target_allocation": { "stock_pct": 0, "hedge_pct": 0, "cash_pct": 0, "label": "" },
  "hedge_allocation": { "type": "TLT | IAU_GLD_TIP | DOLLAR | NONE",
    "rationale": "비제로+QE_OFF / 10Y 하락추세 등", "exit_trigger": "" },
  "rebalancing": { "cash_raised_pct": 0, "max_pct": 25, "qqq_pct": 0 },
  "staking": { "rate_env": "NON_ZERO", "grid_pct": 5, "target_pct": 50, "deployed_pct": 0 },
  "all_in_conditions": [
    { "id": 1, "label": "한달+1일 무마삼", "met": false, "grade": "약", "detail": "D-12" },
    { "id": 2, "label": "8거래일 연속 상승", "met": false, "grade": "중" },
    { "id": 3, "label": "1등주 전고 돌파", "met": false, "grade": "강" },
    { "id": 4, "label": "나스닥 전고 돌파", "met": false, "grade": "강" },
    { "id": 5, "label": "2구간 V자(+10%/+5%)", "met": false, "grade": "중" },
    { "id": 6, "label": "긴급 올인(-30%/-15%)", "met": false, "grade": "강" }
  ],
  "additional_buy": { "target": "rank1 | QQQ", "rsi14": 0, "mfi14": 0, "both_below_50": false },
  "panic_hold": { "active": false, "until_new_high": true },
  "panic_reentry": { "stage": 0, "tranches": [35, 35, 30] },
  "recommended_action": "",
  "alerts": []
}
```

### masam_market.json 핵심 필드

```json
{
  "as_of": "YYYY-MM-DD",
  "rate_env": "ZERO | NON_ZERO",
  "dff": 3.63,
  "dff_change_text": "인상 | 인하 | 동결",
  "dff_trend": "UP | DOWN | UNKNOWN",
  "qe_active": true,
  "walcl_trend": "UP | DOWN | UNKNOWN",
  "walcl_trillion": 6.74,
  "treasury_10y": 4.49,
  "treasury_10y_trend": "UP | DOWN | UNKNOWN",
  "market_sentiment": "위험선호 | 중립 | 위험회피",
  "spy_ma200_label": "MA200 (+17.7%)",
  "vix": 16.4,
  "fear_greed": 62,
  "usd_krw": 1315.5
}
```
- `dff_change_text`: DFF 22거래일 전 대비 ±4bp 초과 시 인상/인하, 이하 동결 (fetch_fred.py)
- `walcl_trillion`: WALCL 최신값 ÷ 1,000,000 (단위: 조 달러) (fetch_fred.py)
- `market_sentiment` / `spy_ma200_label`: NDX vs MA200 기준, ±2% 임계 (fetch_eod.py)
- `dff_trend` / `treasury_10y_trend`: 20일 기울기, ±20bp 임계 (fetch_fred.py)

### positions.json 핵심 필드 (모멘텀)

```json
{
  "as_of": "YYYY-MM-DD",
  "regime": "GREEN | YELLOW | RED",
  "items": [{
    "symbol": "NVDA",
    "status": "WATCH | ENTRY_1 | ENTRY_2 | ENTRY_3 | TRIM | EXIT | REMOVED",
    "toppick_score": 91,
    "avg_price": null, "weight": 0, "deployed_tranches": [1, 2],
    "recent_high": 0, "trailing_stop_line": 0, "horizontal_support": 0,
    "cooldown_until": null,
    "metrics": { "price": 0, "ma50": 0, "ma200": 0, "atr14": 0, "atr_pct": 0,
      "gap50_pct": 0, "dist_to_stop_pct": 0,
      "vol20ma": 0, "vol_ratio": 0 },
    "next_action": "HOLD | BUY_1 | BUY_2 | BUY_3 | TRIM_HALF | EXIT",
    "reason": "",
    "weight": 0.7,
    "weight_note": "과열 구간 (MA50 +55%) — 일부 현금화 검토"
  }]
}
```

---

## 9. UX / IA (기준: `ux-ui_mockup_v2.html`)

### 9-1. 디자인 시스템

```css
--bg:#17171C; --bg-deep:#0E0E12;
--surface:#202027; --surface-2:#26262E; --surface-3:#2C2C35; --line:#2A2A31;
--txt:#F4F5F7; --txt-2:#9A9AA3; --txt-3:#6B6B73;
--up:#F04452;   /* 상승 = 빨강(한국 관례) */
--down:#4593FC; /* 하락 = 파랑 */
--blue:#3182F6; --teal:#2BC4B6; --green:#2BC4B6; --purple:#8B5CF6; --amber:#F7A93B;
/* 그라데이션 액센트(AI/모멘텀 강조): linear-gradient(110deg,#6d5efc,#3182F6 55%,#8b5cf6) */
```
- 모바일 폭 390px, 다크. 폰트 Pretendard Variable(500/600/700/800). 카드 radius ~16px, 좌우 패딩 17px. 아이콘 Iconify(bxs/heroicons) + twemoji(국기·이모지).

### 9-2. 앱 셸 · IA

- 상단 전략 토글 `[마삼룰] [모멘텀]`(선택 상태 영구 저장). 하단 4-탭:
  - 마삼룰: **발견(현재 상태)** · **관심(시가총액 순위)** · 경제지표 · 설정
  - 모멘텀: **탑픽(종목 선정)** · **관심종목(보유·줍줍)** · 경제지표 · 설정
  - 뒤 2칸(경제지표·설정)은 슬롯 공유, **내용은 모드별로 교체**(시장 화면 전략별 분리).
- 면책 Footer 상시 노출(어느 화면에서도 숨김 금지): "⚠️ 투자 권유 아님 · 실거래 전 백테스트 검증".
- 토스증권 보유현황 모방 화면(`증권`)은 보조 화면으로 유지.

### 9-3. 마삼룰 화면

| 화면 | 내용 |
|---|---|
| 발견(현재 상태) | 지수 롤(나스닥/S&P/다우) · 국면칩(리밸런싱/말뚝박기/V자반등/올인/마삼해제) · 모드 배지(NORMAL/CRISIS/PANIC) + 이번 달 마삼 N회·해제 D-day · 나스닥 최고점 대비 %·최근 마삼일 · 목표 비중 배너 · **1등주 주가 구간**(드롭다운 1등주/QQQ · 탭 최고점/직전고점/직접입력 · -25%/-50% · 말뚝 구간 테이블) |
| 관심(시가총액 순위) | 큐레이트 글로벌 시총 순위(1등주 트로피·**1등주 대비 격차%**) · 롤(환율/VIX/공포탐욕) |
| 경제지표(시장환경·표시) | 금리환경·DFF(전월 인상/인하/동결)·연준총자산($xT·QE)·**10Y 추세**·**나스닥 시장심리(NDX vs MA200)**·**✦ 헤지 권장 배너(슬라이드)** · 추가 자금(RSI14/MFI14, 1등주/QQQ 토글) · **올인 체크리스트 6종** · (표시)Fear&Greed·VIX |
| 설정 | 리밸런싱 한도(25%/50%) · **부록 Z 옵션 토글**(충돌 옵션 경고 배너) |

PANIC 완전 홀드 시 배너: "공황 올인 — 최고점 경신까지 리밸런싱·말뚝 중단".

### 9-4. 모멘텀 화면 (신규 — 탑픽 스펙으로 재설계, 셸·토큰 유지)

| 화면 | 내용 |
|---|---|
| 탑픽(종목 선정) | 필터칩(전체/매수 후보/보유/매도 신호) · 종목 카드(6단계 인디케이터 도트 · 상태 배지 · 하트) · **카드 클릭 → 6단계 드로어**(펀더멘털/실적전망/MA50이격/거래량 4컬럼 + 단계별 pass/fail 행, 스와이프 닫기) |
| 관심종목(보유·줍줍) | **단일 리스트**(보유현황/매도신호 탭 분리 없음) · 카드 클릭 → 동일 드로어 · 현금 비중 카드 · `weight` 자동 표시 |
| 경제지표(모멘텀 국면) | **국면 GREEN/YELLOW/RED** 배지(SPX·NDX vs MA200/MA50) · 매수 게이트 상태(허용/보수/차단) · (표시)VIX·F&G·PMI 참고 |
| 설정 | 줍줍 비중 방식·50MA 지지 범위·트레일링(고정/ATR/혼합·%·승수·절반축소)·추세이탈 매도·탑픽 임계·재선정·동시추적·국면 지수·어닝·실행 모드 (preset 선택 기본) |

> 시그널 배지 색: 매수 강도/방어를 `--up`(적극)·`--amber`(매수)·`--teal`(보유)·`--down`(매도)로. RED 국면 시 매수 배지는 정보성(비활성).

---

## 10. 구현 단계 (Phase)

| Phase | 내용 | 체크 |
|---|---|---|
| **0 데이터 PoC** | ① ^IXIC 마삼·달력월 카운트·금리환경·전고점 ② 큐레이트 mcap 1위(yfinance) + DGS10 추세 헤지 ③ 모멘텀: 탑픽 펀더 입력·MA50/200·ATR·**수평지지 자동검출**·GREEN/YELLOW/RED·트레일링 ④ **준실시간 표시 PoC**(공개 repo 장중 cron 주기·지터, 무료 지연시세 소스) | [ ] |
| **1 엔진** | 마삼 3-모드 상태머신 + 모멘텀 상태머신(3분할/트레일링) + 백테스트(익일 시가·사이징) | [ ] |
| **2 백엔드** | EOD + 장중 live 배치(공개 repo) + state/position persistence + 저장 | [ ] |
| **3 모바일 UI** | 전략 토글 + 마삼 화면 + 모멘텀 화면(탑픽 재설계) + 전략별 시장 화면 + 면책 Footer | [ ] |
| **4 알림/설정** | Web Push(잠정/근접 라벨 포함) + 파라미터·부록 Z 토글·펀더 입력 | [ ] |
| **5 검증/최적화** | 모멘텀 워크포워드 + 마삼 룰/옵션 백테스트 | [ ] |

---

## 11. 구현 제약 (반드시 준수)

### 룰북 무결성
- 엔진 규칙의 정답은 두 매뉴얼. 코드는 매뉴얼대로 구현, 임의 변경·단순화 금지.
- 부록 Z·preset은 `params.json` 토글로만 활성화(기본 원본). 원본 충돌 옵션 ON 시 경고 배너.

### 데이터 정확성
- 마삼 기준 `^IXIC` 단일. 수정주가 필수. 이상치 자동 폐기 금지(검수 플래그).
- **판정용 = EOD 고정. live.json은 표시값만.** 장중 값으로 신호 발동 금지.

### 비용·인프라
- 서버리스 유지(런타임 API 서버 금지). PWA는 자기 정적 JSON만 fetch.
- **무료 전제 = 공개 repo**(Actions 무료). 무료 한도 초과 소스 금지.

### 면책
- 면책 Footer는 전 화면 상시 노출. "투자 추천/수익 보장" 류 문구 금지.

### 백테스트
- 시그널 = 종가 산출 → **익일 시가 체결**(look-ahead 방지). point-in-time 유니버스. 사이징(fixed-fractional/ATR). 슬리피지·갭·결측 처리(명세서 14·15장).

---

## 12. 워크플로우 오케스트레이션

- **플랜 모드 기본**: 3단계 이상/아키텍처 결정은 플랜 모드. 틀어지면 즉시 STOP·재계획.
- **서브에이전트**: 리서치·탐색·병렬 분석 위임(하나당 1작업), 메인 컨텍스트 보존.
- **자기개선 루프**: 사용자 수정마다 이 CLAUDE.md에 패턴 반영. 세션 시작 시 검토.
- **완료 전 검증**: 작동 증명 없이 완료 표시 금지. "시니어가 승인할까?"

## 13. 태스크 관리

1. 계획 우선(체크 가능 항목) → 2. 구현 전 사용자 확인 → 3. 진행 추적 → 4. 단계별 고수준 요약 → 5. 수정 후 CLAUDE.md 갱신.

## 14. 핵심 원칙

- 단순함 우선 / 게으름 금지(근본 원인) / 최소 영향 / **룰북 우선**(엔진 로직은 매뉴얼이 정답).

## 15. 소프트웨어 구축 워크플로우 (7단계)

참고: https://github.com/obra/superpowers.git
1. brainstorming → 2. using-git-worktrees → 3. writing-plans(2~5분 태스크) → 4. subagent-driven/executing(2단계 리뷰) → 5. test-driven(RED-GREEN-REFACTOR) → 6. requesting-code-review(Critical 차단) → 7. finishing-a-development-branch.

## 16. 디자인 가이드

1. **스케치 먼저**: `ux-ui_mockup_v2.html` 구조·토큰을 기준. 변경 전 승인.
2. 스크린샷 첨부 시 해당 스타일 따름.
3. §9 디자인 시스템(색·폰트·radius) 엄수. 변형 시 승인.
4. 빌드 전 폰트(Pretendard)·아이콘(Iconify/SVG) 확인.
5. UI 코드 작성 전 frontend-design 스킬/추론 엔진 실행(ui-ux-pro-max-skill).
6. **모멘텀 화면은 새 탑픽 스펙으로 재설계**(셸·토큰 유지). HTML의 모멘텀 수치는 임시값이었음.
