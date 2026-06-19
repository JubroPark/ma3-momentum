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
