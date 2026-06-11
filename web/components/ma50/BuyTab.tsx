'use client';
import { useState } from 'react';
import { useSignals } from '@/hooks/useSignals';
import type { SignalType } from '@/types/signals';
import { tickerColor, tickerInitials, fmtPct, fmtScore } from '@/lib/utils';

type Filter = 'all' | 'STRONG_BREAKOUT' | 'EARLY_TREND' | 'BOUNCE';

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

const FILTER_LABEL: Record<Filter, string> = {
  STRONG_BREAKOUT: '강돌파',
  EARLY_TREND: '초기추세',
  BOUNCE: '지지반등',
  all: '전체',
};

export default function BuyTab() {
  const [filter, setFilter] = useState<Filter>('all');
  const { data, error, isLoading } = useSignals();

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
        <span style={{ color: 'var(--t2)', fontSize: 13, marginTop: 4, display: 'block' }}>잠시 후 다시 시도해주세요</span>
      </div>
    </div>
  );
  if (!data) return null;

  const buyItems = [...data.items]
    .filter(i => BUY_SIGNALS.includes(i.signal_type))
    .sort((a, b) => b.score - a.score);
  const counts = {
    STRONG_BREAKOUT: buyItems.filter(i => i.signal_type === 'STRONG_BREAKOUT').length,
    EARLY_TREND: buyItems.filter(i => i.signal_type === 'EARLY_TREND').length,
    BOUNCE: buyItems.filter(i => i.signal_type === 'BOUNCE').length,
  };
  const filtered = filter === 'all'
    ? buyItems
    : buyItems.filter(i => i.signal_type === filter);

  return (
    <section>
      <div className="bigttl">
        매수 후보
        <small>기준일 <b>{data.as_of}</b></small>
      </div>

      <div className="tiles">
        {(['STRONG_BREAKOUT', 'EARLY_TREND', 'BOUNCE', 'all'] as const).map(f => (
          <button
            key={f}
            className={`tile ${filter === f ? 'on' : ''}`}
            onClick={() => setFilter(f)}
          >
            {FILTER_LABEL[f]}
            {f !== 'all' ? ` ${counts[f]}` : ''}
          </button>
        ))}
      </div>

      <div className="inset">
        <div className="tx">
          강돌파 {counts.STRONG_BREAKOUT} · 초기추세 {counts.EARLY_TREND} · 지지반등 {counts.BOUNCE}
          <s>레짐 {data.regime === 'RISK_ON' ? '위험선호' : '방어'}</s>
        </div>
      </div>

      {data.regime === 'RISK_OFF' && (
        <div className="inset" style={{ background: 'rgba(240,68,82,.08)' }}>
          <div className="tx" style={{ color: 'var(--up)' }}>
            하락장 — 초기추세 신호 비활성
            <s>RISK_OFF: SPY가 200일선 아래</s>
          </div>
        </div>
      )}

      <div className="sh big">
        <span className="t">스크리너 랭킹</span>
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
            </li>
          ))
        )}
      </ol>
    </section>
  );
}
