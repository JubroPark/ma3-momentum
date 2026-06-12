'use client';
import { useState, useEffect } from 'react';
import { useSignals } from '@/hooks/useSignals';
import BuyTab from './ma50/BuyTab';
import HoldTab from './ma50/HoldTab';
import MarketTab from './ma50/MarketTab';
import SettingsTab from './ma50/SettingsTab';
import MasamShell from './masam/MasamShell';

type Strategy = 'masam' | 'ma50';
type Ma50Tab = 'buy' | 'hold' | 'market' | 'settings';

export default function AppShell() {
  const [strategy, setStrategy] = useState<Strategy>('ma50');
  const [tab, setTab] = useState<Ma50Tab>('buy');
  const { data } = useSignals();

  useEffect(() => {
    const s = localStorage.getItem('strategy') as Strategy | null;
    const VALID_TABS: Ma50Tab[] = ['buy', 'hold', 'market', 'settings'];
    const t = localStorage.getItem('ma50Tab');
    if (s === 'masam' || s === 'ma50') setStrategy(s);
    if (t && (VALID_TABS as string[]).includes(t)) setTab(t as Ma50Tab);
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
        <div className="topbar-left">
          <div className="topbar-title">
            ma3 momentum
            {data?.as_of && <b> {data.as_of}</b>}
          </div>
        </div>
        <div className="topbar-icons">
          {/* 즐겨찾기 */}
          <svg viewBox="0 0 24 24">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {/* 검색 */}
          <svg viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="7"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65" strokeLinecap="round"/>
          </svg>
          {/* 메뉴 (알림 dot) */}
          <div className="bdot" style={{ display: 'flex', alignItems: 'center' }}>
            <svg viewBox="0 0 24 24">
              <line x1="4" y1="7" x2="20" y2="7" strokeLinecap="round"/>
              <line x1="4" y1="12" x2="20" y2="12" strokeLinecap="round"/>
              <line x1="4" y1="17" x2="14" y2="17" strokeLinecap="round"/>
            </svg>
          </div>
        </div>
      </div>

      {/* Strategy Toggle */}
      <div className="strategy-seg">
        <button
          className={strategy === 'masam' ? 'on' : ''}
          onClick={() => switchStrategy('masam')}
        >나스닥 마삼룰</button>
        <button
          className={strategy === 'ma50' ? 'on' : ''}
          onClick={() => switchStrategy('ma50')}
        >모멘텀 탑픽</button>
      </div>

      {/* Content */}
      <div className="scroll">
        {strategy === 'masam' && <MasamShell />}
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
