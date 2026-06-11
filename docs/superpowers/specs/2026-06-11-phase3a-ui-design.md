# Phase 3A 모바일 UI 설계 — Next.js PWA + MA50 스크리너 4탭

## 목표

`ma3-momentum` 레포 `web/` 서브디렉토리에 Next.js PWA를 구축한다. 전략 토글 앱 셸(마삼 placeholder 포함) + MA50 스크리너 4탭을 완성하고 Vercel에 배포한다. 데이터는 `data` 브랜치 raw URL에서 fetch한다.

---

## 확정 사항

- **위치**: 같은 레포 `web/` 서브디렉토리
- **렌더링**: Client SPA — `'use client'` 전면, SSR 없음
- **앱 셸**: 전략 토글(마삼 placeholder 포함) + MA50 4탭 Bottom Nav
- **배포**: Vercel Hobby, Root Directory = `web`

---

## 1. 파일 구조

```
ma3-momentum/
└── web/
    ├── app/
    │   ├── layout.tsx            ← HTML shell, PWA meta, Pretendard 폰트, 면책 Footer
    │   ├── page.tsx              ← 진입점 (AppShell 렌더)
    │   └── globals.css           ← CSS 변수 (디자인 시스템 토큰)
    ├── components/
    │   ├── AppShell.tsx          ← 전략 토글 + 탭 라우팅
    │   ├── masam/
    │   │   └── MasamPlaceholder.tsx
    │   └── ma50/
    │       ├── BuyTab.tsx        ← 탭1: 매수 후보
    │       ├── HoldTab.tsx       ← 탭2: 보유 관리
    │       ├── MarketTab.tsx     ← 탭3: 시장 환경 (공유 컴포넌트)
    │       └── SettingsTab.tsx   ← 탭4: 설정
    ├── hooks/
    │   ├── useSignals.ts         ← signals.json SWR fetch
    │   └── useMasam.ts           ← masam.json SWR fetch (Phase 3B에서 채움)
    ├── lib/
    │   └── urls.ts               ← raw URL 상수
    ├── types/
    │   └── signals.ts            ← SignalsJson, SignalItem 타입
    ├── public/
    │   ├── manifest.json
    │   └── icons/                ← PWA 아이콘 (192x192, 512x512)
    ├── next.config.js
    ├── tailwind.config.ts
    └── package.json
```

---

## 2. 디자인 시스템

`globals.css` CSS 변수 — `ux-ui_mockup.html` 토큰 그대로 이식:

```css
:root {
  --bg: #16161a;
  --frame: #0a0a0c;
  --card: #1e1f24;
  --card-sub: #1b1c20;
  --inset: #26272d;
  --pill: #26272d;
  --pill-on: #34353d;
  --line: rgba(255, 255, 255, 0.05);
  --t1: #f3f3f5;
  --t2: #8b8d94;
  --t3: #5a5b63;
  --up: #f04452;
  --down: #4593fc;
  --accent: #3182f6;
  --green: #15c47a;
  --amber: #f7a93b;
  --teal: #3fc8a9;
}
```

- 폰트: Pretendard (CDN, weight 500 기본 / 700·800 헤딩)
- 카드 radius: 16px
- 패딩: 20px 좌우
- Tailwind는 유틸리티 보조용. 레이아웃·컴포넌트 스타일은 CSS 변수 + className 직접 작성

---

## 3. 데이터 레이어

### `lib/urls.ts`

```ts
const BASE = "https://raw.githubusercontent.com/JubroPark/ma3-momentum/data";
export const URLS = {
  signals: `${BASE}/outputs/signals.json`,
  masam:   `${BASE}/outputs/masam.json`,
} as const;
```

### `types/signals.ts`

```ts
export type SignalType =
  | "EARLY_TREND" | "STRONG_BREAKOUT" | "BOUNCE" | "SELL" | "OK";

export type State =
  | "WATCH" | "BUY" | "HOLDING" | "SELL_WATCH" | "SELL";

export type Metrics = {
  close: number; ma50: number; ma200: number;
  gap50: number; vol_ratio: number; rs_pct: number;
  ma50_slope_pct: number; high_n: number; atr14: number;
  sector_etf: string;
};

export type SignalItem = {
  ticker: string;
  signal_type: SignalType;
  state: State;
  score: number;
  trigger_reason: string;
  metrics: Metrics;
};

export type SignalsJson = {
  as_of: string;
  regime: "RISK_ON" | "RISK_OFF";
  items: SignalItem[];
};
```

### `hooks/useSignals.ts`

```ts
import useSWR from "swr";
import { URLS } from "@/lib/urls";
import type { SignalsJson } from "@/types/signals";

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useSignals() {
  const { data, error, isLoading } = useSWR<SignalsJson>(URLS.signals, fetcher, {
    refreshInterval: 60 * 60 * 1000,
    revalidateOnFocus: false,
  });
  return { data, error, isLoading };
}
```

**공통 상태 처리:**
- 로딩: 스켈레톤 카드 (dim 처리된 카드 모양)
- 에러: "데이터를 불러올 수 없습니다 · 잠시 후 다시 시도" 인셋 카드
- 빈 배열: "오늘은 매수 후보가 없습니다" 안내

---

## 4. 앱 셸

### `AppShell.tsx`

```
┌─────────────────────────────────┐
│  TopBar                          │
│  좌: 나스닥 (as_of 날짜)          │
│  우: 알림·검색·햄버거 (빈 구현)    │
├─────────────────────────────────┤
│  전략 토글                        │
│  [마삼 대응]  [MA50 스크리너]      │
│  → localStorage("strategy") 저장 │
├─────────────────────────────────┤
│  컨텐츠 영역 (overflow-y scroll)  │
│  • 마삼 선택 → MasamPlaceholder  │
│  • MA50 선택 → 4탭 컨텐츠         │
├─────────────────────────────────┤
│  Bottom Nav (MA50 모드만 표시)     │
│  매수후보 / 보유관리 / 시장환경 / 설정 │
│  → localStorage("ma50Tab") 저장  │
├─────────────────────────────────┤
│  면책 Footer (position: fixed)   │
│  ⚠️ 투자 권유 아님 · 실거래 전      │
│  백테스트 검증 필수                 │
└─────────────────────────────────┘
```

**상태 초기화:** 앱 로드 시 localStorage에서 전략·탭 읽어 초기값 설정. 없으면 MA50 + 탭1 기본.

---

## 5. MA50 4탭 컴포넌트

### 탭1: BuyTab (매수 후보)

- **필터 타일** (가로 스크롤): 강돌파 / 초기추세 / 지지반등 / 전체
  - 선택 타일로 `items` 필터링 (`signal_type` 기준)
- **시그널 요약 인셋**: "강돌파 N · 지지반등 N · 레짐 RISK_ON/OFF"
- **RISK_OFF 배너**: "하락장 — 초기추세 신호 비활성" (regime === "RISK_OFF" 시)
- **종목 리스트** (score 내림차순):
  - 순위 · 로고(ticker 이니셜 + 색) · 종목명 · chip · 메트릭(거래량배수·RS·gap50) · 점수

### 탭2: HoldTab (보유 관리)

- `state`가 `HOLDING` | `SELL_WATCH` | `SELL`인 items만 표시
- 각 종목 카드: state chip + `days_in_state` + `entry_price` + `stop_level`
- `SELL` 종목: "매도 권장" 강조 박스 (빨간 인셋)
- 빈 상태: "현재 보유 중인 종목이 없습니다"

### 탭3: MarketTab (시장 환경)

- 레짐 게이지 카드: RISK_ON / RISK_OFF + 설명 문구
- `as_of` 날짜 표시
- FRED 지표 섹션: "준비 중" placeholder (Phase 3B 이후 채움)
- 이 컴포넌트는 Phase 3B에서 마삼 탭3과 공유

### 탭4: SettingsTab (설정)

- **RISK_OFF 모드 토글**: strict(차단) / soft(완화) → localStorage("riskOffMode") 저장
- **파라미터 표시** (읽기 전용): vol_mult, breakout_high_lookback, rs_early_th, consec_below_sell, max_hold_watch_days
- **데이터 정보**: as_of 날짜, 갱신 주기(평일 22:00 UTC)

---

## 6. PWA 설정

### `app/layout.tsx` 메타

```tsx
export const metadata = {
  title: "ma3 momentum",
  description: "마삼 대응 · MA50 스크리너",
  themeColor: "#16161a",
  manifest: "/manifest.json",
  viewport: "width=device-width, initial-scale=1, viewport-fit=cover",
};
```

### `public/manifest.json`

```json
{
  "name": "ma3 momentum",
  "short_name": "ma3",
  "display": "standalone",
  "background_color": "#16161a",
  "theme_color": "#16161a",
  "start_url": "/",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

---

## 7. Vercel 배포

- Root Directory: `web`
- Framework: Next.js (자동 감지)
- 환경 변수: 없음 (모든 데이터 public raw URL)
- `main` 브랜치 push → 자동 빌드·배포
- CORS: raw.githubusercontent.com 공개 리소스, 별도 설정 불필요

### `web/next.config.js`

```js
const nextConfig = {
  images: { unoptimized: true },
};
export default nextConfig;
```

---

## 8. 에러 핸들링

| 상황 | 대응 |
|---|---|
| signals.json fetch 실패 | 에러 인셋 카드, SWR 자동 재시도 |
| 데이터 stale (as_of 오래됨) | 별도 처리 없음 (Phase 4에서 고려) |
| localStorage 없음 | 기본값으로 폴백 |
| 빈 종목 리스트 | 안내 문구 표시 |

---

## 9. Phase 3A 범위 외 (의도적 제외)

| 항목 | 이유 |
|---|---|
| 마삼 3탭 컨텐츠 | Phase 3B |
| Web Push 알림 | Phase 4 |
| 파라미터 편집 | Phase 4 |
| lightweight-charts 종목 차트 | Phase 4 (종목 상세) |
| FRED 지표 실데이터 | Phase 3B (market.json 추가 후) |
| 사용자 watchlist 저장 | Phase 4 |
