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
