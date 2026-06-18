# Ma3 Momentum v2 — UI 구현 설계 명세서

**날짜**: 2026-06-18  
**범위**: Phase 3 UI (Next.js PWA) + 부분 실데이터 (FRED)  
**기준 문서**: CLAUDE.md · new_조던_마삼룰_통합매뉴얼.md · new_미주은_모멘텀_탑픽_전략구조.md · ux-ui_mockup_v2.html

---

## 1. 프로젝트 구성

### 위치
```
Ma3 momentum v2/
├── app/                    # Next.js 14 App Router 프로젝트
├── scripts/
│   └── fetch_fred.py       # FRED API → masam_market.json
├── docs/superpowers/specs/ # 설계 문서
└── CLAUDE.md
```

### 기술 스택
| 영역 | 기술 |
|---|---|
| 프레임워크 | Next.js 14 App Router · TypeScript · Tailwind CSS |
| 차트 | lightweight-charts |
| 데이터 fetch | SWR (`swr` 패키지) |
| PWA | `@ducanh2912/next-pwa` |
| 데이터 소스 | `public/data/*.json` 정적 파일만 (서버 API 없음) |
| FRED 실데이터 | `scripts/fetch_fred.py` 로컬 실행 → JSON 갱신 |
| 폰트 | Pretendard Variable (jsDelivr CDN) |
| 아이콘 | Iconify |
| 상태관리 | React Context + `localStorage` 영구 저장 |

---

## 2. 아키텍처

### 컴포넌트 구조 (Feature-Slice)
```
src/
├── app/
│   ├── layout.tsx              # 앱 셸 (토글 + 탭바 + 면책)
│   └── page.tsx                # 탭 콘텐츠 라우팅
│
├── shared/components/
│   ├── StrategyToggle          # [마삼룰][모멘텀] 슬라이딩 토글
│   ├── BottomTabBar            # 하단 4탭 (전략별 라벨 교체)
│   ├── DisclaimerFooter        # 면책 고정 배너 (항상 노출)
│   ├── NotificationBell        # 알림 아이콘 + 배지
│   ├── Card                    # 공통 카드 컨테이너
│   ├── Badge                   # 상태 배지 (NORMAL/CRISIS/GREEN/RED 등)
│   ├── IndexRoll               # 지수 롤링 표시
│   └── EconPanel               # 경제지표 패널 베이스
│
├── features/masam/components/
│   ├── DiscoveryTab            # 탭1: 현재 상태·모드·구간 테이블
│   ├── WatchlistTab            # 탭2: 시총 순위·격차
│   ├── MarketTab               # 탭3: 금리·QE·10Y·헤지·올인 체크리스트
│   └── SettingsTab             # 탭4: 리밸런싱 한도·부록 Z 토글
│
└── features/momentum/components/
    ├── ToppickTab              # 탭1: 탑픽 카드·필터칩·상태 배지
    ├── PortfolioTab            # 탭2: 포지션·트랜치·스탑선
    ├── MarketTab               # 탭3: 국면 GREEN/YELLOW/RED
    └── SettingsTab             # 탭4: 줍줍 비중·트레일링 preset
```

### 앱 셸 레이아웃
```
┌─────────────────────────────────┐
│  전략 토글 [마삼룰][모멘텀] + 알림  │
├─────────────────────────────────┤
│         화면 콘텐츠 (탭별 교체)     │
├─────────────────────────────────┤
│  ⚠️ 투자 권유 아님 · 백테스트 검증  │  ← 항상 노출
├─────────────────────────────────┤
│  탭1  │  탭2  │  탭3  │  탭4     │
└─────────────────────────────────┘
```

### 전략 Context
```ts
type Strategy = 'masam' | 'momentum'
type Tab = 0 | 1 | 2 | 3

const AppContext = {
  strategy: Strategy,   // localStorage 영구 저장
  tab: Tab,
  setStrategy,
  setTab,
}
```

---

## 3. 탭 매핑

| 탭 | 마삼룰 | 모멘텀 |
|---|---|---|
| 탭1 | 발견 (현재 상태·모드·구간) | 탑픽 (종목 선정·필터칩) |
| 탭2 | 관심 (글로벌 시총 순위·격차) | 관심종목 (포지션·트랜치·스탑) |
| 탭3 | 경제지표 (금리·QE·10Y·헤지·올인 체크리스트) | 경제지표 (국면 GREEN/YELLOW/RED) |
| 탭4 | 설정 (리밸런싱 한도·부록 Z 토글) | 설정 (줍줍 비중·트레일링 preset) |

---

## 4. 데이터 레이어

### 파일 목록
```
public/data/
├── masam_market.json       ← FRED 실데이터 (fetch_fred.py 생성)
├── masam.json              ← mock (마삼 상태·비중·올인 체크리스트)
├── mcap_daily.json         ← mock (1등주 시총 순위)
├── hedge_prices.json       ← mock (TLT·IAU·GLD·TIP)
├── positions.json          ← mock (모멘텀 포지션)
├── indicators.json         ← mock (MA·ATR·거래량 지표)
├── momentum_market.json    ← mock (국면 GREEN/YELLOW/RED)
├── params.json             ← mock (전략 파라미터·부록 Z 토글)
└── live.json               ← mock (준실시간 표시값)
```

### FRED 실데이터 (`masam_market.json` 일부)
```json
{
  "as_of": "YYYY-MM-DD",
  "rate_env": "NON_ZERO",
  "dff": 4.33,
  "qe_active": false,
  "walcl_trend": "DOWN",
  "treasury_10y": 4.21,
  "treasury_10y_trend": "UP"
}
```
수집 항목: `DFF`(기준금리) · `DGS10`(10Y 금리) · `WALCL`(연준 총자산)

### 데이터 훅 패턴
```ts
function useMasamData() {
  return useSWR('/data/masam.json', fetcher)
}
function useMomentumPositions() {
  return useSWR('/data/positions.json', fetcher)
}
```

---

## 5. 디자인 시스템 (ux-ui_mockup_v2.html 기준)

```css
--bg: #17171C;          --bg-deep: #0E0E12;
--surface: #202027;     --surface-2: #26262E;    --surface-3: #2C2C35;
--line: #2A2A31;
--txt: #F4F5F7;         --txt-2: #9A9AA3;        --txt-3: #6B6B73;
--up: #F04452;          /* 상승 = 빨강 (한국 관례) */
--down: #4593FC;        /* 하락 = 파랑 */
--blue: #3182F6;        --teal: #2BC4B6;          --purple: #8B5CF6;
/* 그라데이션: linear-gradient(110deg,#6d5efc,#3182F6 55%,#8b5cf6) */
```

- 모바일 390px · 다크 모드 전용
- 폰트: Pretendard Variable (500/600/700/800)
- 카드 radius ~16px · 좌우 패딩 17px
- 아이콘: Iconify (bxs/heroicons)

---

## 6. PWA & 환경

### Service Worker
- `@ducanh2912/next-pwa` 사용
- JSON fetch: Network First (항상 최신, 오프라인 시 캐시 폴백)

### 환경변수 (`.env.local` — git 제외)
```
FRED_API_KEY=<FRED_API_KEY>
```

### 에러 처리
| 상황 | 처리 |
|---|---|
| JSON fetch 실패 | 스켈레톤 유지 + "데이터 로딩 중" |
| `as_of` 2일 이상 지연 | "⚠️ 데이터 갱신 지연" 배너 |
| FRED 스크립트 실패 | 이전 JSON 유지 (덮어쓰기 안 함) |
| 설정값 범위 초과 | 저장 차단 + 인라인 에러 |

---

## 7. 구현 원칙

- **서버 API 없음**: PWA는 `public/data/*.json`만 fetch. 외부 API 직접 호출 금지.
- **면책 Footer 항상 노출**: 어느 화면에서도 숨김 금지.
- **판정용 = EOD 고정**: live.json은 표시값만. 장중 값으로 신호 발동 금지.
- **룰북 우선**: 엔진 로직은 두 매뉴얼이 정답. 임의 변경·단순화 금지.
- **마삼룰 화면**: ux-ui_mockup_v2.html 충실 포팅.
- **모멘텀 화면**: 탑픽 스펙 기반 새 설계 (셸·디자인 토큰 유지).
