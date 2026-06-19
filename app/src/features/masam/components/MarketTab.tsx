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
