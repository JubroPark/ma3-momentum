'use client';
import { useState, useEffect } from 'react';
import { useSignals } from '@/hooks/useSignals';
import BuyTab from './ma50/BuyTab';
import HoldTab from './ma50/HoldTab';
import MarketTab from './ma50/MarketTab';
import SettingsTab from './ma50/SettingsTab';
import MasamPlaceholder from './masam/MasamPlaceholder';

type Strategy = 'masam' | 'ma50';
type Ma50Tab = 'buy' | 'hold' | 'market' | 'settings';

export default function AppShell() {
  const [strategy, setStrategy] = useState<Strategy>('ma50');
  const [tab, setTab] = useState<Ma50Tab>('buy');
  const { data } = useSignals();

  useEffect(() => {
    const s = localStorage.getItem('strategy') as Strategy | null;
    const t = localStorage.getItem('ma50Tab') as Ma50Tab | null;
    if (s === 'masam' || s === 'ma50') setStrategy(s);
    if (t) setTab(t);
  }, []);

  const switchStrategy = (s: Strategy) => {
    setStrategy(s);
    localStorage.setItem('strategy', s);
  };

  const switchTab = (t: Ma50Tab) => {
    setTab(t);
    localStorage.setItem('ma50Tab', t);
  };

  return (
    <div className="phone">
      {/* TopBar */}
      <div className="topbar">
        <div>
          <div className="topbar-title">ma3 momentum</div>
          {data?.as_of && (
            <div className="topbar-date">기준일 {data.as_of}</div>
          )}
        </div>
      </div>

      {/* Strategy Toggle */}
      <div className="strategy-seg">
        <button
          className={strategy === 'masam' ? 'on' : ''}
          onClick={() => switchStrategy('masam')}
        >마삼 대응</button>
        <button
          className={strategy === 'ma50' ? 'on' : ''}
          onClick={() => switchStrategy('ma50')}
        >MA50 스크리너</button>
      </div>

      {/* Content */}
      <div className="scroll">
        {strategy === 'masam' && <MasamPlaceholder />}
        {strategy === 'ma50' && (
          <>
            {tab === 'buy' && <BuyTab />}
            {tab === 'hold' && <HoldTab />}
            {tab === 'market' && <MarketTab />}
            {tab === 'settings' && <SettingsTab />}
          </>
        )}
      </div>

      {/* Bottom Nav (MA50 전용) */}
      {strategy === 'ma50' && (
        <nav className="nav">
          <button className={tab === 'buy' ? 'on' : ''} onClick={() => switchTab('buy')}>
            <svg viewBox="0 0 24 24"><path d="M4 18l5-6 4 3 5-8" strokeLinecap="round" strokeLinejoin="round"/></svg>
            <span>매수후보</span>
          </button>
          <button className={tab === 'hold' ? 'on' : ''} onClick={() => switchTab('hold')}>
            <svg viewBox="0 0 24 24"><rect x="3" y="6" width="18" height="13" rx="3"/><path d="M3 10h18M16 14h2"/></svg>
            <span>보유관리</span>
          </button>
          <button className={tab === 'market' ? 'on' : ''} onClick={() => switchTab('market')}>
            <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="9" ry="4"/><path d="M12 3v18"/></svg>
            <span>시장환경</span>
          </button>
          <button className={tab === 'settings' ? 'on' : ''} onClick={() => switchTab('settings')}>
            <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 13a7.5 7.5 0 0 0 0-2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-1.7-1l-.4-2.6h-4l-.4 2.6a7 7 0 0 0-1.7 1l-2.3-1-2 3.4 2 1.5a7.5 7.5 0 0 0 0 2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 1.7 1l.4 2.6h4l.4-2.6a7 7 0 0 0 1.7-1l2.3 1 2-3.4z"/></svg>
            <span>설정</span>
          </button>
        </nav>
      )}

      {/* 면책 Footer */}
      <div className="disclaimer">
        ⚠️ 투자 권유 아님 · 실거래 전 백테스트 검증 필수
      </div>
    </div>
  );
}
