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
