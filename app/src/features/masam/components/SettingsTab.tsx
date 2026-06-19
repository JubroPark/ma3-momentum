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
