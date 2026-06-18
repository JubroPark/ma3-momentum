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
