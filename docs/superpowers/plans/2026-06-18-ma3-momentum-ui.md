# Ma3 Momentum v2 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Next.js 14 App Router PWA로 마삼룰·모멘텀 두 전략을 상단 토글로 전환하는 모바일 투자 보조 서비스 UI를 구현한다.

**Architecture:** Feature-slice 구조(features/masam, features/momentum, shared)로 두 전략을 완전 분리. PWA는 public/data/*.json만 fetch(서버 API 없음). FRED 실데이터는 scripts/fetch_fred.py가 masam_market.json을 생성.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, SWR, @ducanh2912/next-pwa, Jest + @testing-library/react, Python 3 (FRED 스크립트)

## Global Constraints

- 모바일 max-width 390px, 다크 모드 전용
- 폰트: Pretendard Variable (jsDelivr CDN) — 로컬 설치 금지
- 디자인 토큰: `--bg:#17171C` `--up:#F04452` `--down:#4593FC` 등 ux-ui_mockup_v2.html 기준 엄수
- 면책 Footer(`⚠️ 투자 권유 아님 · 실거래 전 백테스트 검증`) 전 화면 항상 노출, 숨김 금지
- PWA fetch 원칙: `/data/*.json` 정적 파일만. 외부 API 직접 호출 금지
- 판정용 데이터 = EOD 고정. live.json은 표시값만
- FRED API KEY: .env.local에만 저장, git 커밋 금지

---

## File Map

```
Ma3 momentum v2/
├── app/                          # Next.js 프로젝트 루트
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── jest.config.ts
│   ├── jest.setup.ts
│   ├── tsconfig.json
│   ├── .env.local                # gitignored
│   ├── .gitignore
│   ├── public/
│   │   ├── manifest.json
│   │   └── data/
│   │       ├── masam.json
│   │       ├── masam_market.json
│   │       ├── mcap_daily.json
│   │       ├── hedge_prices.json
│   │       ├── positions.json
│   │       ├── indicators.json
│   │       ├── momentum_market.json
│   │       ├── params.json
│   │       └── live.json
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   └── globals.css
│       ├── shared/
│       │   ├── context/AppContext.tsx
│       │   ├── types/masam.ts
│       │   ├── types/momentum.ts
│       │   ├── hooks/useData.ts
│       │   └── components/
│       │       ├── StrategyToggle.tsx
│       │       ├── BottomTabBar.tsx
│       │       ├── DisclaimerFooter.tsx
│       │       ├── NotificationBell.tsx
│       │       ├── Card.tsx
│       │       ├── Badge.tsx
│       │       └── IndexRoll.tsx
│       └── features/
│           ├── masam/
│           │   └── components/
│           │       ├── DiscoveryTab.tsx
│           │       ├── WatchlistTab.tsx
│           │       ├── MarketTab.tsx
│           │       └── SettingsTab.tsx
│           └── momentum/
│               └── components/
│                   ├── ToppickTab.tsx
│                   ├── PortfolioTab.tsx
│                   ├── MarketTab.tsx
│                   └── SettingsTab.tsx
└── scripts/
    └── fetch_fred.py
```

---

## Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `app/` (Next.js 프로젝트 전체)
- Create: `app/.gitignore`
- Create: `app/.env.local`
- Create: `app/jest.config.ts`
- Create: `app/jest.setup.ts`

**Interfaces:**
- Produces: `npm run dev` 동작, `npm test` 동작

- [ ] **Step 1: Next.js 프로젝트 생성**

```bash
cd "/Users/jubro/Claude Project/Ma3 momentum v2"
npx create-next-app@14 app \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --no-eslint \
  --import-alias "@/*"
```

- [ ] **Step 2: 의존성 설치**

```bash
cd app
npm install swr @ducanh2912/next-pwa
npm install -D jest jest-environment-jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 3: jest.config.ts 작성**

```ts
// app/jest.config.ts
import type { Config } from 'jest'
import nextJest from 'next/jest.js'

const createJestConfig = nextJest({ dir: './' })

const config: Config = {
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
}

export default createJestConfig(config)
```

- [ ] **Step 4: jest.setup.ts 작성**

```ts
// app/jest.setup.ts
import '@testing-library/jest-dom'
```

- [ ] **Step 5: .gitignore에 .env.local 확인**

`app/.gitignore`에 `.env.local` 항목이 있는지 확인. 없으면 추가.

- [ ] **Step 6: .env.local 작성 (커밋 금지)**

```
# app/.env.local
FRED_API_KEY=cb6fb72ffbfb566a4438a4287d451617
```

- [ ] **Step 7: 빌드 확인**

```bash
npm run build
```
Expected: 빌드 성공, 에러 없음

- [ ] **Step 8: 커밋**

```bash
cd "/Users/jubro/Claude Project/Ma3 momentum v2"
git init
git add app/ scripts/ docs/ CLAUDE.md new_조던_마삼룰_통합매뉴얼.md new_미주은_모멘텀_탑픽_전략구조.md ux-ui_mockup_v2.html
git commit -m "chore: 프로젝트 초기 스캐폴딩"
```

---

## Task 2: 디자인 시스템 (Tailwind 토큰 + globals.css)

**Files:**
- Modify: `app/tailwind.config.ts`
- Modify: `app/src/app/globals.css`

**Interfaces:**
- Produces: `bg-surface`, `text-up`, `text-down` 등 커스텀 클래스 사용 가능

- [ ] **Step 1: tailwind.config.ts 수정**

```ts
// app/tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#17171C',
        'bg-deep': '#0E0E12',
        surface: '#202027',
        'surface-2': '#26262E',
        'surface-3': '#2C2C35',
        line: '#2A2A31',
        txt: '#F4F5F7',
        'txt-2': '#9A9AA3',
        'txt-3': '#6B6B73',
        up: '#F04452',
        down: '#4593FC',
        blue: '#3182F6',
        teal: '#2BC4B6',
        purple: '#8B5CF6',
        amber: '#F7A93B',
      },
      fontFamily: {
        sans: ['Pretendard Variable', 'Pretendard', '-apple-system', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
      },
      maxWidth: {
        app: '390px',
      },
    },
  },
  plugins: [],
}

export default config
```

- [ ] **Step 2: globals.css 수정**

```css
/* app/src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');

  html, body {
    @apply bg-bg text-txt;
    height: 100%;
    overflow: hidden;
    -webkit-font-smoothing: antialiased;
    -webkit-tap-highlight-color: transparent;
  }

  * {
    box-sizing: border-box;
  }
}

@layer utilities {
  .gradient-accent {
    background: linear-gradient(110deg, #6d5efc, #3182F6 55%, #8b5cf6);
  }
  .gradient-text {
    background: linear-gradient(90deg, #7c6dff, #4593FC);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
}
```

- [ ] **Step 3: 커밋**

```bash
git add app/tailwind.config.ts app/src/app/globals.css
git commit -m "feat: 디자인 시스템 Tailwind 토큰 설정"
```

---

## Task 3: 타입 정의

**Files:**
- Create: `app/src/shared/types/masam.ts`
- Create: `app/src/shared/types/momentum.ts`

**Interfaces:**
- Produces: `MasamData`, `McapDaily`, `HedgePrices`, `MasamMarket`, `LiveData` (masam.ts)
- Produces: `Position`, `Indicators`, `MomentumMarket`, `Actions`, `Params` (momentum.ts)

- [ ] **Step 1: masam.ts 작성**

```ts
// app/src/shared/types/masam.ts

export type RateEnv = 'ZERO' | 'NON_ZERO'
export type TreasuryTrend = 'DOWN' | 'UP' | 'UNKNOWN'
export type MasamMode = 'NORMAL' | 'CRISIS' | 'PANIC'
export type HedgeType = 'TLT' | 'IAU_GLD_TIP' | 'DOLLAR' | 'NONE'

export interface AllInCondition {
  id: number
  label: string
  met: boolean
  grade: '약' | '중' | '강'
  detail?: string
}

export interface MasamData {
  as_of: string
  mode: MasamMode
  rate_env: RateEnv
  qe_active: boolean
  treasury_10y_trend: TreasuryTrend
  masam: {
    month_count: number
    last_masam_date: string | null
    crisis_end_dday: number | null
    panic_end_dday: number | null
  }
  leader_status: {
    rank1_ticker: string
    rank2_ticker: string
    gap_pct: number
    overtake_detected: boolean
    gap_within_10pct: boolean
  }
  target_allocation: {
    stock_pct: number
    hedge_pct: number
    cash_pct: number
    label: string
  }
  hedge_allocation: {
    type: HedgeType
    rationale: string
    exit_trigger: string
  }
  rebalancing: {
    cash_raised_pct: number
    max_pct: number
    qqq_pct: number
  }
  staking: {
    rate_env: RateEnv
    grid_pct: number
    target_pct: number
    deployed_pct: number
  }
  all_in_conditions: AllInCondition[]
  additional_buy: {
    target: 'rank1' | 'QQQ'
    rsi14: number
    mfi14: number
    both_below_50: boolean
  }
  panic_hold: { active: boolean; until_new_high: boolean }
  panic_reentry: { stage: number; tranches: number[] }
  recommended_action: string
  alerts: string[]
}

export interface McapItem {
  rank: number
  ticker: string
  name: string
  mcap_usd: number
  gap_pct_from_rank1: number
  is_leader: boolean
}

export interface McapDaily {
  as_of: string
  rank1_ticker: string
  items: McapItem[]
}

export interface HedgePrices {
  as_of: string
  TLT: number
  IAU: number
  GLD: number
  TIP: number
}

export interface MasamMarket {
  as_of: string
  rate_env: RateEnv
  dff: number
  qe_active: boolean
  walcl_trend: 'UP' | 'DOWN' | 'UNKNOWN'
  treasury_10y: number
  treasury_10y_trend: TreasuryTrend
  vix?: number
  fear_greed?: number
  usd_krw?: number
}

export interface LiveData {
  as_of: string
  nasdaq: { price: number; change_pct: number; dist_to_masam_pct: number }
  rank1: { ticker: string; price: number; change_pct: number }
  hedges: { TLT: number; IAU: number; GLD: number; TIP: number }
}
```

- [ ] **Step 2: momentum.ts 작성**

```ts
// app/src/shared/types/momentum.ts

export type PositionStatus = 'WATCH' | 'ENTRY_1' | 'ENTRY_2' | 'ENTRY_3' | 'TRIM' | 'EXIT' | 'REMOVED'
export type ActionType = 'HOLD' | 'BUY_1' | 'BUY_2' | 'BUY_3' | 'TRIM_HALF' | 'EXIT'
export type Regime = 'GREEN' | 'YELLOW' | 'RED'
export type TrailMode = 'fixed' | 'atr' | 'hybrid'

export interface Position {
  symbol: string
  name: string
  status: PositionStatus
  toppick_score: number
  avg_price: number | null
  weight: number
  deployed_tranches: (1 | 2 | 3)[]
  recent_high: number | null
  trailing_stop_line: number | null
  horizontal_support: number | null
  cooldown_until: string | null
  next_action: ActionType
  reason: string
}

export interface Indicators {
  symbol: string
  date: string
  price: number
  ma50: number
  ma200: number
  atr14: number
  atr_pct: number
  recent_high: number
  horizontal_support: number | null
  vol20ma: number
  vol_ratio: number
  gap50_pct: number
  dist_to_stop_pct: number | null
}

export interface MomentumMarket {
  as_of: string
  regime: Regime
  spx: { close: number; ma50: number; ma200: number }
  ndx: { close: number; ma50: number; ma200: number }
  buy_gate: 'OPEN' | 'CAUTIOUS' | 'BLOCKED'
  vix?: number
  fear_greed?: number
}

export interface Params {
  masam: {
    rebalancing_max_pct: number
    appendix_z: Record<string, boolean>
  }
  momentum: {
    toppick_threshold: number
    max_symbols: number
    tranche_1: number
    tranche_2: number
    tranche_3: number
    reserve: number
    ma50_support_band: number
    trail_mode: TrailMode
    trail_fixed_pct: number
    trail_atr_mult: number
    trail_floor_pct: number
    trail_ceiling_pct: number
    vol_breakout_min: number
    vol_spike_warn: number
    cooldown_days: number
    rescore_cadence: 'monthly' | 'quarterly' | 'semiannual'
  }
}
```

- [ ] **Step 3: 커밋**

```bash
git add app/src/shared/types/
git commit -m "feat: 마삼룰·모멘텀 타입 정의 추가"
```

---

## Task 4: Mock JSON 데이터 파일

**Files:**
- Create: `app/public/data/masam.json`
- Create: `app/public/data/mcap_daily.json`
- Create: `app/public/data/hedge_prices.json`
- Create: `app/public/data/positions.json`
- Create: `app/public/data/indicators.json`
- Create: `app/public/data/momentum_market.json`
- Create: `app/public/data/params.json`
- Create: `app/public/data/live.json`

**Interfaces:**
- Produces: SWR fetch 훅이 읽는 정적 JSON 파일들

- [ ] **Step 1: masam.json 작성**

```json
{
  "as_of": "2026-06-18",
  "mode": "NORMAL",
  "rate_env": "NON_ZERO",
  "qe_active": false,
  "treasury_10y_trend": "UP",
  "masam": {
    "month_count": 0,
    "last_masam_date": "2026-05-21",
    "crisis_end_dday": null,
    "panic_end_dday": null
  },
  "leader_status": {
    "rank1_ticker": "NVDA",
    "rank2_ticker": "MSFT",
    "gap_pct": 18.4,
    "overtake_detected": false,
    "gap_within_10pct": false
  },
  "target_allocation": {
    "stock_pct": 100,
    "hedge_pct": 0,
    "cash_pct": 0,
    "label": "1등주 집중"
  },
  "hedge_allocation": {
    "type": "NONE",
    "rationale": "평상시 — 헤지 불필요",
    "exit_trigger": ""
  },
  "rebalancing": { "cash_raised_pct": 0, "max_pct": 25, "qqq_pct": 0 },
  "staking": { "rate_env": "NON_ZERO", "grid_pct": 5, "target_pct": 50, "deployed_pct": 0 },
  "all_in_conditions": [
    { "id": 1, "label": "한달+1일 무마삼", "met": true, "grade": "약", "detail": "충족" },
    { "id": 2, "label": "8거래일 연속 상승", "met": false, "grade": "중", "detail": "3일 연속" },
    { "id": 3, "label": "1등주 전고 돌파", "met": false, "grade": "강", "detail": "-4.2%" },
    { "id": 4, "label": "나스닥 전고 돌파", "met": false, "grade": "강", "detail": "-2.1%" },
    { "id": 5, "label": "2구간 V자(+10%/+5%)", "met": false, "grade": "중", "detail": "해당없음" },
    { "id": 6, "label": "긴급 올인(-30%/-15%)", "met": false, "grade": "강", "detail": "해당없음" }
  ],
  "additional_buy": { "target": "rank1", "rsi14": 58, "mfi14": 62, "both_below_50": false },
  "panic_hold": { "active": false, "until_new_high": true },
  "panic_reentry": { "stage": 0, "tranches": [35, 35, 30] },
  "recommended_action": "리밸런싱 유지 — 1등주(NVDA) 집중",
  "alerts": []
}
```

- [ ] **Step 2: mcap_daily.json 작성**

```json
{
  "as_of": "2026-06-18",
  "rank1_ticker": "NVDA",
  "items": [
    { "rank": 1, "ticker": "NVDA", "name": "NVIDIA", "mcap_usd": 3420000000000, "gap_pct_from_rank1": 0, "is_leader": true },
    { "rank": 2, "ticker": "MSFT", "name": "Microsoft", "mcap_usd": 2890000000000, "gap_pct_from_rank1": 15.5, "is_leader": false },
    { "rank": 3, "ticker": "AAPL", "name": "Apple", "mcap_usd": 2760000000000, "gap_pct_from_rank1": 19.3, "is_leader": false },
    { "rank": 4, "ticker": "AMZN", "name": "Amazon", "mcap_usd": 2340000000000, "gap_pct_from_rank1": 31.6, "is_leader": false },
    { "rank": 5, "ticker": "GOOGL", "name": "Alphabet", "mcap_usd": 2180000000000, "gap_pct_from_rank1": 36.3, "is_leader": false }
  ]
}
```

- [ ] **Step 3: hedge_prices.json 작성**

```json
{
  "as_of": "2026-06-18",
  "TLT": 88.42,
  "IAU": 54.17,
  "GLD": 301.85,
  "TIP": 107.23
}
```

- [ ] **Step 4: positions.json 작성**

```json
{
  "as_of": "2026-06-18",
  "regime": "GREEN",
  "items": [
    {
      "symbol": "NVDA", "name": "NVIDIA",
      "status": "ENTRY_2", "toppick_score": 91,
      "avg_price": 118.40, "weight": 0.70, "deployed_tranches": [1, 2],
      "recent_high": 153.13, "trailing_stop_line": 122.50, "horizontal_support": 110.00,
      "cooldown_until": null,
      "next_action": "HOLD", "reason": "50MA 위 안착, 트레일링 스탑 원거리"
    },
    {
      "symbol": "META", "name": "Meta Platforms",
      "status": "ENTRY_1", "toppick_score": 84,
      "avg_price": 612.30, "weight": 0.20, "deployed_tranches": [1],
      "recent_high": 741.80, "trailing_stop_line": 593.44, "horizontal_support": 580.00,
      "cooldown_until": null,
      "next_action": "HOLD", "reason": "1차 진입 후 보유 중"
    },
    {
      "symbol": "AAPL", "name": "Apple",
      "status": "WATCH", "toppick_score": 76,
      "avg_price": null, "weight": 0, "deployed_tranches": [],
      "recent_high": null, "trailing_stop_line": null, "horizontal_support": 195.00,
      "cooldown_until": null,
      "next_action": "HOLD", "reason": "50MA 하회 — 1차 진입 대기"
    }
  ]
}
```

- [ ] **Step 5: indicators.json 작성**

```json
{
  "as_of": "2026-06-18",
  "items": [
    {
      "symbol": "NVDA", "date": "2026-06-18",
      "price": 136.80, "ma50": 128.40, "ma200": 112.30,
      "atr14": 6.42, "atr_pct": 0.047,
      "recent_high": 153.13, "horizontal_support": 110.00,
      "vol20ma": 285000000, "vol_ratio": 1.12,
      "gap50_pct": 6.5, "dist_to_stop_pct": 10.5
    },
    {
      "symbol": "META", "date": "2026-06-18",
      "price": 698.40, "ma50": 672.10, "ma200": 601.50,
      "atr14": 18.30, "atr_pct": 0.026,
      "recent_high": 741.80, "horizontal_support": 580.00,
      "vol20ma": 14500000, "vol_ratio": 0.88,
      "gap50_pct": 3.9, "dist_to_stop_pct": 15.0
    },
    {
      "symbol": "AAPL", "date": "2026-06-18",
      "price": 211.20, "ma50": 219.40, "ma200": 208.70,
      "atr14": 4.10, "atr_pct": 0.019,
      "recent_high": 237.23, "horizontal_support": 195.00,
      "vol20ma": 58000000, "vol_ratio": 0.74,
      "gap50_pct": -3.7, "dist_to_stop_pct": null
    }
  ]
}
```

- [ ] **Step 6: momentum_market.json 작성**

```json
{
  "as_of": "2026-06-18",
  "regime": "GREEN",
  "spx": { "close": 5842.10, "ma50": 5612.30, "ma200": 5240.80 },
  "ndx": { "close": 21384.50, "ma50": 20410.20, "ma200": 19120.40 },
  "buy_gate": "OPEN",
  "vix": 14.8,
  "fear_greed": 62
}
```

- [ ] **Step 7: params.json 작성**

```json
{
  "masam": {
    "rebalancing_max_pct": 25,
    "appendix_z": {
      "B4_trigger_grade": true,
      "D2_1_vix_fg_panel": true,
      "B1_dynamic_masam": false,
      "C1_emergency_split": false,
      "C2_allin_relax": false,
      "C4_stoploss": false
    }
  },
  "momentum": {
    "toppick_threshold": 70,
    "max_symbols": 15,
    "tranche_1": 0.30,
    "tranche_2": 0.40,
    "tranche_3": 0.20,
    "reserve": 0.10,
    "ma50_support_band": 0.03,
    "trail_mode": "hybrid",
    "trail_fixed_pct": 0.20,
    "trail_atr_mult": 5.0,
    "trail_floor_pct": 0.15,
    "trail_ceiling_pct": 0.30,
    "vol_breakout_min": 1.30,
    "vol_spike_warn": 1.50,
    "cooldown_days": 5,
    "rescore_cadence": "quarterly"
  }
}
```

- [ ] **Step 8: live.json 작성**

```json
{
  "as_of": "2026-06-18T15:32:00Z",
  "nasdaq": { "price": 19842.30, "change_pct": 0.84, "dist_to_masam_pct": 2.18 },
  "rank1": { "ticker": "NVDA", "price": 136.80, "change_pct": 1.24 },
  "hedges": { "TLT": 88.42, "IAU": 54.17, "GLD": 301.85, "TIP": 107.23 }
}
```

- [ ] **Step 9: 커밋**

```bash
git add app/public/data/
git commit -m "feat: mock JSON 데이터 파일 추가"
```

---

## Task 5: FRED 데이터 수집 스크립트

**Files:**
- Create: `scripts/fetch_fred.py`

**Interfaces:**
- Consumes: `FRED_API_KEY` 환경변수
- Produces: `app/public/data/masam_market.json` (실데이터 덮어쓰기)

- [ ] **Step 1: fetch_fred.py 작성**

```python
# scripts/fetch_fred.py
"""FRED API → app/public/data/masam_market.json"""

import os, json, sys
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request

API_KEY = os.environ.get("FRED_API_KEY", "")
if not API_KEY:
    sys.exit("FRED_API_KEY 환경변수를 설정하세요")

OUT = Path(__file__).parent.parent / "app/public/data/masam_market.json"
BASE = "https://api.stlouisfed.org/fred/series/observations"

def fetch(series: str, limit: int = 60) -> list[dict]:
    url = (f"{BASE}?series_id={series}&api_key={API_KEY}"
           f"&file_type=json&sort_order=desc&limit={limit}")
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())["observations"]

def latest_value(obs: list[dict]) -> float | None:
    for o in obs:
        try:
            v = float(o["value"])
            return v
        except (ValueError, KeyError):
            continue
    return None

def slope_sign(obs: list[dict], n: int = 20) -> str:
    vals = []
    for o in obs:
        try:
            vals.append(float(o["value"]))
        except (ValueError, KeyError):
            continue
        if len(vals) >= n:
            break
    if len(vals) < 2:
        return "UNKNOWN"
    return "DOWN" if vals[0] < vals[-1] else "UP"

def main():
    print("FRED 데이터 수집 중...")
    dff_obs  = fetch("DFF",   10)
    dgs_obs  = fetch("DGS10", 30)
    walcl_obs = fetch("WALCL", 8)

    dff   = latest_value(dff_obs) or 0.0
    dgs10 = latest_value(dgs_obs) or 0.0

    # QE: WALCL 4주 이동평균 기울기
    walcl_vals = []
    for o in walcl_obs:
        try:
            walcl_vals.append(float(o["value"]))
        except (ValueError, KeyError):
            continue
    if len(walcl_vals) >= 2:
        ma4_recent = sum(walcl_vals[:4]) / min(4, len(walcl_vals[:4]))
        ma4_prev   = sum(walcl_vals[4:8]) / min(4, len(walcl_vals[4:8]))
        qe_active  = ma4_recent > ma4_prev
        walcl_trend = "UP" if qe_active else "DOWN"
    else:
        qe_active, walcl_trend = False, "UNKNOWN"

    rate_env = "ZERO" if dff <= 0.25 else "NON_ZERO"
    t10_trend = slope_sign(dgs_obs, 20)

    # 기존 파일에서 표시용 필드 유지
    existing = {}
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text())
        except Exception:
            pass

    result = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d"),
        "rate_env": rate_env,
        "dff": round(dff, 4),
        "qe_active": qe_active,
        "walcl_trend": walcl_trend,
        "treasury_10y": round(dgs10, 4),
        "treasury_10y_trend": t10_trend,
        "vix": existing.get("vix"),
        "fear_greed": existing.get("fear_greed"),
        "usd_krw": existing.get("usd_krw"),
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"완료: {OUT}")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 스크립트 실행 테스트**

```bash
cd "/Users/jubro/Claude Project/Ma3 momentum v2"
FRED_API_KEY=$(grep FRED_API_KEY app/.env.local | cut -d= -f2) python scripts/fetch_fred.py
```
Expected: `app/public/data/masam_market.json`이 실데이터로 갱신됨

- [ ] **Step 3: 커밋**

```bash
git add scripts/fetch_fred.py
git commit -m "feat: FRED 실데이터 수집 스크립트 추가"
```

---

## Task 6: AppContext + SWR 데이터 훅

**Files:**
- Create: `app/src/shared/context/AppContext.tsx`
- Create: `app/src/shared/hooks/useData.ts`
- Create: `app/src/shared/hooks/useData.test.ts`

**Interfaces:**
- Produces: `useAppContext()` → `{ strategy, tab, setStrategy, setTab }`
- Produces: `useMasamData()`, `useMcapDaily()`, `useMomentumPositions()`, `useMomentumMarket()`, `useLiveData()`, `useParams()`

- [ ] **Step 1: 실패 테스트 작성**

```ts
// app/src/shared/hooks/useData.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { useMasamData } from './useData'

global.fetch = jest.fn(() =>
  Promise.resolve({ json: () => Promise.resolve({ as_of: '2026-06-18', mode: 'NORMAL' }) })
) as jest.Mock

test('useMasamData returns data', async () => {
  const { result } = renderHook(() => useMasamData())
  await waitFor(() => expect(result.current.data).toBeDefined())
  expect(result.current.data?.as_of).toBe('2026-06-18')
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd app && npx jest src/shared/hooks/useData.test.ts
```
Expected: FAIL (useMasamData not defined)

- [ ] **Step 3: AppContext.tsx 작성**

```tsx
// app/src/shared/context/AppContext.tsx
'use client'
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

type Strategy = 'masam' | 'momentum'
type Tab = 0 | 1 | 2 | 3

interface AppContextValue {
  strategy: Strategy
  tab: Tab
  setStrategy: (s: Strategy) => void
  setTab: (t: Tab) => void
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [strategy, setStrategyState] = useState<Strategy>('masam')
  const [tab, setTabState] = useState<Tab>(0)

  useEffect(() => {
    const saved = localStorage.getItem('strategy') as Strategy | null
    if (saved) setStrategyState(saved)
  }, [])

  const setStrategy = (s: Strategy) => {
    setStrategyState(s)
    setTabState(0)
    localStorage.setItem('strategy', s)
  }

  return (
    <AppContext.Provider value={{ strategy, tab, setStrategy, setTab: setTabState }}>
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used within AppProvider')
  return ctx
}
```

- [ ] **Step 4: useData.ts 작성**

```ts
// app/src/shared/hooks/useData.ts
import useSWR from 'swr'
import type { MasamData, McapDaily, HedgePrices, MasamMarket, LiveData } from '../types/masam'
import type { Position, Indicators, MomentumMarket, Params } from '../types/momentum'

const fetcher = (url: string) => fetch(url).then(r => r.json())

export const useMasamData = () =>
  useSWR<MasamData>('/data/masam.json', fetcher, { refreshInterval: 60_000 })

export const useMcapDaily = () =>
  useSWR<McapDaily>('/data/mcap_daily.json', fetcher, { refreshInterval: 60_000 })

export const useHedgePrices = () =>
  useSWR<HedgePrices>('/data/hedge_prices.json', fetcher, { refreshInterval: 60_000 })

export const useMasamMarket = () =>
  useSWR<MasamMarket>('/data/masam_market.json', fetcher, { refreshInterval: 300_000 })

export const useLiveData = () =>
  useSWR<LiveData>('/data/live.json', fetcher, { refreshInterval: 30_000 })

export const useMomentumPositions = () =>
  useSWR<{ as_of: string; regime: string; items: Position[] }>(
    '/data/positions.json', fetcher, { refreshInterval: 60_000 }
  )

export const useMomentumIndicators = () =>
  useSWR<{ as_of: string; items: Indicators[] }>(
    '/data/indicators.json', fetcher, { refreshInterval: 60_000 }
  )

export const useMomentumMarket = () =>
  useSWR<MomentumMarket>('/data/momentum_market.json', fetcher, { refreshInterval: 60_000 })

export const useParams = () =>
  useSWR<Params>('/data/params.json', fetcher)
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
npx jest src/shared/hooks/useData.test.ts
```
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add app/src/shared/
git commit -m "feat: AppContext + SWR 데이터 훅 추가"
```

---

## Task 7: 공통 UI 프리미티브 컴포넌트

**Files:**
- Create: `app/src/shared/components/Card.tsx`
- Create: `app/src/shared/components/Badge.tsx`
- Create: `app/src/shared/components/IndexRoll.tsx`
- Create: `app/src/shared/components/Card.test.tsx`

**Interfaces:**
- Produces: `<Card>`, `<Badge variant>`, `<IndexRoll items>`

- [ ] **Step 1: 실패 테스트 작성**

```tsx
// app/src/shared/components/Card.test.tsx
import { render, screen } from '@testing-library/react'
import { Card } from './Card'

test('Card renders children', () => {
  render(<Card>테스트 내용</Card>)
  expect(screen.getByText('테스트 내용')).toBeInTheDocument()
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
npx jest src/shared/components/Card.test.tsx
```
Expected: FAIL

- [ ] **Step 3: Card.tsx 작성**

```tsx
// app/src/shared/components/Card.tsx
import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  gradient?: boolean
}

export function Card({ children, className = '', gradient = false }: CardProps) {
  if (gradient) {
    return (
      <div className="p-[1.4px] rounded-card gradient-accent">
        <div className={`bg-bg rounded-[14.6px] p-4 ${className}`}>{children}</div>
      </div>
    )
  }
  return (
    <div className={`bg-surface rounded-card px-[17px] py-4 ${className}`}>
      {children}
    </div>
  )
}
```

- [ ] **Step 4: Badge.tsx 작성**

```tsx
// app/src/shared/components/Badge.tsx
const VARIANTS = {
  normal:  'bg-blue/20 text-blue',
  crisis:  'bg-amber/20 text-amber',
  panic:   'bg-up/20 text-up',
  green:   'bg-teal/20 text-teal',
  yellow:  'bg-amber/20 text-amber',
  red:     'bg-up/20 text-up',
  buy:     'bg-teal/20 text-teal',
  sell:    'bg-up/20 text-up',
  hold:    'bg-surface-2 text-txt-2',
  watch:   'bg-purple/20 text-purple',
} as const

type Variant = keyof typeof VARIANTS

interface BadgeProps {
  variant: Variant
  children: React.ReactNode
  className?: string
}

export function Badge({ variant, children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-600 ${VARIANTS[variant]} ${className}`}>
      {children}
    </span>
  )
}
```

- [ ] **Step 5: IndexRoll.tsx 작성**

```tsx
// app/src/shared/components/IndexRoll.tsx
'use client'
import { useState, useEffect } from 'react'

interface IndexItem {
  label: string
  value: string
  changePct: number
}

export function IndexRoll({ items, intervalMs = 3000 }: { items: IndexItem[]; intervalMs?: number }) {
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    if (items.length <= 1) return
    const t = setInterval(() => setIdx(i => (i + 1) % items.length), intervalMs)
    return () => clearInterval(t)
  }, [items.length, intervalMs])

  const item = items[idx]
  if (!item) return null

  return (
    <div className="flex items-baseline gap-1.5 text-[11.9px] font-500 text-txt-2">
      <span className="text-txt font-700">{item.label}</span>
      <span className="font-700">{item.value}</span>
      <span className={item.changePct >= 0 ? 'text-up' : 'text-down'}>
        {item.changePct >= 0 ? '+' : ''}{item.changePct.toFixed(2)}%
      </span>
    </div>
  )
}
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
npx jest src/shared/components/Card.test.tsx
```
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add app/src/shared/components/
git commit -m "feat: 공통 UI 프리미티브 컴포넌트 추가"
```

---

## Task 8: 앱 셸 컴포넌트

**Files:**
- Create: `app/src/shared/components/StrategyToggle.tsx`
- Create: `app/src/shared/components/BottomTabBar.tsx`
- Create: `app/src/shared/components/DisclaimerFooter.tsx`
- Create: `app/src/shared/components/NotificationBell.tsx`
- Create: `app/src/shared/components/StrategyToggle.test.tsx`

**Interfaces:**
- Consumes: `useAppContext()`
- Produces: 앱 셸 상단·하단 고정 UI

- [ ] **Step 1: 실패 테스트 작성**

```tsx
// app/src/shared/components/StrategyToggle.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { StrategyToggle } from './StrategyToggle'
import { AppProvider } from '../context/AppContext'

test('모멘텀 버튼 클릭 시 전략 전환', () => {
  render(<AppProvider><StrategyToggle /></AppProvider>)
  fireEvent.click(screen.getByText('모멘텀'))
  // localStorage에 저장됐는지 확인
  expect(localStorage.getItem('strategy')).toBe('momentum')
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
npx jest src/shared/components/StrategyToggle.test.tsx
```
Expected: FAIL

- [ ] **Step 3: StrategyToggle.tsx 작성**

```tsx
// app/src/shared/components/StrategyToggle.tsx
'use client'
import { useAppContext } from '../context/AppContext'

export function StrategyToggle() {
  const { strategy, setStrategy } = useAppContext()

  return (
    <div className="relative flex bg-[#1e1e26] rounded-[10px] p-[3px] gap-[2px]">
      {(['masam', 'momentum'] as const).map(s => (
        <button
          key={s}
          onClick={() => setStrategy(s)}
          className={`relative z-10 px-3 py-[4.5px] rounded-lg text-xs font-500 transition-colors duration-200 whitespace-nowrap
            ${strategy === s ? 'text-txt' : 'text-txt-3'}`}
        >
          {s === 'masam' ? '마삼룰' : '모멘텀'}
        </button>
      ))}
      <div
        className="absolute top-[3px] bottom-[3px] bg-[#2e2e3a] rounded-lg transition-all duration-250 pointer-events-none"
        style={{
          left: strategy === 'masam' ? '3px' : '50%',
          width: 'calc(50% - 3px)',
        }}
      />
    </div>
  )
}
```

- [ ] **Step 4: BottomTabBar.tsx 작성**

```tsx
// app/src/shared/components/BottomTabBar.tsx
'use client'
import { useAppContext } from '../context/AppContext'

const TABS = {
  masam: ['발견', '관심', '경제지표', '설정'],
  momentum: ['탑픽', '관심종목', '경제지표', '설정'],
} as const

const ICONS = {
  masam: ['ph:compass-bold', 'ph:star-bold', 'ph:chart-line-bold', 'ph:gear-bold'],
  momentum: ['ph:chart-bar-bold', 'ph:briefcase-bold', 'ph:chart-line-bold', 'ph:gear-bold'],
}

export function BottomTabBar() {
  const { strategy, tab, setTab } = useAppContext()
  const labels = TABS[strategy]
  const icons = ICONS[strategy]

  return (
    <nav className="flex border-t border-line bg-bg-deep">
      {labels.map((label, i) => (
        <button
          key={i}
          onClick={() => setTab(i as 0 | 1 | 2 | 3)}
          className={`flex-1 flex flex-col items-center justify-center gap-1 py-2.5 transition-colors
            ${tab === i ? 'text-blue' : 'text-txt-3'}`}
        >
          <span className="iconify text-xl" data-icon={icons[i]} />
          <span className="text-[10px] font-600">{label}</span>
        </button>
      ))}
    </nav>
  )
}
```

- [ ] **Step 5: DisclaimerFooter.tsx 작성**

```tsx
// app/src/shared/components/DisclaimerFooter.tsx
export function DisclaimerFooter() {
  return (
    <div className="px-4 py-2 text-center text-[10px] text-txt-3 bg-bg-deep border-t border-line">
      ⚠️ 투자 권유 아님 · 실거래 전 백테스트 검증
    </div>
  )
}
```

- [ ] **Step 6: NotificationBell.tsx 작성**

```tsx
// app/src/shared/components/NotificationBell.tsx
'use client'

interface Props { count?: number }

export function NotificationBell({ count = 0 }: Props) {
  return (
    <button className="relative p-1">
      <span className="iconify text-xl text-txt-2" data-icon="ph:bell-bold" />
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-up" />
      )}
    </button>
  )
}
```

- [ ] **Step 7: 테스트 통과 확인**

```bash
npx jest src/shared/components/StrategyToggle.test.tsx
```
Expected: PASS

- [ ] **Step 8: 커밋**

```bash
git add app/src/shared/components/
git commit -m "feat: 앱 셸 컴포넌트 추가 (토글·탭바·면책·알림)"
```

---

## Task 9: App Layout + Page 라우팅

**Files:**
- Modify: `app/src/app/layout.tsx`
- Modify: `app/src/app/page.tsx`
- Create: `app/public/manifest.json`
- Modify: `app/next.config.ts`

**Interfaces:**
- Consumes: `AppProvider`, `StrategyToggle`, `BottomTabBar`, `DisclaimerFooter`
- Consumes: 모든 feature 탭 컴포넌트
- Produces: 완전한 앱 셸 + 탭 라우팅

- [ ] **Step 1: manifest.json 작성**

```json
{
  "name": "Ma3 Momentum",
  "short_name": "Ma3",
  "description": "마삼룰·모멘텀 투자 모니터링",
  "theme_color": "#17171C",
  "background_color": "#17171C",
  "display": "standalone",
  "start_url": "/",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 2: next.config.ts 수정 (PWA 설정)**

```ts
// app/next.config.ts
import type { NextConfig } from 'next'
const withPWA = require('@ducanh2912/next-pwa').default({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  runtimeCaching: [
    {
      urlPattern: /\/data\/.*\.json$/,
      handler: 'NetworkFirst',
      options: { cacheName: 'data-cache', expiration: { maxAgeSeconds: 60 * 60 } },
    },
  ],
})

const nextConfig: NextConfig = { reactStrictMode: true }
export default withPWA(nextConfig)
```

- [ ] **Step 3: layout.tsx 수정**

```tsx
// app/src/app/layout.tsx
import type { Metadata } from 'next'
import './globals.css'
import { AppProvider } from '@/shared/context/AppContext'

export const metadata: Metadata = {
  title: 'Ma3 Momentum',
  description: '마삼룰·모멘텀 투자 모니터링',
  manifest: '/manifest.json',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          as="style"
          crossOrigin="anonymous"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css"
        />
        <script src="https://code.iconify.design/3/3.1.1/iconify.min.js" async />
      </head>
      <body>
        <AppProvider>
          <div className="w-full h-full max-w-app mx-auto bg-bg flex flex-col shadow-2xl">
            {children}
          </div>
        </AppProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 4: page.tsx 작성**

```tsx
// app/src/app/page.tsx
'use client'
import { useAppContext } from '@/shared/context/AppContext'
import { StrategyToggle } from '@/shared/components/StrategyToggle'
import { BottomTabBar } from '@/shared/components/BottomTabBar'
import { DisclaimerFooter } from '@/shared/components/DisclaimerFooter'
import { NotificationBell } from '@/shared/components/NotificationBell'

// 마삼룰 탭
import { DiscoveryTab } from '@/features/masam/components/DiscoveryTab'
import { WatchlistTab as MasamWatchlist } from '@/features/masam/components/WatchlistTab'
import { MarketTab as MasamMarket } from '@/features/masam/components/MarketTab'
import { SettingsTab as MasamSettings } from '@/features/masam/components/SettingsTab'

// 모멘텀 탭
import { ToppickTab } from '@/features/momentum/components/ToppickTab'
import { PortfolioTab } from '@/features/momentum/components/PortfolioTab'
import { MarketTab as MomentumMarket } from '@/features/momentum/components/MarketTab'
import { SettingsTab as MomentumSettings } from '@/features/momentum/components/SettingsTab'

const MASAM_TABS = [DiscoveryTab, MasamWatchlist, MasamMarket, MasamSettings]
const MOMENTUM_TABS = [ToppickTab, PortfolioTab, MomentumMarket, MomentumSettings]

export default function Page() {
  const { strategy, tab } = useAppContext()
  const tabs = strategy === 'masam' ? MASAM_TABS : MOMENTUM_TABS
  const ActiveTab = tabs[tab]

  return (
    <>
      {/* 상단 바 */}
      <header className="flex items-center justify-between px-[17px] pt-[env(safe-area-inset-top,0px)] pt-3 pb-1 flex-shrink-0">
        <StrategyToggle />
        <NotificationBell />
      </header>

      {/* 탭 콘텐츠 */}
      <main className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide min-h-0">
        <ActiveTab />
      </main>

      {/* 하단 고정 */}
      <DisclaimerFooter />
      <BottomTabBar />
    </>
  )
}
```

- [ ] **Step 5: dev 서버로 앱 셸 확인**

```bash
cd app && npm run dev
```
브라우저에서 `http://localhost:3000` 열어 토글·탭바·면책 Footer 렌더링 확인.

- [ ] **Step 6: 커밋**

```bash
git add app/src/app/ app/public/manifest.json app/next.config.ts
git commit -m "feat: App Layout + 탭 라우팅 구성"
```

---

## Task 10: 마삼룰 — 발견 탭 (DiscoveryTab)

**Files:**
- Create: `app/src/features/masam/components/DiscoveryTab.tsx`
- Create: `app/src/features/masam/components/DiscoveryTab.test.tsx`

**Interfaces:**
- Consumes: `useMasamData()`, `useLiveData()`, `useMcapDaily()`
- Produces: 현재 모드 배지, 마삼 카운트, 목표 비중 배너, 1등주 구간 테이블

- [ ] **Step 1: 실패 테스트 작성**

```tsx
// app/src/features/masam/components/DiscoveryTab.test.tsx
import { render, screen } from '@testing-library/react'
import { DiscoveryTab } from './DiscoveryTab'

jest.mock('@/shared/hooks/useData', () => ({
  useMasamData: () => ({
    data: {
      as_of: '2026-06-18', mode: 'NORMAL', rate_env: 'NON_ZERO',
      masam: { month_count: 0, last_masam_date: null, crisis_end_dday: null, panic_end_dday: null },
      leader_status: { rank1_ticker: 'NVDA', rank2_ticker: 'MSFT', gap_pct: 18.4, gap_within_10pct: false, overtake_detected: false },
      target_allocation: { stock_pct: 100, hedge_pct: 0, cash_pct: 0, label: '1등주 집중' },
      recommended_action: '리밸런싱 유지',
      all_in_conditions: [],
      panic_hold: { active: false, until_new_high: true },
    }
  }),
  useLiveData: () => ({
    data: { nasdaq: { price: 19842, change_pct: 0.84, dist_to_masam_pct: 2.18 }, rank1: { ticker: 'NVDA', price: 136.80, change_pct: 1.24 } }
  }),
  useMcapDaily: () => ({ data: null }),
}))

test('NORMAL 모드 배지가 렌더링된다', () => {
  render(<DiscoveryTab />)
  expect(screen.getByText('리밸런싱')).toBeInTheDocument()
})

test('추천 액션이 표시된다', () => {
  render(<DiscoveryTab />)
  expect(screen.getByText('리밸런싱 유지')).toBeInTheDocument()
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
npx jest src/features/masam/components/DiscoveryTab.test.tsx
```

- [ ] **Step 3: DiscoveryTab.tsx 구현**

```tsx
// app/src/features/masam/components/DiscoveryTab.tsx
'use client'
import { useMasamData, useLiveData } from '@/shared/hooks/useData'
import { Badge } from '@/shared/components/Badge'
import { Card } from '@/shared/components/Card'

const MODE_LABEL: Record<string, string> = {
  NORMAL: '리밸런싱', CRISIS: '말뚝박기', PANIC: '공황 대기',
}
const MODE_BADGE: Record<string, 'normal' | 'crisis' | 'panic'> = {
  NORMAL: 'normal', CRISIS: 'crisis', PANIC: 'panic',
}

export function DiscoveryTab() {
  const { data: masam } = useMasamData()
  const { data: live } = useLiveData()

  if (!masam) return <div className="p-4 text-txt-3 text-sm">로딩 중...</div>

  const mode = masam.mode
  const nasdaq = live?.nasdaq

  return (
    <div className="px-[17px] pt-4 pb-6 space-y-3">
      {/* 공황 홀드 배너 */}
      {masam.panic_hold.active && (
        <div className="bg-up/10 border border-up/30 rounded-card px-4 py-3 text-sm text-up font-600">
          공황 올인 — 최고점 경신까지 리밸런싱·말뚝 중단
        </div>
      )}

      {/* 현재 국면 카드 */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div>
            <Badge variant={MODE_BADGE[mode]}>{MODE_LABEL[mode]}</Badge>
            <span className="ml-2 text-[11px] text-txt-3 font-500">{mode}</span>
          </div>
          <span className="text-[11px] text-txt-3">{masam.as_of}</span>
        </div>
        <p className="text-sm text-txt-2 font-500">{masam.recommended_action}</p>

        {/* 마삼 카운트 */}
        <div className="mt-3 flex gap-4">
          <div>
            <p className="text-[11px] text-txt-3">이번 달 마삼</p>
            <p className="text-lg font-700 text-txt">{masam.masam.month_count}회</p>
          </div>
          {masam.masam.crisis_end_dday !== null && (
            <div>
              <p className="text-[11px] text-txt-3">위기 해제</p>
              <p className="text-lg font-700 text-up">D-{masam.masam.crisis_end_dday}</p>
            </div>
          )}
          {masam.masam.panic_end_dday !== null && (
            <div>
              <p className="text-[11px] text-txt-3">공황 해제</p>
              <p className="text-lg font-700 text-up">D-{masam.masam.panic_end_dday}</p>
            </div>
          )}
        </div>
      </Card>

      {/* 나스닥 현재값 */}
      {nasdaq && (
        <Card>
          <p className="text-[11px] text-txt-3 mb-1">나스닥 종합</p>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-700">{nasdaq.price.toLocaleString()}</span>
            <span className={`text-sm font-600 ${nasdaq.change_pct >= 0 ? 'text-up' : 'text-down'}`}>
              {nasdaq.change_pct >= 0 ? '+' : ''}{nasdaq.change_pct.toFixed(2)}%
            </span>
          </div>
          <p className="text-[11px] text-txt-3 mt-1">
            마삼(-3%)까지 <span className="text-txt font-600">{nasdaq.dist_to_masam_pct.toFixed(2)}%</span> 남음
          </p>
        </Card>
      )}

      {/* 목표 비중 배너 */}
      <Card gradient>
        <p className="text-[11px] text-txt-3 mb-2">목표 비중</p>
        <div className="flex gap-4">
          <div className="text-center">
            <p className="text-lg font-700 text-txt">{masam.target_allocation.stock_pct}%</p>
            <p className="text-[10px] text-txt-3">주식</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-700 text-txt">{masam.target_allocation.hedge_pct}%</p>
            <p className="text-[10px] text-txt-3">헤지</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-700 text-txt">{masam.target_allocation.cash_pct}%</p>
            <p className="text-[10px] text-txt-3">현금</p>
          </div>
        </div>
        <p className="text-[11px] text-txt-2 mt-2 font-500">{masam.target_allocation.label}</p>
      </Card>

      {/* 1등주 정보 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-2">1등주 현황</p>
        <div className="flex items-center justify-between">
          <div>
            <span className="text-base font-700">🏆 {masam.leader_status.rank1_ticker}</span>
            <span className="ml-2 text-txt-3 text-sm">vs {masam.leader_status.rank2_ticker}</span>
          </div>
          <Badge variant={masam.leader_status.gap_within_10pct ? 'yellow' : 'hold'}>
            격차 {masam.leader_status.gap_pct.toFixed(1)}%
          </Badge>
        </div>
        {masam.leader_status.overtake_detected && (
          <p className="mt-2 text-xs text-amber">⚠️ 1·2등 역전 감지 — 1:1 비중으로 조정</p>
        )}
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest src/features/masam/components/DiscoveryTab.test.tsx
```
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add app/src/features/masam/components/DiscoveryTab.tsx app/src/features/masam/components/DiscoveryTab.test.tsx
git commit -m "feat: 마삼룰 발견 탭 구현"
```

---

## Task 11: 마삼룰 — 관심·경제지표·설정 탭

**Files:**
- Create: `app/src/features/masam/components/WatchlistTab.tsx`
- Create: `app/src/features/masam/components/MarketTab.tsx`
- Create: `app/src/features/masam/components/SettingsTab.tsx`

**Interfaces:**
- Consumes: `useMcapDaily()`, `useMasamMarket()`, `useMasamData()`, `useParams()`

- [ ] **Step 1: WatchlistTab.tsx 작성**

```tsx
// app/src/features/masam/components/WatchlistTab.tsx
'use client'
import { useMcapDaily, useLiveData } from '@/shared/hooks/useData'
import { Card } from '@/shared/components/Card'

function fmt(n: number) {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `$${(n / 1e9).toFixed(0)}B`
  return `$${n.toLocaleString()}`
}

export function WatchlistTab() {
  const { data: mcap } = useMcapDaily()
  const { data: live } = useLiveData()

  if (!mcap) return <div className="p-4 text-txt-3 text-sm">로딩 중...</div>

  return (
    <div className="px-[17px] pt-4 pb-6 space-y-3">
      {/* 롤: 환율/VIX */}
      <div className="flex gap-3 text-[11.9px] text-txt-2 font-500">
        <span>USD/KRW <span className="text-txt font-700">1,382</span></span>
        <span>VIX <span className="text-txt font-700">14.8</span></span>
      </div>

      {/* 시총 순위 */}
      <div className="space-y-2">
        {mcap.items.map(item => (
          <Card key={item.ticker} className={item.is_leader ? 'border border-blue/30' : ''}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-txt-3 text-[11px] w-4">{item.rank}</span>
                {item.is_leader && <span>🏆</span>}
                <div>
                  <p className="font-700 text-sm">{item.ticker}</p>
                  <p className="text-[11px] text-txt-3">{item.name}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-600 text-sm">{fmt(item.mcap_usd)}</p>
                {!item.is_leader && (
                  <p className="text-[11px] text-txt-3">1위 대비 -{item.gap_pct_from_rank1.toFixed(1)}%</p>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: MarketTab.tsx 작성 (경제지표 — 금리·QE·헤지·올인 체크리스트)**

```tsx
// app/src/features/masam/components/MarketTab.tsx
'use client'
import { useMasamMarket, useMasamData } from '@/shared/hooks/useData'
import { Badge } from '@/shared/components/Badge'
import { Card } from '@/shared/components/Card'

const GRADE_COLOR = { '약': 'text-txt-2', '중': 'text-amber', '강': 'text-up' } as const

export function MarketTab() {
  const { data: market } = useMasamMarket()
  const { data: masam } = useMasamData()

  if (!market || !masam) return <div className="p-4 text-txt-3 text-sm">로딩 중...</div>

  return (
    <div className="px-[17px] pt-4 pb-6 space-y-3">
      {/* 금리 환경 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-3">금리 환경</p>
        <div className="flex gap-4">
          <div>
            <p className="text-[11px] text-txt-3">기준금리(DFF)</p>
            <p className="text-lg font-700">{market.dff.toFixed(2)}%</p>
            <Badge variant={market.rate_env === 'ZERO' ? 'green' : 'crisis'}>
              {market.rate_env === 'ZERO' ? '제로금리' : '비제로금리'}
            </Badge>
          </div>
          <div>
            <p className="text-[11px] text-txt-3">10Y 국채(DGS10)</p>
            <p className="text-lg font-700">{market.treasury_10y.toFixed(2)}%</p>
            <p className="text-[11px] text-txt-2">추세: {market.treasury_10y_trend === 'DOWN' ? '↓ 하락' : market.treasury_10y_trend === 'UP' ? '↑ 상승' : '? 미상'}</p>
          </div>
        </div>
      </Card>

      {/* QE */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] text-txt-3 mb-1">연준 총자산(WALCL)</p>
            <Badge variant={market.qe_active ? 'buy' : 'hold'}>
              {market.qe_active ? 'QE ON' : 'QE OFF'}
            </Badge>
          </div>
          <div className="text-right">
            <p className="text-[11px] text-txt-3">추세</p>
            <p className="text-sm font-600">{market.walcl_trend === 'UP' ? '↑ 확대' : market.walcl_trend === 'DOWN' ? '↓ 축소' : '? 미상'}</p>
          </div>
        </div>
      </Card>

      {/* 헤지 배치 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-2">헤지 배치 (자동)</p>
        <p className="font-600 text-sm">{masam.hedge_allocation.type}</p>
        <p className="text-[11px] text-txt-2 mt-1">{masam.hedge_allocation.rationale}</p>
      </Card>

      {/* 추가 자금 투입 조건 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-2">추가 자금 투입 조건 (RSI+MFI)</p>
        <div className="flex gap-4">
          <div>
            <p className="text-[11px] text-txt-3">RSI14</p>
            <p className={`text-lg font-700 ${masam.additional_buy.rsi14 <= 50 ? 'text-teal' : 'text-txt'}`}>
              {masam.additional_buy.rsi14}
            </p>
          </div>
          <div>
            <p className="text-[11px] text-txt-3">MFI14</p>
            <p className={`text-lg font-700 ${masam.additional_buy.mfi14 <= 50 ? 'text-teal' : 'text-txt'}`}>
              {masam.additional_buy.mfi14}
            </p>
          </div>
          <div className="ml-auto flex items-center">
            <Badge variant={masam.additional_buy.both_below_50 ? 'buy' : 'hold'}>
              {masam.additional_buy.both_below_50 ? '투입 가능' : '대기'}
            </Badge>
          </div>
        </div>
      </Card>

      {/* 올인 체크리스트 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-3">올인 체크리스트</p>
        <div className="space-y-2">
          {masam.all_in_conditions.map(c => (
            <div key={c.id} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span>{c.met ? '✅' : '⬜'}</span>
                <span className="text-sm font-500">{c.label}</span>
                <span className={`text-[10px] font-600 ${GRADE_COLOR[c.grade]}`}>{c.grade}</span>
              </div>
              {c.detail && <span className="text-[11px] text-txt-3">{c.detail}</span>}
            </div>
          ))}
        </div>
      </Card>

      {/* 경제지표 표시 */}
      {(market.vix || market.fear_greed) && (
        <Card>
          <p className="text-[11px] text-txt-3 mb-2">참고 지표 (표시용)</p>
          <div className="flex gap-4">
            {market.vix && <div><p className="text-[11px] text-txt-3">VIX</p><p className="font-700">{market.vix}</p></div>}
            {market.fear_greed && <div><p className="text-[11px] text-txt-3">공포탐욕</p><p className="font-700">{market.fear_greed}</p></div>}
          </div>
        </Card>
      )}
    </div>
  )
}
```

- [ ] **Step 3: SettingsTab.tsx 작성**

```tsx
// app/src/features/masam/components/SettingsTab.tsx
'use client'
import { useState } from 'react'
import { useParams } from '@/shared/hooks/useData'
import { Card } from '@/shared/components/Card'

const APPENDIX_Z_LABELS: Record<string, { label: string; conflict: boolean }> = {
  B4_trigger_grade:  { label: 'B-4 트리거 등급 표시', conflict: false },
  D2_1_vix_fg_panel: { label: 'D-2-1 VIX·F&G 참고 패널', conflict: false },
  B1_dynamic_masam:  { label: 'B-1 마삼 동적 기준(VIX/ATR)', conflict: true },
  C1_emergency_split:{ label: 'C-1 긴급 올인 분할', conflict: true },
  C2_allin_relax:    { label: 'C-2 올인 구조 완화', conflict: true },
  C4_stoploss:       { label: 'C-4 손절 (원본 충돌⚠️)', conflict: true },
}

export function SettingsTab() {
  const { data: params } = useParams()
  const [rebMax, setRebMax] = useState<25 | 50>(25)
  const [appendixZ, setAppendixZ] = useState<Record<string, boolean>>(
    params?.masam.appendix_z ?? {}
  )

  const toggle = (key: string) => {
    setAppendixZ(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="px-[17px] pt-4 pb-6 space-y-3">
      {/* 리밸런싱 한도 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-3">리밸런싱 한도</p>
        <div className="flex gap-2">
          {([25, 50] as const).map(v => (
            <button
              key={v}
              onClick={() => setRebMax(v)}
              className={`flex-1 py-2 rounded-xl text-sm font-600 transition-colors
                ${rebMax === v ? 'bg-blue text-white' : 'bg-surface-2 text-txt-2'}`}
            >
              최대 {v}%
            </button>
          ))}
        </div>
      </Card>

      {/* 부록 Z 옵션 토글 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-1">부록 Z 옵션</p>
        <p className="text-[10px] text-txt-3 mb-3">기본 OFF · 백테스트 검증 후 활성화 권장</p>
        <div className="space-y-3">
          {Object.entries(APPENDIX_Z_LABELS).map(([key, { label, conflict }]) => (
            <div key={key}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-500">{label}</span>
                <button
                  onClick={() => toggle(key)}
                  className={`w-11 h-6 rounded-full transition-colors ${appendixZ[key] ? 'bg-blue' : 'bg-surface-2'}`}
                >
                  <span className={`block w-5 h-5 bg-white rounded-full shadow transition-transform m-0.5
                    ${appendixZ[key] ? 'translate-x-5' : 'translate-x-0'}`} />
                </button>
              </div>
              {conflict && appendixZ[key] && (
                <p className="text-[10px] text-up mt-1">⚠️ 원본 룰 변경 — 백테스트 필수</p>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: 커밋**

```bash
git add app/src/features/masam/components/
git commit -m "feat: 마삼룰 관심·경제지표·설정 탭 구현"
```

---

## Task 12: 모멘텀 — 탑픽 탭 (ToppickTab)

**Files:**
- Create: `app/src/features/momentum/components/ToppickTab.tsx`
- Create: `app/src/features/momentum/components/ToppickTab.test.tsx`

**Interfaces:**
- Consumes: `useMomentumPositions()`, `useMomentumIndicators()`
- Produces: 필터칩, 탑픽 카드 (점수·상태·이격·스탑선·추천 액션)

- [ ] **Step 1: 실패 테스트 작성**

```tsx
// app/src/features/momentum/components/ToppickTab.test.tsx
import { render, screen } from '@testing-library/react'
import { ToppickTab } from './ToppickTab'

jest.mock('@/shared/hooks/useData', () => ({
  useMomentumPositions: () => ({
    data: {
      as_of: '2026-06-18', regime: 'GREEN',
      items: [
        { symbol: 'NVDA', name: 'NVIDIA', status: 'ENTRY_2', toppick_score: 91,
          avg_price: 118.40, weight: 0.70, deployed_tranches: [1, 2],
          recent_high: 153.13, trailing_stop_line: 122.50, horizontal_support: 110.00,
          cooldown_until: null, next_action: 'HOLD', reason: '보유 중' }
      ]
    }
  }),
  useMomentumIndicators: () => ({
    data: {
      items: [
        { symbol: 'NVDA', price: 136.80, ma50: 128.40, ma200: 112.30,
          vol_ratio: 1.12, gap50_pct: 6.5, dist_to_stop_pct: 10.5 }
      ]
    }
  }),
}))

test('종목 카드가 렌더링된다', () => {
  render(<ToppickTab />)
  expect(screen.getByText('NVDA')).toBeInTheDocument()
})

test('탑픽 점수가 표시된다', () => {
  render(<ToppickTab />)
  expect(screen.getByText('91')).toBeInTheDocument()
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
npx jest src/features/momentum/components/ToppickTab.test.tsx
```

- [ ] **Step 3: ToppickTab.tsx 작성**

```tsx
// app/src/features/momentum/components/ToppickTab.tsx
'use client'
import { useState } from 'react'
import { useMomentumPositions, useMomentumIndicators } from '@/shared/hooks/useData'
import { Badge } from '@/shared/components/Badge'
import { Card } from '@/shared/components/Card'
import type { PositionStatus, ActionType } from '@/shared/types/momentum'

type Filter = 'all' | 'buyable' | 'holding' | 'sell'

const STATUS_BADGE: Record<PositionStatus, string> = {
  WATCH: 'watch', ENTRY_1: 'buy', ENTRY_2: 'buy', ENTRY_3: 'buy',
  TRIM: 'sell', EXIT: 'sell', REMOVED: 'sell',
} as const

const ACTION_LABEL: Record<ActionType, string> = {
  HOLD: '보유', BUY_1: '1차 매수', BUY_2: '2차 줍줍', BUY_3: '3차 줍줍',
  TRIM_HALF: '절반 축소', EXIT: '청산',
}

const ACTION_VARIANT: Record<ActionType, string> = {
  HOLD: 'hold', BUY_1: 'buy', BUY_2: 'buy', BUY_3: 'yellow',
  TRIM_HALF: 'crisis', EXIT: 'sell',
} as const

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: '전체' },
  { key: 'buyable', label: '매수 후보' },
  { key: 'holding', label: '보유' },
  { key: 'sell', label: '매도 신호' },
]

function matchFilter(status: PositionStatus, filter: Filter): boolean {
  if (filter === 'all') return true
  if (filter === 'buyable') return status === 'WATCH'
  if (filter === 'holding') return ['ENTRY_1', 'ENTRY_2', 'ENTRY_3', 'TRIM'].includes(status)
  if (filter === 'sell') return ['TRIM', 'EXIT', 'REMOVED'].includes(status)
  return true
}

export function ToppickTab() {
  const { data: positions } = useMomentumPositions()
  const { data: indicatorsData } = useMomentumIndicators()
  const [filter, setFilter] = useState<Filter>('all')

  if (!positions) return <div className="p-4 text-txt-3 text-sm">로딩 중...</div>

  const indMap = Object.fromEntries(
    (indicatorsData?.items ?? []).map(i => [i.symbol, i])
  )

  const filtered = positions.items.filter(p => matchFilter(p.status, filter))

  return (
    <div className="flex flex-col h-full">
      {/* 국면 배지 */}
      <div className="px-[17px] pt-4 pb-2 flex items-center gap-2">
        <Badge variant={positions.regime.toLowerCase() as 'green' | 'yellow' | 'red'}>
          {positions.regime}
        </Badge>
        <span className="text-[11px] text-txt-3">{positions.as_of} 기준</span>
      </div>

      {/* 필터칩 */}
      <div className="px-[17px] pb-3 flex gap-2 overflow-x-auto scrollbar-hide">
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-600 transition-colors
              ${filter === f.key ? 'bg-blue text-white' : 'bg-surface-2 text-txt-2'}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* 종목 카드 목록 */}
      <div className="px-[17px] pb-6 space-y-3 overflow-y-auto scrollbar-hide flex-1">
        {filtered.map(pos => {
          const ind = indMap[pos.symbol]
          return (
            <Card key={pos.symbol}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-700 text-base">{pos.symbol}</span>
                    <Badge variant={STATUS_BADGE[pos.status] as any}>{pos.status}</Badge>
                  </div>
                  <p className="text-[11px] text-txt-3 mt-0.5">{pos.name}</p>
                </div>
                {/* 탑픽 점수 */}
                <div className="text-right">
                  <p className="text-2xl font-800 text-blue">{pos.toppick_score}</p>
                  <p className="text-[10px] text-txt-3">탑픽 점수</p>
                </div>
              </div>

              {ind && (
                <div className="flex gap-3 text-[11px] text-txt-2 mb-2">
                  <span>현재가 <span className="text-txt font-600">{ind.price.toLocaleString()}</span></span>
                  <span>50MA 이격 <span className={`font-600 ${ind.gap50_pct >= 0 ? 'text-up' : 'text-down'}`}>
                    {ind.gap50_pct >= 0 ? '+' : ''}{ind.gap50_pct.toFixed(1)}%
                  </span></span>
                  {ind.dist_to_stop_pct && (
                    <span>스탑까지 <span className="text-txt font-600">{ind.dist_to_stop_pct.toFixed(1)}%</span></span>
                  )}
                </div>
              )}

              {/* 집행 트랜치 */}
              {pos.deployed_tranches.length > 0 && (
                <div className="flex gap-1 mb-2">
                  {[1, 2, 3].map(t => (
                    <span
                      key={t}
                      className={`w-6 h-6 rounded-full text-[10px] font-700 flex items-center justify-center
                        ${pos.deployed_tranches.includes(t as 1|2|3)
                          ? 'bg-blue text-white'
                          : 'bg-surface-2 text-txt-3'}`}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}

              {/* 거래량 경보 */}
              {ind && ind.vol_ratio >= 1.5 && (
                <p className="text-[10px] text-up mb-2">⚠️ 매도압력 급증 (거래량 ×{ind.vol_ratio.toFixed(2)})</p>
              )}

              {/* 추천 액션 */}
              <div className="flex items-center justify-between">
                <Badge variant={ACTION_VARIANT[pos.next_action] as any}>
                  {ACTION_LABEL[pos.next_action]}
                </Badge>
                <p className="text-[10px] text-txt-3">{pos.reason}</p>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npx jest src/features/momentum/components/ToppickTab.test.tsx
```
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add app/src/features/momentum/components/ToppickTab.tsx app/src/features/momentum/components/ToppickTab.test.tsx
git commit -m "feat: 모멘텀 탑픽 탭 구현"
```

---

## Task 13: 모멘텀 — 관심종목·경제지표·설정 탭

**Files:**
- Create: `app/src/features/momentum/components/PortfolioTab.tsx`
- Create: `app/src/features/momentum/components/MarketTab.tsx`
- Create: `app/src/features/momentum/components/SettingsTab.tsx`

**Interfaces:**
- Consumes: `useMomentumPositions()`, `useMomentumMarket()`, `useParams()`

- [ ] **Step 1: PortfolioTab.tsx 작성**

```tsx
// app/src/features/momentum/components/PortfolioTab.tsx
'use client'
import { useMomentumPositions, useMomentumIndicators } from '@/shared/hooks/useData'
import { Badge } from '@/shared/components/Badge'
import { Card } from '@/shared/components/Card'

export function PortfolioTab() {
  const { data: positions } = useMomentumPositions()
  const { data: indData } = useMomentumIndicators()

  if (!positions) return <div className="p-4 text-txt-3 text-sm">로딩 중...</div>

  const holding = positions.items.filter(p =>
    ['ENTRY_1', 'ENTRY_2', 'ENTRY_3', 'TRIM'].includes(p.status)
  )
  const sellSignal = positions.items.filter(p =>
    ['TRIM', 'EXIT', 'REMOVED'].includes(p.status)
  )
  const indMap = Object.fromEntries((indData?.items ?? []).map(i => [i.symbol, i]))

  return (
    <div className="px-[17px] pt-4 pb-6 space-y-3">
      {/* 무한보유 강조 배너 */}
      <div className="bg-teal/10 border border-teal/30 rounded-card px-4 py-2.5 text-[11px] text-teal font-500">
        📌 무한 보유 원칙 — 추세 유지 시 상승률 익절 없음
      </div>

      {/* 매도 신호 탭 */}
      {sellSignal.length > 0 && (
        <Card className="border border-up/30">
          <p className="text-[11px] text-up font-600 mb-2">🔴 매도 신호</p>
          {sellSignal.map(pos => (
            <div key={pos.symbol} className="flex justify-between items-center py-1">
              <span className="font-600">{pos.symbol}</span>
              <Badge variant="sell">{pos.next_action}</Badge>
            </div>
          ))}
        </Card>
      )}

      {/* 보유 포지션 */}
      {holding.map(pos => {
        const ind = indMap[pos.symbol]
        return (
          <Card key={pos.symbol}>
            <div className="flex justify-between items-start mb-3">
              <div>
                <p className="font-700 text-base">{pos.symbol}</p>
                <p className="text-[11px] text-txt-3">{pos.name}</p>
              </div>
              <div className="text-right">
                <p className="font-700 text-sm">{(pos.weight * 100).toFixed(0)}%</p>
                <p className="text-[10px] text-txt-3">비중</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-y-2 text-[11px] text-txt-2 mb-3">
              <div>평단 <span className="text-txt font-600">{pos.avg_price?.toFixed(2)}</span></div>
              <div>최고가 <span className="text-txt font-600">{pos.recent_high?.toFixed(2)}</span></div>
              <div>스탑선 <span className="text-up font-600">{pos.trailing_stop_line?.toFixed(2)}</span></div>
              <div>수평지지 <span className="text-txt font-600">{pos.horizontal_support?.toFixed(2)}</span></div>
              {ind && <div>거래량비 <span className={`font-600 ${ind.vol_ratio >= 1.5 ? 'text-up' : 'text-txt'}`}>×{ind.vol_ratio.toFixed(2)}</span></div>}
            </div>

            {/* 트랜치 표시 */}
            <div className="flex gap-1">
              {[1, 2, 3].map(t => (
                <span
                  key={t}
                  className={`flex-1 py-1 rounded-lg text-center text-[10px] font-700
                    ${pos.deployed_tranches.includes(t as 1|2|3)
                      ? 'bg-blue text-white'
                      : 'bg-surface-2 text-txt-3'}`}
                >
                  {t}차 {t === 1 ? '30%' : t === 2 ? '40%' : '20%'}
                </span>
              ))}
            </div>

            {pos.cooldown_until && (
              <p className="mt-2 text-[10px] text-txt-3">쿨다운: {pos.cooldown_until}까지</p>
            )}
          </Card>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: MarketTab.tsx 작성 (모멘텀 국면)**

```tsx
// app/src/features/momentum/components/MarketTab.tsx
'use client'
import { useMomentumMarket } from '@/shared/hooks/useData'
import { Badge } from '@/shared/components/Badge'
import { Card } from '@/shared/components/Card'
import type { Regime } from '@/shared/types/momentum'

const REGIME_BADGE: Record<Regime, 'green' | 'yellow' | 'red'> = {
  GREEN: 'green', YELLOW: 'yellow', RED: 'red',
}
const REGIME_DESC: Record<Regime, string> = {
  GREEN: 'SPX·NDX 모두 200MA 위, 정배열 — 정상 운용',
  YELLOW: '중립 구간 — 1차 진입 보수적 허용',
  RED: 'SPX 또는 NDX 200MA 이탈 — 신규 매수 차단',
}
const GATE_LABEL = { OPEN: '매수 허용', CAUTIOUS: '보수적 허용', BLOCKED: '차단' } as const

export function MarketTab() {
  const { data: market } = useMomentumMarket()

  if (!market) return <div className="p-4 text-txt-3 text-sm">로딩 중...</div>

  return (
    <div className="px-[17px] pt-4 pb-6 space-y-3">
      {/* 국면 */}
      <Card gradient={market.regime === 'GREEN'}>
        <div className="flex items-center gap-3 mb-2">
          <Badge variant={REGIME_BADGE[market.regime]}>{market.regime}</Badge>
          <Badge variant={market.buy_gate === 'OPEN' ? 'buy' : market.buy_gate === 'CAUTIOUS' ? 'yellow' : 'sell'}>
            {GATE_LABEL[market.buy_gate]}
          </Badge>
        </div>
        <p className="text-[11px] text-txt-2">{REGIME_DESC[market.regime]}</p>
      </Card>

      {/* SPX */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-2">S&P 500</p>
        <div className="flex gap-4 text-[11px] text-txt-2">
          <div>종가 <span className="text-txt font-600">{market.spx.close.toLocaleString()}</span></div>
          <div>MA50 <span className="text-txt font-600">{market.spx.ma50.toLocaleString()}</span></div>
          <div>MA200 <span className="text-txt font-600">{market.spx.ma200.toLocaleString()}</span></div>
        </div>
        <div className="flex gap-2 mt-2">
          <Badge variant={market.spx.close > market.spx.ma50 ? 'green' : 'red'}>
            {market.spx.close > market.spx.ma50 ? '50MA 위' : '50MA 아래'}
          </Badge>
          <Badge variant={market.spx.close > market.spx.ma200 ? 'green' : 'red'}>
            {market.spx.close > market.spx.ma200 ? '200MA 위' : '200MA 아래'}
          </Badge>
        </div>
      </Card>

      {/* NDX */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-2">나스닥 100</p>
        <div className="flex gap-4 text-[11px] text-txt-2">
          <div>종가 <span className="text-txt font-600">{market.ndx.close.toLocaleString()}</span></div>
          <div>MA50 <span className="text-txt font-600">{market.ndx.ma50.toLocaleString()}</span></div>
          <div>MA200 <span className="text-txt font-600">{market.ndx.ma200.toLocaleString()}</span></div>
        </div>
        <div className="flex gap-2 mt-2">
          <Badge variant={market.ndx.close > market.ndx.ma50 ? 'green' : 'red'}>
            {market.ndx.close > market.ndx.ma50 ? '50MA 위' : '50MA 아래'}
          </Badge>
          <Badge variant={market.ndx.close > market.ndx.ma200 ? 'green' : 'red'}>
            {market.ndx.close > market.ndx.ma200 ? '200MA 위' : '200MA 아래'}
          </Badge>
        </div>
      </Card>

      {/* 참고 지표 */}
      {(market.vix || market.fear_greed) && (
        <Card>
          <p className="text-[11px] text-txt-3 mb-2">참고 지표 (표시용)</p>
          <div className="flex gap-4">
            {market.vix && <div><p className="text-[11px] text-txt-3">VIX</p><p className="font-700">{market.vix}</p></div>}
            {market.fear_greed && <div><p className="text-[11px] text-txt-3">공포탐욕</p><p className="font-700">{market.fear_greed}</p></div>}
          </div>
        </Card>
      )}
    </div>
  )
}
```

- [ ] **Step 3: SettingsTab.tsx 작성 (모멘텀)**

```tsx
// app/src/features/momentum/components/SettingsTab.tsx
'use client'
import { useState } from 'react'
import { useParams } from '@/shared/hooks/useData'
import { Card } from '@/shared/components/Card'
import type { TrailMode } from '@/shared/types/momentum'

export function SettingsTab() {
  const { data: params } = useParams()
  const cfg = params?.momentum

  const [tranche, setTranche] = useState<'점증형' | '지지집중형' | '균등형'>('점증형')
  const [trailMode, setTrailMode] = useState<TrailMode>('hybrid')
  const [threshold, setThreshold] = useState(70)

  if (!cfg) return <div className="p-4 text-txt-3 text-sm">로딩 중...</div>

  return (
    <div className="px-[17px] pt-4 pb-6 space-y-3">
      {/* 줍줍 비중 방식 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-3">분할 투입 비중 방식</p>
        {(['점증형', '지지집중형', '균등형'] as const).map(v => (
          <button
            key={v}
            onClick={() => setTranche(v)}
            className={`w-full text-left px-3 py-2.5 rounded-xl mb-2 text-sm transition-colors
              ${tranche === v ? 'bg-blue/20 border border-blue text-blue' : 'bg-surface-2 text-txt-2'}`}
          >
            {v === '점증형' ? '점증형 (1차30·2차40·3차20·예비10) — 기본' : v === '지지집중형' ? '지지집중형 (25·50·15·10)' : '균등형 (30·30·30·10)'}
          </button>
        ))}
      </Card>

      {/* 트레일링 스탑 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-3">트레일링 스탑 방식</p>
        {(['fixed', 'atr', 'hybrid'] as const).map(v => (
          <button
            key={v}
            onClick={() => setTrailMode(v)}
            className={`w-full text-left px-3 py-2.5 rounded-xl mb-2 text-sm transition-colors
              ${trailMode === v ? 'bg-blue/20 border border-blue text-blue' : 'bg-surface-2 text-txt-2'}`}
          >
            {v === 'fixed' ? '고정 비율 (-20%)' : v === 'atr' ? '변동성 연동 (ATR×5)' : '혼합 — 기본'}
          </button>
        ))}
      </Card>

      {/* 탑픽 임계 */}
      <Card>
        <p className="text-[11px] text-txt-3 mb-3">탑픽 편입 기준점</p>
        <div className="flex gap-2">
          {[70, 75, 80].map(v => (
            <button
              key={v}
              onClick={() => setThreshold(v)}
              className={`flex-1 py-2 rounded-xl text-sm font-600 transition-colors
                ${threshold === v ? 'bg-blue text-white' : 'bg-surface-2 text-txt-2'}`}
            >
              {v}점
            </button>
          ))}
        </div>
      </Card>

      <p className="text-[10px] text-txt-3 text-center">설정 변경은 다음 평가 주기부터 적용됩니다</p>
    </div>
  )
}
```

- [ ] **Step 4: 커밋**

```bash
git add app/src/features/momentum/components/
git commit -m "feat: 모멘텀 관심종목·경제지표·설정 탭 구현"
```

---

## Task 14: 전체 빌드 검증 + 플레이스홀더 컴포넌트 정리

**Files:**
- Modify: 각 탭 컴포넌트 (빌드 에러 수정)

**Interfaces:**
- Produces: `npm run build` 성공, `npm test` 전체 통과

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd app && npx jest --passWithNoTests
```
Expected: 모든 테스트 PASS

- [ ] **Step 2: 타입 체크**

```bash
npx tsc --noEmit
```
Expected: 에러 없음. 에러 발생 시 각 파일 수정.

- [ ] **Step 3: 프로덕션 빌드**

```bash
npm run build
```
Expected: 빌드 성공. 에러 발생 시 에러 메시지 기반으로 수정.

- [ ] **Step 4: 브라우저 확인**

```bash
npm run dev
```
다음 항목 직접 확인:
- [ ] 마삼룰 ↔ 모멘텀 토글 전환 시 탭 라벨 교체됨
- [ ] 각 탭 클릭 시 내용 교체됨
- [ ] 면책 Footer가 항상 보임
- [ ] localStorage에 전략 저장됨 (새로고침 후 유지)

- [ ] **Step 5: 최종 커밋**

```bash
git add -A
git commit -m "feat: Ma3 Momentum v2 UI 구현 완료"
```

---

## 자기검토 (Spec Coverage)

| 스펙 요구사항 | 담당 태스크 |
|---|---|
| Next.js 14 + TypeScript + Tailwind | Task 1 |
| 디자인 토큰 (#17171C 등) | Task 2 |
| 마삼 타입 / 모멘텀 타입 | Task 3 |
| Mock JSON 9종 | Task 4 |
| FRED 실데이터 스크립트 | Task 5 |
| AppContext (전략·탭 localStorage) | Task 6 |
| SWR 데이터 훅 | Task 6 |
| Card · Badge · IndexRoll | Task 7 |
| StrategyToggle · BottomTabBar | Task 8 |
| DisclaimerFooter 항상 노출 | Task 8, 9 |
| App 셸 layout + page 라우팅 | Task 9 |
| PWA manifest | Task 9 |
| 마삼 발견 탭 (모드·마삼 카운트·목표비중·1등주) | Task 10 |
| 마삼 관심 탭 (시총 순위·격차) | Task 11 |
| 마삼 경제지표 탭 (금리·QE·10Y·헤지·올인 체크리스트) | Task 11 |
| 마삼 설정 탭 (리밸런싱 한도·부록 Z 토글) | Task 11 |
| 모멘텀 탑픽 탭 (필터칩·카드·점수·상태·거래량 경보) | Task 12 |
| 모멘텀 관심종목 탭 (포지션·트랜치·스탑·무한보유 강조) | Task 13 |
| 모멘텀 경제지표 탭 (GREEN/YELLOW/RED·매수 게이트) | Task 13 |
| 모멘텀 설정 탭 (줍줍 비중·트레일링 preset) | Task 13 |
| 전체 빌드·테스트 검증 | Task 14 |
