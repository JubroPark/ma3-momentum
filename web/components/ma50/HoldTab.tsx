'use client';
import { useSignals } from '@/hooks/useSignals';
import { tickerColor, tickerInitials, fmtPct } from '@/lib/utils';

type HoldState = 'HOLDING' | 'SELL_WATCH' | 'SELL' | 'BUY';

const STATE_CHIP: Record<HoldState, string> = {
  HOLDING: 'chip ok',
  SELL_WATCH: 'chip hold',
  SELL: 'chip sell',
  BUY: 'chip buy',
};

const STATE_LABEL: Record<HoldState, string> = {
  HOLDING: '보유중',
  SELL_WATCH: 'HOLD-WATCH',
  SELL: '매도',
  BUY: '매수대기',
};

const RBOX_TEXT: Partial<Record<HoldState, (gap: number) => string>> = {
  SELL_WATCH: (gap) =>
    `50선 이탈했지만 200선 위 · RS 양호 → 관망 중. gap ${gap > 0 ? '+' : ''}${(gap * 100).toFixed(1)}%`,
  SELL: () => '3일 연속 50선 이탈 → 강제 매도 권장. 현금 확보 고려.',
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

  const holdItems = data.items.filter(i =>
    (HOLD_STATES as readonly string[]).includes(i.state)
  );
  const holdingCount = holdItems.filter(i => i.state === 'HOLDING' || i.state === 'BUY').length;
  const sellCount = holdItems.filter(i => i.state === 'SELL' || i.state === 'SELL_WATCH').length;
  const hasSellAlert = holdItems.some(i => i.state === 'SELL');

  return (
    <section>
      <div className="bigttl">
        보유 관리
        <small>기준일 <b>{data.as_of}</b></small>
      </div>

      {/* 요약 카드 2개 */}
      <div className="duo">
        <div className="c">
          <div className="l">보유중</div>
          <div className="v">{holdingCount}종목</div>
        </div>
        <div className="c">
          <div className="l">매도·관망</div>
          <div className="v" style={{ color: sellCount > 0 ? 'var(--up)' : 'var(--t1)' }}>
            {sellCount}종목
          </div>
        </div>
      </div>

      {holdItems.length === 0 ? (
        <div className="empty-state">현재 보유 중인 종목이 없습니다</div>
      ) : (
        <>
          <div className="sh"><span className="t">보유 종목</span><span className="a">기준일 {data.as_of}</span></div>
          <div className="list">
            {holdItems.map(item => {
              const state = item.state as HoldState;
              const rboxFn = RBOX_TEXT[state];
              return (
                <div key={item.ticker}>
                  <div className="lr">
                    <div className="logo" style={{ background: tickerColor(item.ticker) }}>
                      {tickerInitials(item.ticker)}
                    </div>
                    <div className="meta">
                      <div className="nm">
                        {item.ticker}
                        <span className={STATE_CHIP[state] ?? 'chip ok'}>
                          {STATE_LABEL[state] ?? item.state}
                        </span>
                      </div>
                      <div className="sb">
                        현재가 {item.metrics.close.toLocaleString()} · MA50 {item.metrics.ma50.toLocaleString()}
                      </div>
                    </div>
                    <div className="rt">
                      <div className="v" style={{ fontSize: 13, color: item.metrics.gap50 >= 0 ? 'var(--green)' : 'var(--up)' }}>
                        {fmtPct(item.metrics.gap50)}
                      </div>
                      <div className="c" style={{ color: 'var(--t3)' }}>vs MA50</div>
                    </div>
                  </div>
                  {rboxFn && (
                    <div className="rbox">
                      <b>{rboxFn(item.metrics.gap50)}</b>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* 매도 알림 배너 */}
          {hasSellAlert && (
            <div className="notch" style={{ marginBottom: 8 }}>
              <p>50선이 무너졌거나 매도 신호가 뜬 종목은<br/>여기서 한번에 확인하세요</p>
            </div>
          )}

          {/* 하단 메뉴 */}
          <div style={{ marginTop: 14 }}>
            <div className="nrow">
              <span className="k">전이 기록</span>
              <svg viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>
            <div className="nrow" style={{ borderBottom: '1px solid var(--line)' }}>
              <span className="k">매도 내역</span>
              <svg viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
