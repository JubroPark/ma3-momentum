'use client';
import { useState, useEffect } from 'react';
import { useSignals } from '@/hooks/useSignals';
import type { SignalType } from '@/types/signals';
import { tickerColor, tickerInitials, fmtPct, fmtScore } from '@/lib/utils';

type Filter = 'all' | 'STRONG_BREAKOUT' | 'EARLY_TREND' | 'BOUNCE';
type SortBy = 'score' | 'vol' | 'rs';

const CHIP_CLASS: Record<string, string> = {
  STRONG_BREAKOUT: 'chip strong',
  EARLY_TREND: 'chip early',
  BOUNCE: 'chip bounce',
  SELL: 'chip sell',
  OK: 'chip ok',
};

const CHIP_LABEL: Record<string, string> = {
  STRONG_BREAKOUT: '강돌파',
  EARLY_TREND: '초기추세',
  BOUNCE: '지지반등',
  SELL: '매도',
  OK: 'OK',
};

const BUY_SIGNALS: SignalType[] = ['STRONG_BREAKOUT', 'EARLY_TREND', 'BOUNCE'];

const FILTER_ICON: Record<Filter, React.ReactNode> = {
  STRONG_BREAKOUT: (
    <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 18 9 11 13 14 19 6"/>
      <polyline points="15 6 19 6 19 10"/>
    </svg>
  ),
  EARLY_TREND: (
    <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 15 9 10 13 13 20 5"/>
    </svg>
  ),
  BOUNCE: (
    <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 9v4a7 7 0 0 0 14 0"/>
      <path d="M5 9l3-3 3 3"/>
    </svg>
  ),
  all: (
    <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round">
      <line x1="5" y1="7" x2="19" y2="7"/>
      <line x1="5" y1="12" x2="19" y2="12"/>
      <line x1="5" y1="17" x2="13" y2="17"/>
    </svg>
  ),
};

const FILTER_LABEL: Record<Filter, string> = {
  STRONG_BREAKOUT: '강돌파',
  EARLY_TREND: '초기추세',
  BOUNCE: '지지반등',
  all: '전체',
};

const SORT_LABEL: Record<SortBy, string> = {
  score: '점수순',
  vol: '거래량순',
  rs: 'RS순',
};

export default function BuyTab() {
  const [filter, setFilter] = useState<Filter>('all');
  const [sortBy, setSortBy] = useState<SortBy>('score');
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const { data, error, isLoading } = useSignals();

  useEffect(() => {
    try {
      const saved = localStorage.getItem('ma50fav');
      if (saved) setFavorites(new Set(JSON.parse(saved)));
    } catch {}
  }, []);

  const toggleFav = (ticker: string) => {
    setFavorites(prev => {
      const next = new Set(prev);
      if (next.has(ticker)) next.delete(ticker); else next.add(ticker);
      localStorage.setItem('ma50fav', JSON.stringify([...next]));
      return next;
    });
  };

  if (isLoading) return (
    <>
      <div className="skeleton" style={{ height: 60 }} />
      <div className="skeleton" style={{ height: 200, marginTop: 10 }} />
    </>
  );
  if (error) return (
    <div className="inset" style={{ margin: '20px' }}>
      <div className="tx">
        데이터를 불러올 수 없습니다
        <s>잠시 후 다시 시도해주세요</s>
      </div>
    </div>
  );
  if (!data) return null;

  const buyItems = [...data.items].filter(i => BUY_SIGNALS.includes(i.signal_type));
  const counts = {
    STRONG_BREAKOUT: buyItems.filter(i => i.signal_type === 'STRONG_BREAKOUT').length,
    EARLY_TREND: buyItems.filter(i => i.signal_type === 'EARLY_TREND').length,
    BOUNCE: buyItems.filter(i => i.signal_type === 'BOUNCE').length,
  };

  let filtered = filter === 'all'
    ? buyItems
    : buyItems.filter(i => i.signal_type === filter);

  filtered = [...filtered].sort((a, b) => {
    if (sortBy === 'vol') return b.metrics.vol_ratio - a.metrics.vol_ratio;
    if (sortBy === 'rs') return b.metrics.rs_pct - a.metrics.rs_pct;
    return b.score - a.score;
  });

  const regimeLabel = data.regime === 'RISK_ON' ? 'RISK ON' : 'RISK OFF';

  return (
    <section>
      <div className="bigttl">
        매수 후보
        <small>기준일 <b>{data.as_of}</b></small>
      </div>

      {/* 아이콘 필터 타일 */}
      <div className="tiles">
        {(['STRONG_BREAKOUT', 'EARLY_TREND', 'BOUNCE', 'all'] as const).map(f => (
          <button
            key={f}
            className={`ftile ${filter === f ? 'on' : ''}`}
            onClick={() => setFilter(f)}
          >
            <div className="g">{FILTER_ICON[f]}</div>
            <div className="tnm">
              {FILTER_LABEL[f]}
              {f !== 'all' ? ` ${counts[f as keyof typeof counts]}` : ''}
            </div>
          </button>
        ))}
      </div>

      {/* AI 요약 카드 */}
      <div className="ai">
        <div className="in">
          <svg style={{ width: 18, height: 18, flex: 'none', stroke: '#9b8cff', fill: 'none', strokeWidth: 1.8 }} viewBox="0 0 24 24">
            <path d="M12 4l1.6 4.8L18 10l-4.4 1.2L12 16l-1.6-4.8L6 10l4.4-1.2z"/>
          </svg>
          <div className="tx">
            <b>오늘의 시그널 요약</b>
            <p>강돌파 {counts.STRONG_BREAKOUT} · 초기추세 {counts.EARLY_TREND} · 지지반등 {counts.BOUNCE} · 레짐 {regimeLabel}</p>
          </div>
          <svg className="cv" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </div>
      </div>

      {data.regime === 'RISK_OFF' && (
        <div className="inset" style={{ background: 'rgba(240,68,82,.08)' }}>
          <svg viewBox="0 0 24 24" style={{ width: 18, height: 18, stroke: 'var(--t2)', fill: 'none', strokeWidth: 1.9, flex: 'none' }}>
            <circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/>
          </svg>
          <div className="tx" style={{ color: 'var(--up)' }}>
            하락장이라 초기추세 시그널은 꺼져 있어요
            <s>강돌파만 노출 중</s>
          </div>
        </div>
      )}

      <div className="sh big">
        <span className="t">스크리너 랭킹</span>
      </div>

      {/* 정렬 탭 */}
      <div className="ttabs">
        {(['score', 'vol', 'rs'] as SortBy[]).map(s => (
          <button
            key={s}
            className={sortBy === s ? 'on' : ''}
            onClick={() => setSortBy(s)}
          >
            {SORT_LABEL[s]}
          </button>
        ))}
      </div>

      <ol className="list" style={{ listStyle: 'none', padding: '0 20px' }}>
        {filtered.length === 0 ? (
          <div className="empty-state">오늘은 매수 후보가 없습니다</div>
        ) : (
          filtered.map((item, idx) => (
            <li key={item.ticker} className="lr">
              <span className="rk">{idx + 1}</span>
              <div className="logo" style={{ background: tickerColor(item.ticker) }}>
                {tickerInitials(item.ticker)}
              </div>
              <div className="meta">
                <div className="nm">
                  {item.ticker}
                  <span
                    className={CHIP_CLASS[item.signal_type] ?? 'chip ok'}
                    onClick={() => {
                      const f = item.signal_type as Filter;
                      if (f === 'STRONG_BREAKOUT' || f === 'EARLY_TREND' || f === 'BOUNCE') {
                        setFilter(f);
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    {CHIP_LABEL[item.signal_type] ?? item.signal_type}
                  </span>
                </div>
                <div className="sb">
                  거래량 {item.metrics.vol_ratio.toFixed(1)}x · RS 상위 {(100 - item.metrics.rs_pct).toFixed(0)}% · 50선 {fmtPct(item.metrics.gap50)}
                </div>
              </div>
              <div className="rt">
                <div className="v">{fmtScore(item.score)}</div>
              </div>
              {/* 하트 아이콘 */}
              <button
                className={`heart ${favorites.has(item.ticker) ? 'on' : ''}`}
                onClick={() => toggleFav(item.ticker)}
                style={{ border: 'none', background: 'none', cursor: 'pointer', padding: 0, flex: 'none' }}
                aria-label={favorites.has(item.ticker) ? '즐겨찾기 해제' : '즐겨찾기'}
              >
                <svg viewBox="0 0 24 24" style={{ width: 23, height: 23, strokeWidth: 1.8 }}>
                  <path d="M12 20s-7-4.3-9.3-8.3C1.2 8.9 2.4 5.5 5.6 5.5c1.9 0 3.2 1.1 4.4 2.6 1.2-1.5 2.5-2.6 4.4-2.6 3.2 0 4.4 3.4 2.9 6.2C19 15.7 12 20 12 20z"/>
                </svg>
              </button>
            </li>
          ))
        )}
      </ol>
    </section>
  );
}
