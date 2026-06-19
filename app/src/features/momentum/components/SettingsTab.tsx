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
