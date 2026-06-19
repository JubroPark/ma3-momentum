'use client'
import { useState } from 'react'
import { useMomentumPositions, useMomentumIndicators } from '@/shared/hooks/useData'
import { Badge } from '@/shared/components/Badge'
import { Card } from '@/shared/components/Card'
import type { PositionStatus, ActionType } from '@/shared/types/momentum'

type Filter = 'all' | 'buyable' | 'holding' | 'sell'

const STATUS_BADGE: Record<PositionStatus, 'watch' | 'buy' | 'sell'> = {
  WATCH: 'watch', ENTRY_1: 'buy', ENTRY_2: 'buy', ENTRY_3: 'buy',
  TRIM: 'sell', EXIT: 'sell', REMOVED: 'sell',
}

const ACTION_LABEL: Record<ActionType, string> = {
  HOLD: '보유', BUY_1: '1차 매수', BUY_2: '2차 줍줍', BUY_3: '3차 줍줍',
  TRIM_HALF: '절반 축소', EXIT: '청산',
}

const ACTION_VARIANT: Record<ActionType, 'hold' | 'buy' | 'yellow' | 'crisis' | 'sell'> = {
  HOLD: 'hold', BUY_1: 'buy', BUY_2: 'buy', BUY_3: 'yellow',
  TRIM_HALF: 'crisis', EXIT: 'sell',
}

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
                    <Badge variant={STATUS_BADGE[pos.status]}>{pos.status}</Badge>
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
                  {ind.dist_to_stop_pct != null && (
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
                        ${pos.deployed_tranches.includes(t as 1 | 2 | 3)
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
                <p className="text-[10px] text-up mb-2">매도압력 급증 (거래량 x{ind.vol_ratio.toFixed(2)})</p>
              )}

              {/* 추천 액션 */}
              <div className="flex items-center justify-between">
                <Badge variant={ACTION_VARIANT[pos.next_action]}>
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
