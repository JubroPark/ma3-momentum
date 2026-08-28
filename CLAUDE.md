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
| FRED `DFF`·`DGS10`·`WALCL` | FRED API | 금리환경·10Y 추세·QE 판정 | 코어 (헤지 완전자동, 마삼룰 판정용 — critical) |
| FRED `DGS30`·`WRESBAL`·`DTWEXBGS`·`T5YIFR`·`TREAST`·`THREEFYTP10` | FRED API | 경제지표 탭 [일간]/[주간] 매크로 대시보드 | 표시 전용(2026-08-21 추가, §9-5 참고). 실패해도 배치 안 죽음(non-critical) |
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
>
> **live.yml 크론이 서머타임 기준으로만 짜여있던 버그 (2026-07-28 수정)**: 미 정규장은 EDT(서머타임) 13:30~20:00 UTC / EST(비서머타임) 14:30~21:00 UTC로 매년 두 번 바뀌는데, 크론은 EDT만 가정해 13:00~20:15 UTC로 고정돼 있었음 → 겨울철엔 장마감 직전 45분(20:15~21:00 UTC)을 못 잡음. 13:00~21:15 UTC 전체로 확장해 양쪽 다 커버(장외 시간에 도는 여분의 실행은 무해 — 프론트가 정규장 시간 가드로 걸러냄).
>
> **워크플로우 push 재시도 (2026-07-28 추가)**: eod/live/universe.yml 모두 `git pull --rebase && git push`를 재시도 없이 한 번만 시도해서, 수동 dispatch나 `universe.yml` 종료 후 자동 재트리거되는 `eod.yml`이 다른 push와 타이밍이 겹치면 그대로 실패하던 문제. 세 워크플로우 모두 push 실패 시 최대 5회(5·10·15·20·25초 백오프) 재시도하도록 수정. (크론 스케줄 자체는 서로 안 겹침 — live 21:15 UTC 종료 후 EOD 22:00 시작 45분 여유, EOD는 보통 수 분 내 종료 후 23:00 유니버스 시작. 충돌은 스케줄이 아니라 ad-hoc 수동 트리거·자동 재트리거에서 발생.)
>
> **yfinance 일시 장애 가드 (2026-07-25 확인)**: `fetch_eod.py` 수동 실행 중 yfinance가 일시적으로 IXIC·1등주·QQQ·헤지 가격 전부 NaN을 반환한 사고 발생 → `NaN`은 JSON 스펙상 무효라 브라우저 `JSON.parse`가 실패, 앱 로딩이 깨질 뻔함. `require_valid()` 가드를 추가해 핵심 가격이 NaN이면 파일 저장 전에 배치를 즉시 중단(기존 데이터 보존)하도록 함. 재시도 시 정상 데이터로 성공 — 같은 코드로도 실행 시점에 따라 yfinance가 일시적으로 실패할 수 있음을 감안할 것.
>
> **1등주 교체(오버테이크) 후유증 (2026-07-28 확인 · 2026-07-31 원인 정정)**: 리더가 바뀌어도 자동으로 안 따라가는 필드가 있음.
> 1. **핵심 원칙 (2026-07-31 확정): 종목의 올인 진입가·직전 고점·스티키 저점은 "슬롯"(1등주/2등주)이 아니라 "티커 그 자체"에 귀속되며, 랭크가 바뀌어도(1등↔2등) 리셋하지 말고 그대로 이어가야 한다.** `_prev_high()`가 공유 `date`("2026-07-06") 이후 **현재 슬롯 점유 티커의 전체 종가 히스토리**를 매 배치 재계산하기 때문에 `nvda_prev_high`/`rank2_prev_high`는 원래도 랭크 이동과 무관하게 자동으로 맞게 나온다 — 문제는 오직 진입가(`last_allin_price.{nvda,qqq,rank2}`)와 `rebalancing.*_lowest_close`를 랭크 교체 시점에 **수동으로 "당일 종가로 리셋"** 해온 관행이었음. 이 리셋이 바로 버그의 원인: 2026-07-28에 AAPL이 1등으로 올라서면서 운영자가 `last_allin_price.nvda`를 AAPL의 진짜 진입가(312.66, 07-06)가 아니라 그날 종가(336.91)로 새로 리셋 → AAPL의 원래 연속 이력을 버림. NVDA가 2등으로 내려왔을 때도 처음엔 같은 실수로 `rank2`를 새 값(196.51)으로 리셋했다가, 사용자 확인 후 NVDA의 진짜 연속 이력(07-06 진입 195.55 / 이후 최고 212.50)으로 재정정. 같은 원칙으로 `nvda`(1등주) 슬롯도 AAPL의 진짜 연속 진입가(312.66)로 재정정 완료.
> 1-1. **저점 스티키는 "전고점 갱신 시 리셋" 필요 (2026-07-31 추가 확인)**: `nvda_lowest_close`를 07-06 이후 전체 최저 종가(310.66, 07-07)로 되돌렸더니 "직전 고점"(340.08, 07-28 경신) 탭에서 curZone이 3으로 잘못 튀는 버그가 드러남 — 310.66은 340.08이라는 전고점이 세워지기도 **전**의 저점이라, "전고점 대비 하락"과는 무관한 값인데도 같은 그리드 계산에 섞여 들어갔기 때문. `_prev_high()`는 전고점을 매일 자동 갱신(랭크 이동과 무관하게 정상)하지만 저점 스티키는 "막바지 2구간 상승 → 전량 재매수"일 때만 리셋했고 전고점이 새로 갱신될 때는 리셋하지 않아서 생긴 불일치. `fetch_eod.py`에 "오늘 전고점을 새로 경신했으면 저점도 그날 종가로 함께 리셋" 조건을 추가(`_nvda_new_peak`/`_qqq_new_peak`/`_rank2_new_peak`)해 해결 — `nvda_lowest_close`는 07-28(전고점 갱신일) 이후 최저인 333.43으로 재정정. **주의**: 이 리셋은 "직전 고점" 탭 기준으로는 항상 맞지만, "올인 지점"(고정된 최초 진입가) 탭 기준으로 볼 땐 전고점 갱신 이전의 하락폭 정보가 사라짐 — 원칙상 두 탭은 서로 다른 저점 이력이 필요한 게 근본 해법이나, 사용자가 신고점 경신 이후엔 항상 "직전 고점" 탭만 본다고 확인했으므로(§9-5) 우선순위상 직전 고점 기준으로 맞춤.
> 2. 장중 라이브 배치(`live.yml`)는 시장시간(UTC 13:00~20:15) 안에만 돌기 때문에, EOD 배치가 장 마감 후~다음 라이브 배치 사이에 리더를 바꾸면 그 사이 `live.json`의 `rank1`/`rank2` 슬롯에 구 리더 시세가 남아 프론트에서 "이름은 새 리더, 가격은 구 리더" 불일치가 생김. 다음 라이브 배치가 돌면 자동 정정 — 급하면 `gh workflow run "장중 준실시간 배치"`로 수동 트리거.
> 3. **2등주(`rank2`) 스티키 저점 미구현 (2026-07-31 수정)**: `rebalancing.rank2_lowest_close`가 아예 계산되지 않고 있었음(1·2등주 필드만 챙기고 rank2는 프론트·백엔드 양쪽에서 스킵) → `fetch_eod.py`·`app.html` 양쪽에 rank2 스티키 저점 계산 추가로 수정.
> 4. **향후 리더 교체 시 주의**: 슬롯 재배정 시 진입가·저점을 "당일 종가로 리셋"하지 말 것. 원칙적으로는 `last_allin_price`를 티커 심볼로 keying해서 슬롯과 무관하게 추적하는 게 근본 해법이지만 아직 미구현 — 당장은 리더 교체 발견 시 git 히스토리로 해당 티커가 최초로 그 슬롯에 들어온 날짜를 특정하고, `date`(07-06) 이후 그 티커 자체의 전체 종가 히스토리에서 진입가·최고가·최저가를 다시 뽑아 수동 패치할 것(리셋 금지).
>
> **나스닥 시세 조회 실패 시 0 폴백 버그 (2026-07-28 수정)**: `fetch_live.py`가 `^IXIC` 조회에 실패하면 `ixic_price`를 0으로 대체해 `from_ath_pct`가 `(0-ATH)/ATH*100 = -100%`로 잘못 계산되던 버그. 화면에 쓰이는 `nasdaq.price`와 동일하게 캐시된 값으로 폴백하도록 수정.
>
> **FRED API 타임아웃 (2026-07-28 수정)**: `fetch_fred.py` timeout 10s→20s + 실패 시 최대 3회 재시도(1s/2s 백오프) — EOD 배치가 FRED 응답 지연으로 통째로 실패하던 문제 완화.
>
> **by_ticker 구조 도입 완료 (2026-08-01) — 위 4번 항목 슈퍼시드**: `last_allin_price.by_ticker[티커]`로 진입가/직전고점/저점을 티커 심볼 자체에 귀속해 추적하는 구조 구현 완료(`_update_ticker()`). 랭크가 바뀌어도(1등↔2등, 랭크 밖으로 밀려남 포함) 해당 티커가 매일 갱신 대상에서 빠질 뿐 데이터는 그대로 보존되고, 다시 랭크에 들어오면 이어서 갱신됨 — "수동 패치" 대응은 더 이상 기본 대응이 아니며, by_ticker 자체가 깨진 경우에만 예외적으로 필요.
>
> **재매수 리셋이 "구간 번호" 비교라 부정확했던 버그 (2026-08-04 수정)**: `zone_idx()`가 "zone1 문턱만 넘으면 전부 0구간"으로 뭉뚱그려서, 예를 들어 직전고점 $212.5·저점 2구간($190.01)에서 종가가 $206.64로 반등해도(0구간 문턱 $201.88은 넘었지만 기준가 $212.5 자체엔 못 미침) "2구간 상승"으로 오판해 저점 스티키가 리셋되던 문제. 리셋 판정을 구간 번호(`new_zone <= prev_zone-2`) 대신 **목표 구간에 적힌 실제 가격**(`base*(1-step*(prev_zone-2))`) 도달 여부로 변경. `scripts/test_zone_reach.py`에 이 경계 사례 회귀 테스트 있음.
>
> **재매수 리셋 그리드를 티커별 독립으로 (2026-08-04)**: 기존엔 `rebalancing.max_pct` 단일값으로 전 종목의 리셋을 판정해서, 프론트에서 종목마다 다른 그리드(-25%/-50%)로 보고 있어도 서버 판정은 항상 하나의 그리드만 썼음. `rebalancing.max_pct_by_ticker`(티커 키)로 분리, 신규 티커 기본값은 프론트(`initMaxPctUI`)와 동일하게 금리환경 기반(제로=25%/비제로=50%).
> **⚠️ 화면 그리드 토글 = 서버 설정 (확정 규칙, 2026-08-04)**: `max_pct_by_ticker`는 서버 값과 프론트 localStorage(`max_pct_{target}`)가 별개로 존재해서 자동 동기화가 안 됨(정적 사이트라 클라이언트→서버 write-back 채널이 없음) — 사용자가 화면에서 -25%/-50%를 토글하면 그게 곧 "진짜" 설정이고, `masam.json`의 `max_pct_by_ticker[티커]`를 그에 맞춰 수동으로 같이 바꿔야 함(안 그러면 서버가 다른 그리드로 리셋을 판정해 화면과 어긋남 — 실사용 중 QQQ에서 두 번 발생 확인). 사용자가 그리드를 바꾸거나 "왜 리셋이 안 됐지" 라고 물으면 먼저 프론트 localStorage 값과 `max_pct_by_ticker`가 일치하는지부터 확인할 것.
>
> **2등주 권장 비중 배분에 실제 1등 이력 조건 추가 (2026-08-04)**: `gap_within_10pct`(격차 10% 이내)만으로 1:1 배분 대상이 되면, 한 번도 1등을 탈환한 적 없는 종목(예: GOOGL이 NVDA와 격차만 좁혀진 경우)까지 잡히는 문제. `by_ticker[티커].ever_rank1`(오늘 1등인 티커에 마킹)을 `leader_status.rank2_ever_rank1`으로 노출, 프론트 `dualLeader` 판정을 `overtake_detected || (gap_within_10pct && rank2_ever_rank1)`로 변경.
>
> **`ever_rank1`은 영구 마킹이 아니라 "격차 10% 이내 유지 중"에 한정 (2026-08-27 수정)**: 위 마킹을 최초엔 한 번 True가 되면 영구 유지했는데, 사용자 확인 결과 "1·2등 격차 10% 이내 → 1:1 배분"은 **역전 직후**에만 유효한 규칙이고, 격차가 다시 10%를 넘어서면 그 2등주의 "1등 해본 적 있음" 이력은 리셋되어야 함(안 그러면 예전에 잠깐 1등이었던 종목이 한참 뒤 격차만 우연히 10% 이내로 좁혀져도, 실제 역전 없이 1:1 배분에 다시 잡히는 오류가 생김). `fetch_eod.py`에서 매 배치 `gap_pct > 10.0`이면 `rank2_entry["ever_rank1"] = False`로 리셋하도록 수정. `test_zone_reach.py::test_ever_rank1_resets_when_gap_exceeds_10pct`에 회귀 테스트 있음.
> **소급 정정 필요했음 (2026-08-27)**: 8/20~8/26 사이 NVDA-AAPL 격차가 10.3~13.5%로 여러 번 10%를 넘었는데, 그 기간 배치들은 전부 위 리셋 로직 배포 전(구 코드)이라 AAPL의 `ever_rank1`이 리셋되지 못하고 True로 계속 남아있었음. 코드 배포 직후에도 마침 격차가 이미 9.9%로 좁혀진 뒤라 리셋 조건(`gap_pct > 10.0`)이 발동할 기회가 없어 오염값이 소급 정정되지 않음 → `masam.json`의 `last_allin_price.by_ticker.AAPL.ever_rank1`과 `leader_status.rank2_ever_rank1`을 수동으로 `false`로 1회성 정정. **교훈**: 리셋/정정 로직을 새로 배포할 때, 배포 시점에 조건이 우연히 거짓이라 로직이 즉시 발동하지 않으면 과거에 누적된 오염 상태는 저절로 안 고쳐진다 — 배포 후 "지금 조건이 참인가"뿐 아니라 "과거 이력 중 조건이 참이었던 적이 있었는데 소급 미반영된 상태인가"도 같이 확인할 것.
>
> **live.json에 유효하지 않은 NaN 값이 저장돼 앱이 통째로 안 뜬 사고 (2026-08-04)**: `fetch_live.py`의 `fetch_mcap_live()`가 일부 티커(예: 2222.SR 사우디 아람코)에서 `price`/`prev_close`가 NaN이어도 그대로 `change_pct`에 담아 저장 → Python `json.dumps`는 NaN을 비표준 `NaN` 토큰으로 그대로 씀 → 브라우저 `JSON.parse`가 통째로 실패해 `initFromData()`가 죽고 **더미(플레이스홀더) 데이터만 화면에 남는데 티도 안 남**. `save_json()`에 재귀적으로 NaN/Infinity를 `null`로 치환하는 `_sanitize_nan()` 안전장치 추가(어떤 필드에서 NaN이 나와도 방어). "새로고침해도 똑같다"는 증상이면 이 클래스의 버그(파일 자체가 깨져서 매번 파싱 실패)를 의심할 것 — PWA 캐시 문제와 헷갈리기 쉬움.
>
> **데이터 로딩 실패가 조용히 은닉되던 문제 (2026-08-04 수정)**: 위 NaN 사고처럼 `initFromData()`가 어떤 이유로든 실패하면 `catch(e){ console.error(...) }`만 하고 사용자에게는 아무 표시가 없어서, 하드코딩된 플레이스홀더 값(기준일 "2025.06.14" 등 `app.html`에 데모용으로 박혀있는 값)이 진짜 데이터인 것처럼 그대로 남아있었음. 실패 시 상단에 빨간 배너("데이터를 불러오지 못했습니다")와 캐시·서비스워커까지 초기화하는 "새로고침" 버튼을 표시하도록 수정.
>
> **PWA 앱 셸이 예전 빌드로 고착돼 새로고침해도 안 바뀌던 문제 (2026-08-04 수정)**: `next.config.mjs`의 `withPWAInit({ runtimeCaching: [...] })`에 `/data/*.json` 규칙만 있고 `app.html`(문서) 자체엔 런타임 캐싱 규칙이 없어서, 빌드 시점에 precache된 옛 `app.html`이 계속 서빙됨(정상적인 새로고침으로는 갱신 안 됨 — 서비스워커가 새로 활성화돼야 하는데 그 트리거가 없었음). `app.html`을 precache `exclude`에 추가하고 NetworkFirst(5초 타임아웃) 런타임 규칙 추가.
>
> **`_sanitize_nan()`이 모멘텀 파이프라인엔 이식이 안 돼 있던 사고 (2026-08-13)**: 위 2026-08-04 NaN 사고 때 안전장치를 `fetch_live.py`에만 추가하고 `fetch_momentum.py`(`indicators.json`/`positions.json` 생성)엔 빠뜨림 → SCCO의 `atr14`/`atr_pct`가 (아마 데이터 결측일로) NaN이 되면서 `calc_atr14()`가 예외 없이 조용히 NaN을 전파, 그대로 저장돼 앱이 통째로 안 뜸. `fetch_momentum.py`에도 동일한 `_sanitize_nan()` 추가 + `calc_atr14()`가 NaN true range를 애초에 평균 계산에 안 섞도록 필터링. **NaN 안전장치는 JSON을 저장하는 배치 스크립트 전부(현재 `fetch_eod.py`/`fetch_live.py`/`fetch_momentum.py`)에 동일하게 있어야 함 — 스크립트 하나 새로 추가하거나 리팩터링할 때 빠뜨리기 쉬우니 체크할 것.**
>
> **장중 배치가 24시간+ 계속 크래시하며 전 종목 가격이 null로 굳어진 사고 (2026-08-18)**: 두 버그가 겹침. (1) `fetch_quote()`가 `period="2d"`(달력일 기준)로 조회했는데, 데이터 소스에 하루 공백(2026-08-17)이 끼면서 실제 거래일 2개를 못 채워 매번 조회 실패로 처리됨 → `period="5d"`로 넉넉히 받아 마지막 2개 실제 거래일 행을 쓰도록 수정. (2) 조회 실패 시 `existing_live.get("nasdaq", {}).get("price", 0)`로 직전 값에 폴백하는데, `.get(key, default)`의 `default`는 키가 "없을 때"만 적용되고 **이미 null로 저장된 값이 있으면 그 null을 그대로 돌려줌** — 그 `None`이 `from_ath_pct` 계산 뺄셈에 그대로 들어가 `TypeError`로 스크립트 전체가 죽는 자기영속 크래시로 이어짐(한번 null이 저장되면 다음 실행도 크래시 → 영영 회복 불가). 폴백을 `.get(key) or 0` 패턴으로 바꾸고 산술 연산 직전에도 None 가드 추가. **"이전 값으로 폴백" 코드에 `.get(key, default)`를 쓸 땐, 그 값이 이미 `None`으로 저장돼 있을 수 있다는 걸 항상 의심할 것 — `default`는 키 부재에만 적용되고 저장된 `None`엔 안 먹힘.**

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
| `notifications.json` | 알림 히스토리(마삼 모드 전환·시총 순위 역전), 최근 30일 유지 — `fetch_eod.py`가 전일 대비 diff해서 append | A |

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
  "rebalancing": { "cash_raised_pct": 0, "max_pct": 25, "qqq_pct": 0, "nvda_lowest_close": 0, "qqq_lowest_close": 0 },
  "eod_close": { "nvda": 0, "qqq": 0, "rank2": 0 },
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
- **경제지표 매크로 대시보드 확장 필드 (2026-08-21 추가, §9-5 참고)**: `treasury_30y`·`treasury_30y_10y_spread`·`wresbal_trillion`·`dollar_index`·`inflation_expectation_5y5y`·`treast_trillion`·`term_premium_10y`(전부 표시 전용) + `qe_state`("QE_ON"/"LIQUIDITY_SUPPLY"/"QT"/"UNKNOWN", 표시 전용 — 마삼룰 헤지 판정용 `qe_active`와 별개) + `{지표}_chg_20d`/`{지표}_chg_4w`·`{지표}_chg_dir`(추세) + `{지표}_as_of`(기준일) + `history.{지표}`(60개 스파크라인용 배열)

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

### 9-5. PWA UX 구현 세부

**Pull-to-refresh**
- 스크롤 컨테이너: `body`(window)가 아닌 `.view.active .body` div(`overflow-y:auto`). `window.scrollY`는 항상 0이므로 사용 금지 → `getScroller().scrollTop === 0` 으로 판단.
- `touchstart`: scrollTop===0이면 startY 기록(active는 아직 false).
- `touchmove`: scrollTop!==0이면 즉시 비활성. dy>0(아래 드래그)일 때만 `active=true` + 인디케이터 높이 증가.
- `touchend`: THRESHOLD(80) 절반 이상이면 새로고침. 직전에 현재 뷰를 `sessionStorage('ptr_view')`에 저장.
- 새로고침 후 복원: `initFromData()` 완료 시점에 `sessionStorage('ptr_view')`를 읽어 `show(view)` 호출 후 즉시 삭제.
- 새로고침 버튼(`#refresh-btn`): 현재 `display:none`으로 숨김.

**시총 순위 실시간 보정 (renderMcapList) — (2026-07-28 보강)**
- `live.json`의 `as_of`(UTC)와 `mcap_daily.json`의 `as_of`를 날짜(10자리)로 비교
- `applyLive = (liveDate >= eodDate) && marketHoursNow` — 날짜만으로는 불충분함이 확인됨(아래 참고)
- **정규장 시간 가드 추가**: 뉴욕 현지시간(`America/New_York` 타임존, 09:30~16:00 ET) 기준으로 장중 여부 판단 — 서머타임(EDT/EST) 자동 반영되므로 UTC 고정 시각으로 하드코딩하지 말 것
- **버그 배경**: 장외(장 시작 전 등)에는 `mcap_live.change_pct`가 "새 움직임"이 아니라 이미 EOD 종가에 반영된 지난 세션의 등락률이 그대로 멈춰있는 값. 날짜 비교만으로는 이걸 걸러내지 못해(같은 날짜면 통과) EOD 종가 위에 그 등락률을 한 번 더 곱하는 이중 적용이 발생 → 시총이 실제보다 부풀려져 companiesmarketcap.com 등 레퍼런스와 어긋남. 정규장 시간대 가드를 추가해 장외에는 무조건 EOD 값 그대로 표시하도록 수정
- 등락률 뱃지(`%` 표시)에는 별도 라벨을 붙이지 않음(예: "전일 장마감" 시도했으나 행마다 반복되어 가독성 저하로 제거) — 시총 숫자에만 가드 적용, 뱃지는 항상 `mcap_live.change_pct` 원값 표시

**기준일(topbar) 날짜/시간 표시**
- 날짜: `masam.as_of`(EOD 배치 기준, 한국시간 기준 영업일) 사용
- 시간: `live.update_time`(KST 문자열) 사용
- `live.as_of`는 UTC 타임스탬프 → 날짜 표시에 사용 금지(UTC 기준 날짜가 KST와 다를 수 있음)

**권장 비중 배너 (_calcZone 헬퍼) — (2026-07-28 개편)**
- `renderRangeTable()` 내부의 `_calcZone(tgt)` 헬퍼로 1등주·2등주·QQQ 각각 독립 구간 계산 후 비율 합산. step은 `getMaxPct(tgt)`로 세 타겟 완전 독립 적용(과거엔 2등주가 1등주 설정을 공유하는 버그가 있었음)
- `leader_status.gap_within_10pct || overtake_detected`(매뉴얼 1장: 1·2등 시총 격차 10% 이내/역전) → 1등:2등 = 1:1로 리더 몫을 반씩 나눠 각자 구간 축소 계산. 아니면 1등주가 리더 몫 전체
- 배너 자체는 **1등주(+2등주 합산)/QQQ/현금만** 짧게 표시(overflow 방지) — 탭하면 `openAllocDetail()`이 하단 드로어(`#alloc-overlay`/`#alloc-drawer`)를 열어 로고·티커·정확한 개별 %·비중 막대바를 표시. 상세 데이터는 `window._allocDetail`에 스테이징
- `rangeBase`는 live 로드 시 현재 `rangeTarget` 기준으로 자동전환(직전 고점/올인 지점). (2026-08-06 수정) 배너의 `_calcZone(tgt)`는 이 전역 `rangeBase`를 쓰지 않고 타겟별로 `autoBaseFor(tgt)`를 독립적으로 다시 불러씀 — 예전엔 전역값을 공유해서 QQQ 탭에서 직전고점⇄올인지점을 수동으로 바꾸면 1등주 배너 %까지 같이 흔들리는 버그가 있었음(아래 "직전 고점/올인 지점 자동전환" 참고)

**직전 고점/올인 지점 자동전환 (2026-08-10 재수정 — `prev_high > allin` 비교로 원복)**
- `autoBaseFor(target)`: `masam.last_allin_price.by_ticker[티커].prev_high > allin`이면 "직전 고점" 탭, 아니면 "올인 지점" 탭.
- **비교 기준을 두 번 오갔음. 결론: `prev_high > allin`이 맞고, `eod_close > allin`은 틀렸다.**
  - 원래(~2026-08-04) `prev_high > allin`로 비교했는데, `prev_high`는 재매수 이후에도 재매수 이전 옛 전고점을 계속 반영해서(아래 `since` 리셋 누락 버그) 재매수 직후에도 이미 참이 되어버려 "자동전환이 사실상 항상 직전고점"으로 무력화된 것처럼 보였음
  - 그래서 2026-08-06에 `eod_close(오늘 종가) > allin`으로 바꿨는데, 이러면 "신고점을 찍고 종가가 다시 눌리는" 흔한 케이스에서 직전 고점을 계속 봐야 하는데도 올인 지점으로 되돌아가버리는 **다른** 버그가 생김(2026-08-10, NVDA: allin 219.22 / 직전고점 223.96 / 종가 217.55에서 재현·확인)
  - 진짜 원인은 비교 기준이 아니라 `fetch_eod.py`가 `reached_recovery`(재매수) 시 `entry["allin"]`만 리셋하고 `entry["since"]`(직전고점 계산 시작일)는 안 건드린 것이었음 → 아래 "리밸런싱 스티키 구간"의 `since` 리셋 항목 참고. 이걸 고치면 재매수 직후 `prev_high`가 `allin`과 함께 리셋돼 자동전환이 다시 "올인 지점"부터 정상 시작하므로, `prev_high > allin` 비교로 되돌려도 두 문제 모두 해결됨
- `applyAutoTab(target)`가 `initFromData()`(최초 로드)와 `selectRange(target)`(타겟 전환 시마다) 양쪽에서 호출되도록 함 — 예전엔 최초 로드 1회만 평가하고 이후 타겟을 바꿔도 재평가가 안 됐음
- 백엔드(`fetch_eod.py`)의 재매수 리셋 시 `entry["allin"]`과 `entry["since"]`를 **함께** 당일로 갱신해야 프론트가 비교할 새 기준가·새 직전고점 창이 동시에 생김(아래 리밸런싱 스티키 구간 참고)

**리밸런싱 스티키 구간 (직전 고점/올인 지점 탭 · NORMAL 모드)**
- (2026-07-25 변경) 구간을 **그리드(2.5%/5%)에 고정된 정수**로 저장하면 프론트의 -25%/-50% 토글과 어긋나는 버그가 있어 폐기. 대신 `masam.rebalancing.nvda_lowest_close` / `qqq_lowest_close` / `rank2_lowest_close`(그리드 무관 원시 최저 EOD 종가)를 저장.
  - EOD 배치(`fetch_eod.py`)가 매일 갱신: 저장된 저점보다 당일 종가가 낮으면 갱신, 아니면 유지(스티키)
  - 막바지 2구간 상승(전량 재매수) 판정: (2026-08-04 변경) 그리드는 티커별 독립(`rebalancing.max_pct_by_ticker[티커]`, §5 참고). 판정도 "구간 번호 비교"가 아니라 목표 구간의 실제 가격(`base*(1-step*(prev_zone-2))`) 도달 여부로 함 — 판정 통과 시 저점을 당일 종가로 리셋
  - (2026-07-31 수정) `rank2_lowest_close`는 원래 백엔드 미구현 상태로 프론트·백엔드 모두 2등주를 스킵하고 있었음 → 1등주 교체(오버테이크)로 NVDA가 2등주로 밀린 뒤, 종가 기준 2구간 하락이 있었는데도 스티키 floor가 없어 다음날 반등만 해도 체크가 사라지는 버그로 이어짐. `fetch_eod.py`에 rank2 저점 스티키 계산 추가 + `app.html`의 `rangeTarget/tgt !== 'rank2'` 스킵 제거로 1·2등주 완전 동등 처리
  - **올인 기준가(`allin`) 갱신을 `reached_recovery`로만 한정 (2026-08-06 수정)**: `_update_ticker()`의 `is_reset = reached_recovery or new_peak`에서, `entry["allin"]` 갱신까지 `is_reset` 전체(즉 `new_peak` 단독으로도)에 걸려있었음. `prev_high`(직전 고점)는 신고가 때마다 항상 갱신되는 필드라, 얕은 눌림 후 소폭 신고가만 찍어도 `allin`이 덩달아 리셋돼 "직전 고점"/"올인 지점" 두 탭이 실제로는 아직 재매수 조건(2구간 이상 회복)을 못 채웠는데도 같은 값으로 붕괴하는 버그가 있었음. `entry["allin"] = close`를 `reached_recovery`(2구간 하락 후 실제 회복)일 때만 실행하도록 분리. `test_zone_reach.py::test_allin_vs_prev_high`에 회귀 테스트 있음.
    - 단, **저점이 이미 2구간 이상 깊었던 상태에서 신고가를 찍으면** `reached_recovery`도 함께 True가 돼서(회복 목표가가 새 고점=오늘 종가 자체가 되어 항상 자명하게 충족) 결과적으로 `allin`도 같이 갱신됨 — 이건 버그가 아니라 정상(진짜 2구간 이상 회복이 실제로 일어난 것). NVDA가 2026-08-05에 저점 190.01(2구간 하락)에서 종가 219.22로 신고가 경신했을 때 직전고점·올인지점이 둘 다 219.22로 같아진 게 이 케이스. 반대로 QQQ처럼 저점에서 2구간만 회복하고 옛 전고점은 못 넘은 경우(`allin` 723.85 < `prev_high` 725.51)는 두 값이 정상적으로 분리됨.
  - **재매수 시 `since`도 함께 리셋 (2026-08-10 수정)**: `reached_recovery`일 때 `entry["allin"]`은 리셋하면서 `entry["since"]`(직전고점 `prev_high` 계산의 시작일 — `hist.loc[since_date:, "Close"].max()`)는 그대로 둬서, 재매수 직후에도 `prev_high`가 재매수 이전(붕괴 전) 옛 전고점을 계속 반영하고 있었음. 그 결과 재매수 직후 `prev_high`가 새 `allin`보다 이미 훨씬 높은 채로 남아, 위 "직전 고점/올인 지점 자동전환"이 매 재매수 사이클마다 곧장 무력화되는 문제로 이어짐(2026-08-06에 이걸 `eod_close` 비교로 우회했다가 다른 버그가 남). `reached_recovery`일 때 `entry["since"] = today`와 `new_high = close`(=`prev_high`도 재매수가로 리셋)를 함께 실행하도록 수정 — 재매수 직후엔 `prev_high == allin`(올인 지점부터 시작), 그 이후 진짜 신고점을 찍어야만 `prev_high > allin`(직전 고점)으로 전환됨. `test_zone_reach.py::test_since_reset_on_recovery`에 회귀 테스트 있음.
  - **1구간 하락 중 신고가만으로 저점이 조기 리셋되던 버그 (2026-08-29 수정)**: `is_reset = reached_recovery or new_peak`에서 `new_peak`(직전 고점을 넘는 신고가) 단독 발동이 `prev_zone`을 가리지 않고 저점을 오늘 종가로 완전히 리셋해왔음. `prev_zone>=2`일 땐 새 고점이 서면 `reached_recovery`도 항상 자명하게 함께 True가 돼(바로 위 항목 참고) 문제가 없었지만, **`prev_zone==1`**(2구간 하락 문턱엔 못 미친 상태)일 때는 `reached_recovery`가 구조적으로 항상 False인데도 `new_peak`만으로 리셋이 발동 — 매뉴얼상 재매수 트리거는 "막바지 2구간 상승"뿐인데, since-윈도우 국지적 직전 고점을 살짝만 넘는 신고가로도 "1구간 하락 → 완전 회복(100%/현금0%)"으로 잘못 표시됨(NVDA: 직전고점 225.3→저점 208.48(1구간)→227.98 반등, 2구간 회복 목표가 미달인데도 리셋). `is_reset = reached_recovery or (new_peak and prev_zone == 0)`로 좁혀서 prev_zone==0(추적 중인 하락이 없어 리셋해도 무해)일 때만 new_peak 단독 리셋을 허용. `prev_high`는 여전히 무조건 매 배치 갱신(506행)돼 "직전 고점" 표시 자체는 정상. `test_zone_reach.py`에 회귀 테스트 있음. **소급 정정**: 배포 전 이미 리셋된 NVDA `lowest_close`(227.98)를 원래 값(208.48)으로 `masam.json` 수동 정정.
- 프론트(`renderRangeTable`, `_calcZone(tgt)`)는 이 원시 저점 가격을 가져와 **그때그때 선택된 그리드**로 구간을 재계산 후 `Math.max(live_zone, eod_zone)`으로 floor 적용 (배너·테이블 동일 로직)
- 구간 판정 시 현재가(`RANGE_CUR`, 라이브)가 아니라 `masam.eod_close.{nvda,qqq,rank2}`(EOD 종가)를 기준으로 함 — 장중 변동만으로 구간이 흔들리지 않도록. CRISIS/PANIC 모드는 기존대로 장중 저가(`d.low`) 기준 유지.

**전량 재매수 행 (직전 고점/올인 지점 탭 · NORMAL 모드 · curZone > 0)**
- 막바지 2구간 상승 시 전량 재매수 지점을 테이블에 표시 (주식 100% / 현금 올인)
- curZone=1: 기준 행 위에 별도 행 추가 (`base × 1.025`, 구간 레이블 `▲`)
- curZone=2: 기준 행의 주식/현금 컬럼을 `100% / 올인`(빨간색)으로 표시
- curZone≥3: `curZone-2` 구간 행의 주식/현금 컬럼을 `100% / 올인`으로 표시
- 우측 status 인디케이터: 빈 원형(`rt-none`) — 다른 행과 동일 스타일

**주가 구간 드롭다운/타이틀 (2026-07-28)**
- 타이틀은 종목 접두어 없이 "주가 구간"으로 통일(드롭다운 열면 바로 종목 보이므로 중복 제거)
- 드롭다운 표기 통일: "1등주 (티커)" / "2등주 (티커)" / "나스닥 (QQQ)"
- 주의: 부모에 `display:flex; gap`이 있으면 텍스트 중간의 `<span>`으로 쪼개진 조각들 사이에도 gap이 적용돼 괄호 안에 의도치 않은 여백이 생김 — 라벨 전체를 span 하나로 감싸서 해결(1·2등주 라벨에 적용됨)

**경제지표 탭 FRED 매크로 대시보드 (2026-08-21 4단계 확장)**
- **1단계 — 시리즈 설정 배열화**: `fetch_fred.py`의 `SERIES` 리스트에서 시리즈 ID를 한 곳에서 관리. `critical=True`(DFF/DGS10/WALCL — 마삼룰 헤지 판정용, `fetch_eod.py`의 `calc_hedge_type()`에 직접 입력됨)는 실패 시 `fetch()`가 배치 전체를 `sys.exit`으로 중단(기존 파일 보존). `critical=False`(신규 6종)는 `try_fetch()`로 개별 실패해도 그 필드만 `null`, 배치는 계속. 요청받았던 `ACMTP10`은 FRED에 실재하지 않는 ID(404) — ACM 10년 기간프리미엄의 진짜 ID는 `THREEFYTP10`. **아이콘과 마찬가지로 FRED 시리즈 ID도 존재 여부를 코드 작성 전에 `curl -s https://fred.stlouisfed.org/graph/fredgraph.csv?id=시리즈ID`(API 키 불필요한 공개 CSV 엔드포인트)로 확인할 것** — 그럴듯한 이름이 실제로는 없는 경우가 있음.
- **2단계 — QE 3-state 판정**: `qe_state`("QE_ON"/"LIQUIDITY_SUPPLY"/"QT"/"UNKNOWN", `fetch_fred.py`)를 신설. WALCL 단독 증가만 보면 TGA 변동·레포 사용 등 비QE성 요인으로도 오판 가능 → TREAST(연준의 순수 국채 보유량) 방향까지 같이 봐서 `WALCL↑+TREAST↑=QE_ON`, `WALCL↑+TREAST 횡보/감소=LIQUIDITY_SUPPLY`, `WALCL 횡보/감소=QT`(TREAST 방향 무관, WALCL↓+TREAST↑ 같은 애매한 조합도 이 케이스로 떨어짐 — "총자산 자체가 안 늘면 QE 아님"이 우선). **표시 전용 — 마삼룰 헤지 자동판정이 쓰는 기존 `qe_active` 불리언(WALCL 단독 4주 이평 비교)은 그대로 유지**, 절대 대체하지 않음. "4주 증가" 판정은 `ma4_up()` 헬퍼로 통일(최근 4개 관측치 평균 vs 이전 4개 평균 — 기존 WALCL 단독 판정과 동일 방식이라 일관성 유지).
- **3단계 — 추세 축**: `change_over()` 헬퍼로 변화량 계산 — 일간 시리즈(DFF·10Y·30Y·스프레드·달러지수·기대인플레·기간프리미엄)는 20영업일, 주간 시리즈(WALCL·TREAST·WRESBAL)는 4주(20주간 관측치는 ~5개월 전과 비교하는 셈이라 "최근 변화" 취지에 안 맞음, 2단계 QE 판정과 동일 윈도우로 일관성 유지). `history.{지표}` 배열을 60개로 확장(기존 20/12개). 프론트 `macroCard(label, chipText, subText, sparkValues, chg, chgDir, asOf)` 헬퍼로 카드 렌더링 통합(예전엔 idx-cell 마크업을 카드마다 복제).
- **4단계 — 발표 주기 분리**: 상단 그리드는 VIX·나스닥시장심리·금리환경·DFF(마삼룰 판정 직결) 4카드만 유지, 연준총자산(WALCL)·10Y를 포함한 나머지는 접이식 아코디언 2개로 분리 — `[일간] 금리·통화`(10Y/30Y/스프레드/기간프리미엄/달러인덱스/기대인플레), `[주간] 연준 유동성`(WALCL/TREAST/WRESBAL/QE 3-state 배지). WALCL/TREAST/WRESBAL은 수요일 기준 주간 발표라 일간 지표와 섞이면 며칠 지난 값을 오늘 값으로 오독하기 쉬움 → 카드마다 `{지표}_as_of`(실제 관측치 날짜)를 "기준일" 텍스트로 표시. `toggleAccordion(id)`로 접기/펼치기(기본 접힘).
- **부수 버그 수정**: `fetch_fred.py`가 파일을 재작성할 때 `existing`에서 정해둔 필드(vix 등) 몇 개만 화이트리스트로 옮기던 구조라, `fetch_eod.py`가 나중에 추가한 필드(예: `vix_chg_20d`)가 `fetch_fred.py` 재실행 시 조용히 사라지는 문제가 있었음 → `**existing`을 먼저 펼치고 이 스크립트가 계산한 키만 덮어쓰는 방식으로 변경(`fetch_eod.py`는 원래부터 이 안전한 패턴이었음, `fetch_fred.py`만 예전 방식이 남아있었던 것).

**localStorage 저장 항목**
- `range_allin_nvda`, `range_prev_nvda`, `range_allin_qqq`, `range_prev_qqq`, `range_allin_rank2`, `range_prev_rank2` — 올인·직전고점 수동 입력가
- `max_pct_nvda`, `max_pct_rank2`, `max_pct_qqq` — 현금화 최대 한도 (2026-07-28부터 세 타겟 완전 독립, 설정 탭에 2등주 행 추가)
- `portfolio_ratio` — 1등주:QQQ 포트폴리오 비율
- `momtFavSet` — 모멘텀 관심종목(하트) 목록
- `momtTrimSet` — 트레일링 스탑 1차 터치 기록
- `alloc_history`, `alloc_last` — 권장 비중 변경 히스토리·직전 스냅샷 (2026-08-03 추가, 아래 참고)
- ⚠️ 설정 탭 토글(ON/OFF) 상태는 localStorage 미저장 → 새로고침 시 초기화됨

**알림 히스토리 (벨 아이콘) — (2026-08-03 추가)**
- 마삼룰 화면(발견/관심/경제지표/설정) topbar에 `.notif-btn`(`.refresh-btn`과 동일 스타일) 추가, 클릭 시 `#notif-overlay`/`#notif-drawer`(`#alloc-drawer`와 동일한 하단 드로어 패턴) 오픈. 경제지표·설정은 마삼룰·모멘텀이 topbar를 공유하므로 `updateSettingsView()`에서 `.notif-btn` 표시를 `currentMode` 기준으로 같이 토글.
- **2원화 추적**(근거: 권장 비중은 `portfolio_ratio`/`max_pct_*` 같은 기기별 localStorage 설정에 의존해 서버가 재현 불가):
  - 마삼 모드 전환·1등주 교체·2등주 교체·구간 도달·구간 회복 → 서버(`notifications.json`, `fetch_eod.py`가 전일 대비 diff). 이벤트 타입: `masam_mode`/`leader_swap`/`rank2_swap`/`zone_reach`(2026-08-04에 뒤 2종 추가)/`zone_reset`(2026-08-06 추가)
  - **`zone_reset` 추가 배경 (2026-08-06)**: `zone_reach`(구간 하락 도달)만 있고 반대 방향(구간 회복=전량 재매수) 이벤트가 없어서, 이 전환은 클라이언트 `alloc_history`에만 기록됐음 — `alloc_history`는 "직전 로드 시점 스냅샷과의 diff"라 그 전환을 실제로 겪은 기기에서만 쌓이고, 전환 이후에 처음 접속하거나 로컬스토리지가 지워진 기기는 그 전환 이력을 영영 볼 수 없었음. `_update_ticker()`가 `reset_from_zone`(reached_recovery로 리셋되며 벗어난 구간, 0구간 리셋은 알림 의미 없어 제외)을 함께 반환하도록 해서 서버 쪽에도 대칭 기록.
  - 권장 비중 변경 → 클라이언트(`localStorage['alloc_history']`, `checkAllocationChange()`가 페이지 로드마다 diff) — 기기별로 따로 쌓임, 동기화 안 됨(의도된 동작)
- 두 소스는 `renderNotifList()`가 날짜 내림차순으로 병합해 `window._notifEvents`에 저장, `openNotifDrawer()`가 렌더링
- 권장 비중 변경 항목: (2026-08-04 재설계) 기존엔 `1등주 4→1구간, 2등주 3→0구간, QQQ 3→1구간 — 주식 68%→93%, 현금 32%→7%`처럼 한 줄에 다 욱여넣어 가독성이 나빴음. `alloc_history`를 flat text 대신 구조화 필드(`prevStock`/`nowStock`/`zoneParts`)로 저장하도록 바꾸고, 렌더링 시 "주식 비중 68%→93%"를 주 정보(숫자만 강조, 리스트 다른 항목과 폰트 크기는 동일하게)로, 구간 변화는 알약 칩으로 부가정보화. 기존에 이미 저장된 flat text 항목은 폴백으로 그대로 표시(하위호환)
- 아이콘: 하단 탭과 동일한 `bxs:`(BoxIcons Solid) 패밀리로 통일(기존 heroicons에서 변경, 2026-08-04). **주의**: boxicons solid 세트가 생각보다 좁아서 그럴듯한 이름이 실제로는 존재하지 않아 빈 아이콘으로 렌더링되는 경우가 많음(`bxs:repeat`/`bxs:refresh`/`bxs:transfer-alt`/`bxs:left-right-arrow-circle` 전부 미존재로 확인됨— `left-right-arrow-circle`은 2026-08-04에 "확인됨"으로 잘못 기록됐다가 2026-08-06 실사용 중 빈 원으로 뜨는 게 발견됨). **아이콘 존재 여부는 브라우저 렌더링이 아니라 `curl -s https://api.iconify.design/bxs.json?icons=아이콘명`으로 확인할 것**(단일 svg 엔드포인트 `/bxs/이름.svg`는 존재하는 아이콘도 404를 내는 경우가 있어 신뢰 불가 — 반드시 json 배치 엔드포인트로 확인). 확인된 것: `bxs:sort-alt`(1등주/2등주 교체 — 2026-08-06부터 두 이벤트 동일 아이콘으로 통일, 트로피는 "1등 등극" 의미가 강해 2등 교체엔 안 맞아서 제외), `bxs:down-arrow-circle`(구간 도달), `bxs:up-arrow-circle`(구간 회복/권장비중 증가), `bxs:analyse`(마삼 모드 전환), `bxs:pie-chart-alt-2`/`bxs:bell`(기본값). 드로어 헤더의 🔔 이모지도 topbar 벨 버튼과 동일한 `heroicons:bell`로 교체(이모지를 구조적 아이콘으로 쓰지 말 것 원칙)
- 설계·구현 근거: `docs/superpowers/specs/2026-08-03-notification-history-design.md`, `docs/superpowers/plans/2026-08-03-notification-history.md`

**설정 탭 전략 출처 카드**
- 레이아웃: 좌측 `전략 출처` 레이블 + 우측 `[유튜브 아이콘] 채널명` (두 줄: 이름 / @핸들)
- 마삼룰: 소장 조던 / `@제이디부자연구소JDRich` → `https://www.youtube.com/@%EC%A0%9C%EC%9D%B4%EB%94%94%EB%B6%80%EC%9E%90%EC%97%B0%EA%B5%AC%EC%86%8CJDRich`
- 모멘텀: 미국주식으로은퇴하기 / `@mijooeun` → `https://www.youtube.com/@mijooeun`
- 두 탭 모두 출처 카드 위에 면책 disclaimer 표시

### 9-3. 마삼룰 화면

| 화면 | 내용 |
|---|---|
| 발견(현재 상태) | 지수 롤(나스닥/S&P/다우) · 국면칩(리밸런싱/말뚝박기/V자반등/올인/마삼해제) · 모드 배지(NORMAL/CRISIS/PANIC) + 이번 달 마삼 N회·해제 D-day · 나스닥 최고점 대비 %·최근 마삼일 · 목표 비중 배너 · **1등주 주가 구간**(드롭다운 1등주/QQQ · 탭 최고점/직전고점/직접입력 · -25%/-50% · 말뚝 구간 테이블) |
| 관심(시가총액 순위) | 큐레이트 글로벌 시총 순위(1등주 트로피·**1등주 대비 격차%**) · 롤(환율/VIX/공포탐욕) |
| 경제지표(시장환경·표시) | VIX·나스닥 시장심리·금리환경·DFF(전월 인상/인하/동결) 상단 4카드(마삼룰 판정 직결, 스파크라인·20일 변화량 포함) · **[일간 금리·통화]/[주간 연준 유동성] 아코디언**(10Y/30Y/스프레드/기간프리미엄/달러인덱스/기대인플레, WALCL/TREAST/WRESBAL/QE 3-state 배지, 카드별 기준일 표시 — §9-5 "경제지표 탭 FRED 매크로 대시보드" 참고) · **✦ 헤지 권장 배너(슬라이드)** · 추가 자금(RSI14/MFI14, 1등주/QQQ 토글) · **올인 체크리스트 6종** · (표시)Fear&Greed |
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
