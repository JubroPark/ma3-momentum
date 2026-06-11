'use client';
import { useSignals } from '@/hooks/useSignals';
import { tickerColor, tickerInitials, fmtPct } from '@/lib/utils';

const STATE_CHIP: Record<string, string> = {
  HOLDING: 'chip ok',
  SELL_WATCH: 'chip hold',
  SELL: 'chip sell',
  BUY: 'chip buy',
};

const STATE_LABEL: Record<string, string> = {
  HOLDING: '보유중',
  SELL_WATCH: 'HOLD-WATCH',
  SELL: '매도',
  BUY: '매수대기',
};

const HOLD_STATES = ['HOLDING', 'SELL_WATCH', 'SELL', 'BUY'] as const;

export default function HoldTab() {
  const { data, error, isLoading } = useSignals();

  if (isLoading)
    return <div className="skeleton" style={{ height: 200, margin: '20px' }} />;
  if (error)
    return (
      <div className="inset" style={{ margin: '20px' }}>
        <div className="tx">데이터를 불러올 수 없습니다</div>
      </div>
    );
  if (!data) return null;

  const holdItems = data.items.filter((i) =>
    (HOLD_STATES as readonly string[]).includes(i.state)
  );

  return (
    <section>
      <div className="bigttl">
        보유 관리
        <small>
          기준일 <b>{data.as_of}</b>
        </small>
      </div>

      {holdItems.length === 0 ? (
        <div className="empty-state">현재 보유 중인 종목이 없습니다</div>
      ) : (
        <div className="list">
          {holdItems.map((item) => (
            <div key={item.ticker}>
              <div className="lr">
                <div
                  className="logo"
                  style={{ background: tickerColor(item.ticker) }}
                >
                  {tickerInitials(item.ticker)}
                </div>
                <div className="meta">
                  <div className="nm">
                    {item.ticker}
                    <span className={STATE_CHIP[item.state] ?? 'chip ok'}>
                      {STATE_LABEL[item.state] ?? item.state}
                    </span>
                  </div>
                  <div className="sb">
                    현재가 {item.metrics.close.toLocaleString()} · MA50{' '}
                    {item.metrics.ma50.toLocaleString()}
                  </div>
                </div>
                <div className="rt">
                  <div className="v" style={{ fontSize: 13, color: 'var(--t2)' }}>
                    gap {item.metrics.gap50 >= 0 ? '+' : ''}
                    {(item.metrics.gap50 * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
              {item.state === 'SELL' && (
                <div className="sell-box">
                  ⚠️ 매도 권장 — MA50 이탈 확인
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
