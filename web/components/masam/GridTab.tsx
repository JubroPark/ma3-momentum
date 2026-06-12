'use client';
import { useState } from 'react';
import { useMasam } from '@/hooks/useMasam';

function fmt(price: number) {
  return `$${price.toFixed(2)}`;
}

type StockView = 'leader' | 'qqq';

export default function GridTab() {
  const { data, error, isLoading } = useMasam();
  const [view, setView] = useState<StockView>('leader');

  if (isLoading) return <div className="skeleton" style={{ height: 320, margin: '20px' }} />;
  if (error || !data) return (
    <div className="inset" style={{ margin: '20px' }}>
      <div className="tx">데이터를 불러올 수 없습니다</div>
    </div>
  );

  const { mode, rate_env, leader_status, leader_prices, qqq_prices, target_allocation } = data;
  const prices = view === 'leader' ? leader_prices : qqq_prices;
  const ticker = view === 'leader' ? leader_status.rank1_ticker : 'QQQ';

  const { ath, current, crisis_low } = prices;
  const isCrisis = mode === 'CRISIS_STAKING';
  const interval = rate_env === 'NON_ZERO' ? 5.0 : 2.5;
  const maxLevels = Math.round(50 / interval); // NON_ZERO=10, ZERO=20

  const refPrice = isCrisis ? (crisis_low ?? current) : current;
  const refDrawdown = Math.abs((refPrice / ath - 1) * 100);
  const triggeredLevel = isCrisis
    ? target_allocation.stock_pct / 10
    : (100 - target_allocation.stock_pct) / 10;

  const rows = Array.from({ length: maxLevels + 1 }, (_, i) => {
    const thresholdPct = i * interval;
    const thresholdPrice = ath * (1 - thresholdPct / 100);
    const stockPct = isCrisis ? Math.min(i * 10, 100) : 100 - Math.min(i * 10, 25);
    const isTriggered = i <= Math.floor(triggeredLevel);
    const isCurrent = i === Math.floor(triggeredLevel);
    return { level: i, thresholdPct, thresholdPrice, stockPct, isTriggered, isCurrent };
  });

  return (
    <section>
      <div className="bigttl">
        구간 현황
        <small>기준일 <b>{data.as_of}</b></small>
      </div>

      {/* 종목 토글 */}
      <div style={{ display: 'flex', gap: 8, padding: '0 20px', marginBottom: 4 }}>
        {(['leader', 'qqq'] as StockView[]).map(v => (
          <button
            key={v}
            onClick={() => setView(v)}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 12, border: 'none',
              fontWeight: 700, fontSize: 14, cursor: 'pointer',
              background: view === v ? 'var(--accent)' : 'var(--inset)',
              color: view === v ? '#fff' : 'var(--t2)',
            }}
          >
            {v === 'leader' ? leader_status.rank1_ticker : 'QQQ'}
          </button>
        ))}
      </div>

      {/* 요약 카드 */}
      <div className="card" style={{ marginTop: 6 }}>
        <div className="lab">{ticker} 가격</div>
        <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
          {[
            { label: '전고점', value: fmt(ath), color: 'var(--t1)' },
            { label: '현재가', value: fmt(current), color: 'var(--accent)' },
            ...(isCrisis && crisis_low !== null
              ? [{ label: '위기 저가', value: fmt(crisis_low), color: 'var(--up)' }]
              : []),
          ].map(({ label, value, color }) => (
            <div key={label} style={{
              flex: 1, background: 'var(--inset)', borderRadius: 12,
              padding: '12px 0', textAlign: 'center',
            }}>
              <div style={{ fontSize: 16, fontWeight: 800, color }}>{value}</div>
              <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 3, fontWeight: 600 }}>{label}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--t2)' }}>
          {isCrisis
            ? `위기 저가 기준 낙폭 ${refDrawdown.toFixed(1)}% — ${Math.floor(triggeredLevel)}구간 달성`
            : `현재가 기준 낙폭 ${refDrawdown.toFixed(1)}% — ${Math.floor(triggeredLevel)}구간 현금화`}
        </div>
      </div>

      {/* 구간 테이블 */}
      <div className="sh">
        <span className="t">{isCrisis ? '말뚝박기 구간' : '리밸런싱 구간'}</span>
      </div>
      <div className="card" style={{ marginTop: 0, padding: 0, overflow: 'hidden' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1.4fr 1fr 1.2fr',
          padding: '10px 16px', borderBottom: '1px solid var(--inset)',
        }}>
          {['구간', '진입 기준가', isCrisis ? '주식 비중' : '남은 비중', '상태'].map(h => (
            <div key={h} style={{ fontSize: 11, color: 'var(--t3)', fontWeight: 700 }}>{h}</div>
          ))}
        </div>

        {rows.map(({ level, thresholdPct, thresholdPrice, stockPct, isTriggered, isCurrent }) => {
          const bg = isCurrent
            ? 'rgba(49,130,246,.10)'
            : isTriggered ? 'rgba(21,196,122,.04)' : 'transparent';
          const levelColor = isCurrent ? 'var(--accent)' : isTriggered ? 'var(--green)' : 'var(--t3)';

          return (
            <div key={level} style={{
              display: 'grid', gridTemplateColumns: '1fr 1.4fr 1fr 1.2fr',
              padding: '12px 16px', background: bg,
              borderBottom: '1px solid rgba(255,255,255,.04)',
            }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: levelColor }}>
                {level === 0 ? 'ATH' : `${level}구간`}
              </div>
              <div style={{ fontSize: 13, color: 'var(--t1)' }}>
                {level === 0 ? fmt(ath) : `≤ ${fmt(thresholdPrice)}`}
                {level > 0 && (
                  <div style={{ fontSize: 11, color: 'var(--t3)' }}>-{thresholdPct.toFixed(1)}%</div>
                )}
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: isCurrent ? 'var(--accent)' : 'var(--t1)' }}>
                {stockPct}%
              </div>
              <div style={{ fontSize: 12 }}>
                {isCurrent
                  ? <span style={{ color: 'var(--accent)', fontWeight: 700 }}>◉ 현재</span>
                  : isTriggered
                    ? <span style={{ color: 'var(--green)' }}>✓ 완료</span>
                    : <span style={{ color: 'var(--t3)' }}>○ 미도달</span>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
