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
