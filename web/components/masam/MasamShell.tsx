'use client';
import { useState } from 'react';
import { useMasam } from '@/hooks/useMasam';
import PhaseTab from './PhaseTab';
import GridTab from './GridTab';
import GuideTab from './GuideTab';
import MasamMarketTab from './MasamMarketTab';

type MasamTab = 'phase' | 'grid' | 'guide' | 'market';

const TAB_LABEL: Record<MasamTab, string> = {
  phase:  '현재 국면',
  grid:   '구간 현황',
  guide:  '행동 가이드',
  market: '시장환경/설정',
};

export default function MasamShell() {
  const [tab, setTab] = useState<MasamTab>('phase');
  const { data } = useMasam();

  const isPanicEmergency = data?.mode === 'PANIC_EMERGENCY';

  return (
    <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 80 }}>
      {isPanicEmergency && (
        <div style={{
          background: 'rgba(240,68,82,.15)', borderRadius: 12,
          margin: '12px 20px 0', padding: '12px 16px',
          fontSize: 13, fontWeight: 700, color: 'var(--up)',
        }}>
          ⚠️ 공황 비상 — 고점 -30% 몰빵 없음 · V자 6구간 기준 적용 중
        </div>
      )}

      {/* 탭 내비게이션 */}
      <div className="tiles" style={{ paddingTop: 16 }}>
        {(Object.keys(TAB_LABEL) as MasamTab[]).map(t => (
          <button
            key={t}
            className={`tile ${tab === t ? 'on' : ''}`}
            onClick={() => setTab(t)}
          >
            {TAB_LABEL[t]}
          </button>
        ))}
      </div>

      {tab === 'phase'  && <PhaseTab />}
      {tab === 'grid'   && <GridTab />}
      {tab === 'guide'  && <GuideTab />}
      {tab === 'market' && <MasamMarketTab />}
    </div>
  );
}
