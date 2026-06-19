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
