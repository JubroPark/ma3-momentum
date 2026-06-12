'use client';
import { useState } from 'react';
import { useMasam } from '@/hooks/useMasam';
import MarketContextSection from '@/components/shared/MarketContextSection';

const HEDGE_LABEL: Record<string, string> = {
  DOLLAR:     '달러 현금',
  TLT:        'TLT (장기채)',
  IAU_GLD_TIP:'IAU+GLD+TIP (금·물가)',
};

export default function MasamMarketTab() {
  const { data, error, isLoading } = useMasam();
  const [rebalLimit, setRebalLimit] = useState<25 | 50>(25);

  if (isLoading) return <div className="skeleton" style={{ height: 200, margin: '20px' }} />;
  if (error || !data) return (
    <div className="inset" style={{ margin: '20px' }}>
      <div className="tx">데이터를 불러올 수 없습니다</div>
    </div>
  );

  return (
    <section>
      <div className="bigttl">시장환경 / 설정</div>

      {/* 공유 시장환경 컴포넌트 */}
      <div className="sh"><span className="t">거시 지표</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <MarketContextSection />
      </div>

      {/* 마삼 전용: 헤지 배치 */}
      <div className="sh"><span className="t">헤지 배치</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="mlist">
          <div className="mr">
            <div><div className="k">현재 헤지</div></div>
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

      {/* 마삼 전용: 설정 */}
      <div className="sh"><span className="t">설정</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="mlist">
          <div className="mr">
            <div>
              <div className="k">리밸런싱 한도</div>
              <div className="ks">1회 매도 최대 비중</div>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {([25, 50] as const).map(v => (
                <button
                  key={v}
                  onClick={() => setRebalLimit(v)}
                  style={{
                    background: rebalLimit === v ? 'var(--accent)' : 'var(--inset)',
                    color: rebalLimit === v ? '#fff' : 'var(--t2)',
                    border: 'none', borderRadius: 8, padding: '6px 14px',
                    fontSize: 13, fontWeight: 700, cursor: 'pointer',
                  }}
                >
                  {v}%
                </button>
              ))}
            </div>
          </div>
        </div>
        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--t3)' }}>
          ※ 팬덤/CEO 가중 등 정성 규칙은 서비스 범위 제외 (사용자 자체 판단)
        </div>
      </div>
    </section>
  );
}
