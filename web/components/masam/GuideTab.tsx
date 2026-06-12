'use client';
import { useMasam } from '@/hooks/useMasam';
import type { MasamMode } from '@/types/masam';

const GRADE_LABEL: Record<string, string> = { '약': '약', '중': '중', '강': '강' };
const GRADE_COLOR: Record<string, string> = {
  '약': 'var(--t2)',
  '중': 'var(--amber)',
  '강': 'var(--green)',
};

const HEDGE_LABEL: Record<string, string> = {
  DOLLAR:     '달러 현금',
  TLT:        'TLT (장기채)',
  IAU_GLD_TIP:'IAU+GLD+TIP (금·물가)',
};

function CrisisGuide({ data }: { data: NonNullable<ReturnType<typeof useMasam>['data']> }) {
  const metCount = data.all_in_conditions.filter(c => c.met).length;
  return (
    <>
      <div className="sh"><span className="t">올인 조건 체크리스트</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div style={{ marginBottom: 8, fontSize: 12, color: 'var(--t3)', fontWeight: 600 }}>
          {metCount}/4 충족
        </div>
        <div className="mlist">
          {data.all_in_conditions.map(c => (
            <div key={c.id} className="mr">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  fontSize: 16,
                  color: c.met ? 'var(--green)' : 'var(--t3)',
                }}>
                  {c.met ? '✅' : '☐'}
                </span>
                <div>
                  <div className="k">{c.label}</div>
                </div>
              </div>
              <div>
                <span className="chip" style={{
                  background: 'var(--inset)',
                  color: GRADE_COLOR[c.grade] ?? 'var(--t2)',
                  fontSize: 10,
                }}>
                  {GRADE_LABEL[c.grade]}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="sh"><span className="t">헤지 배치</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="mlist">
          <div className="mr">
            <div>
              <div className="k">현재 헤지</div>
            </div>
            <div>
              <div className="n" style={{ fontSize: 13 }}>
                {HEDGE_LABEL[data.hedge_allocation.type] ?? data.hedge_allocation.type}
              </div>
            </div>
          </div>
        </div>
        <div style={{ marginTop: 10, fontSize: 13, color: 'var(--t2)', fontWeight: 600 }}>
          {data.hedge_allocation.rationale}
        </div>
        <div style={{ marginTop: 6, fontSize: 12, color: 'var(--t3)' }}>
          전환 트리거: {data.hedge_allocation.exit_trigger}
        </div>
      </div>
    </>
  );
}

function RebalancingGuide({ data }: { data: NonNullable<ReturnType<typeof useMasam>['data']> }) {
  return (
    <>
      <div className="sh"><span className="t">현금화 단계</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="tx">{data.target_allocation.label}</div>
        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--t3)' }}>
          -2.5% 하락마다 1등주 10% 매도 → 현금화
        </div>
      </div>
    </>
  );
}

function PanicGuide({ data }: { data: NonNullable<ReturnType<typeof useMasam>['data']> }) {
  const panicLeft = Math.max(0, 4 - data.masam.month_count);
  const { stage, next_tranche_pct, tranches } = data.panic_reentry;
  return (
    <>
      <div className="sh"><span className="t">공황 해제 카운트다운</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div style={{ textAlign: 'center', padding: '8px 0' }}>
          <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--up)' }}>{panicLeft}</div>
          <div style={{ fontSize: 13, color: 'var(--t2)', fontWeight: 600, marginTop: 4 }}>
            마삼 없는 달 필요
          </div>
        </div>
        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--t3)', textAlign: 'center' }}>
          이번 달 {data.masam.month_count}회 발생 · 최근 {data.masam.last_masam_date}
        </div>
      </div>

      <div className="sh"><span className="t">재진입 트래커</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="mlist">
          <div className="mr">
            <div>
              <div className="k">현재 단계</div>
            </div>
            <div>
              <div className="n">{stage + 1} / {tranches.length}</div>
            </div>
          </div>
          <div className="mr">
            <div>
              <div className="k">다음 트랑쉐</div>
              <div className="ks">다음 매수 비중</div>
            </div>
            <div>
              <div className="n" style={{ color: 'var(--accent)' }}>{next_tranche_pct}%</div>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
          {tranches.map((pct, i) => (
            <div key={i} style={{
              flex: 1, background: i <= stage ? 'var(--accent)' : 'var(--inset)',
              borderRadius: 8, padding: '8px 0', textAlign: 'center',
            }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: i <= stage ? '#fff' : 'var(--t3)' }}>
                {pct}%
              </div>
              <div style={{ fontSize: 10, color: i <= stage ? 'rgba(255,255,255,.7)' : 'var(--t3)', marginTop: 2 }}>
                {i + 1}차
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

export default function GuideTab() {
  const { data, error, isLoading } = useMasam();

  if (isLoading) return <div className="skeleton" style={{ height: 320, margin: '20px' }} />;
  if (error || !data) return (
    <div className="inset" style={{ margin: '20px' }}>
      <div className="tx">데이터를 불러올 수 없습니다</div>
    </div>
  );

  return (
    <section>
      <div className="bigttl">행동 가이드</div>

      {/* 권장 행동 */}
      <div className="inset" style={{ background: 'rgba(49,130,246,.1)', marginTop: 10 }}>
        <div className="tx" style={{ color: 'var(--accent)' }}>
          {data.recommended_action}
        </div>
      </div>

      {(data.mode === 'CRISIS_STAKING') && <CrisisGuide data={data} />}
      {(data.mode === 'REBALANCING') && <RebalancingGuide data={data} />}
      {(data.mode === 'PANIC' || data.mode === 'PANIC_EMERGENCY') && <PanicGuide data={data} />}
    </section>
  );
}
