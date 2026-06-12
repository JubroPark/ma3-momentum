'use client';
import { useMasam } from '@/hooks/useMasam';

const MODE_LABEL: Record<string, string> = {
  REBALANCING:    '리밸런싱',
  CRISIS_STAKING: '위기대응 말뚝박기',
  PANIC:          '공황',
  PANIC_EMERGENCY:'공황 비상',
};

const MODE_COLOR: Record<string, string> = {
  REBALANCING:    'var(--amber)',
  CRISIS_STAKING: 'var(--up)',
  PANIC:          'var(--up)',
  PANIC_EMERGENCY:'var(--up)',
};

const HEDGE_LABEL: Record<string, string> = {
  DOLLAR:     '달러 현금',
  TLT:        'TLT (장기채)',
  IAU_GLD_TIP:'IAU+GLD+TIP (금·물가)',
};

const GRADE_COLOR: Record<string, string> = {
  '약': 'var(--t2)',
  '중': 'var(--amber)',
  '강': 'var(--green)',
};

function fmtMcap(n: number): string {
  const t = n / 1e12;
  return t >= 1 ? `${t.toFixed(2)}조` : `${(n / 1e9).toFixed(0)}B`;
}

export default function PhaseTab() {
  const { data, error, isLoading } = useMasam();

  if (isLoading) return <div className="skeleton" style={{ height: 320, margin: '20px' }} />;
  if (error || !data) return (
    <div className="inset" style={{ margin: '20px' }}>
      <div className="tx">데이터를 불러올 수 없습니다</div>
    </div>
  );

  const { mode, masam, leader_status, target_allocation, hedge_allocation,
          distance_to_triggers, additional_buy_signal, alerts } = data;
  const panicLeft = Math.max(0, 4 - masam.month_count);

  return (
    <section>
      <div className="bigttl">
        현재 국면
        <small>기준일 <b>{data.as_of}</b></small>
      </div>

      {/* 모드 배지 */}
      <div className="card" style={{ marginTop: 6 }}>
        <div className="lab">현재 모드</div>
        <div className="big" style={{ color: MODE_COLOR[mode] ?? 'var(--t1)' }}>
          {MODE_LABEL[mode] ?? mode}
        </div>
        <div className="desc">
          이번 달 마삼 {masam.month_count}회 · 공황 확정까지 {panicLeft}회 남음
        </div>
      </div>

      {/* 비중 카드 */}
      <div className="sh"><span className="t">목표 비중</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="tx" style={{ fontSize: 12, color: 'var(--t3)', marginBottom: 12 }}>
          {target_allocation.label}
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {([
            { label: '주식', pct: target_allocation.stock_pct, color: 'var(--up)' },
            { label: '헤지', pct: target_allocation.hedge_pct, color: 'var(--amber)' },
            { label: '현금', pct: target_allocation.cash_pct, color: 'var(--t2)' },
          ] as const).map(({ label, pct, color }) => (
            <div key={label} style={{
              flex: 1, background: 'var(--inset)', borderRadius: 12, padding: '14px 0', textAlign: 'center',
            }}>
              <div style={{ fontSize: 22, fontWeight: 800, color }}>{pct}%</div>
              <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 3, fontWeight: 600 }}>{label}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--t2)', fontWeight: 600 }}>
          헤지: {HEDGE_LABEL[hedge_allocation.type] ?? hedge_allocation.type}
        </div>
      </div>

      {/* 다음 트리거까지 거리 */}
      <div className="sh"><span className="t">다음 트리거까지</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="mlist">
          <div className="mr">
            <div>
              <div className="k">V자 올인</div>
              <div className="ks">강한 올인 조건</div>
            </div>
            <div>
              <div className="n" style={{ color: 'var(--green)' }}>
                -{distance_to_triggers.v_allin_pct_needed.toFixed(1)}%
              </div>
            </div>
          </div>
          <div className="mr">
            <div>
              <div className="k">EMERGENCY 올인</div>
              <div className="ks">공황+고점대비</div>
            </div>
            <div>
              <div className="n" style={{ color: 'var(--up)' }}>
                -{distance_to_triggers.emergency_allin_pct_away.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 1등주 현황 */}
      <div className="sh"><span className="t">1등주 현황</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="mlist">
          <div className="mr">
            <div>
              <div className="k">{leader_status.rank1_ticker} #1</div>
              <div className="ks">시총 {fmtMcap(leader_status.rank1_mcap)}</div>
            </div>
            <div>
              <div className="n" style={{ color: 'var(--green)' }}>1등주</div>
            </div>
          </div>
          <div className="mr">
            <div>
              <div className="k">{leader_status.rank2_ticker} #2</div>
              <div className="ks">시총 {fmtMcap(leader_status.rank2_mcap)}</div>
            </div>
            <div>
              <div className="n" style={{ color: 'var(--t2)' }}>
                격차 {leader_status.gap_pct.toFixed(1)}%
                {leader_status.gap_below_10pct && (
                  <span style={{ color: 'var(--amber)', marginLeft: 4 }}>⚠</span>
                )}
              </div>
            </div>
          </div>
        </div>
        {leader_status.overtake_detected && (
          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--amber)', fontWeight: 700 }}>
            ⚠️ 2등주가 1등주 시총 추월 — 교체 검토 필요
          </div>
        )}
      </div>

      {/* RSI·MFI 배지 */}
      <div className="sh"><span className="t">추가 자금 투입 조건 (1등주)</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
          <div style={{
            flex: 1, background: 'var(--inset)', borderRadius: 10, padding: '12px 0', textAlign: 'center',
          }}>
            <div style={{
              fontSize: 20, fontWeight: 800,
              color: (additional_buy_signal.rsi14 ?? 100) <= 50 ? 'var(--green)' : 'var(--t2)',
            }}>
              {additional_buy_signal.rsi14 !== null ? additional_buy_signal.rsi14.toFixed(1) : 'N/A'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 3, fontWeight: 600 }}>RSI14</div>
          </div>
          <div style={{
            flex: 1, background: 'var(--inset)', borderRadius: 10, padding: '12px 0', textAlign: 'center',
          }}>
            <div style={{
              fontSize: 20, fontWeight: 800,
              color: (additional_buy_signal.mfi14 ?? 100) <= 50 ? 'var(--green)' : 'var(--t2)',
            }}>
              {additional_buy_signal.mfi14 !== null ? additional_buy_signal.mfi14.toFixed(1) : 'N/A'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 3, fontWeight: 600 }}>MFI14</div>
          </div>
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: additional_buy_signal.both_below_50 ? 'var(--green)' : 'var(--t2)' }}>
          {additional_buy_signal.both_below_50 ? '✅ ' : '❌ '}{additional_buy_signal.label}
        </div>
      </div>

      {/* 알림 */}
      {alerts.length > 0 && (
        <>
          <div className="sh"><span className="t">알림</span></div>
          {alerts.map((a, i) => (
            <div key={i} className="inset" style={{ background: 'rgba(247,169,59,.1)' }}>
              <div className="tx" style={{ color: 'var(--amber)' }}>{a}</div>
            </div>
          ))}
        </>
      )}
    </section>
  );
}
