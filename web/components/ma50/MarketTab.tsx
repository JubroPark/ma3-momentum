'use client';
import { useSignals } from '@/hooks/useSignals';

export default function MarketTab() {
  const { data, error, isLoading } = useSignals();

  if (isLoading) return <div className="skeleton" style={{ height: 180, margin: '20px' }} />;
  if (error || !data) return (
    <div className="inset" style={{ margin: '20px' }}>
      <div className="tx">데이터를 불러올 수 없습니다</div>
    </div>
  );

  const isRiskOn = data.regime === 'RISK_ON';

  return (
    <section>
      <div className="bigttl">시장 환경<small>레짐 · 거시</small></div>

      <div className="card gauge" style={{ marginTop: 6 }}>
        <div className="lab">현재 시장 레짐</div>
        <div
          className="big"
          style={{ color: isRiskOn ? 'var(--green)' : 'var(--up)' }}
        >
          {data.regime}
        </div>
        <div className="desc">
          {isRiskOn
            ? 'SPY가 200일선 위 — 정상 매수 모드'
            : 'SPY가 200일선 아래 — 매수 보수화 · 청산 강화'}
        </div>
        <div className="bar">
          <i style={{ width: isRiskOn ? '72%' : '28%' }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--t3)', fontWeight: 600 }}>
          <span>방어</span><span>중립</span><span>위험선호</span>
        </div>
      </div>

      <div className="sh"><span className="t">기준일</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="mlist">
          <div className="mr">
            <div><div className="k">데이터 기준일</div><div className="ks">마지막 갱신</div></div>
            <div><div className="n">{data.as_of}</div></div>
          </div>
          <div className="mr">
            <div><div className="k">갱신 주기</div><div className="ks">GitHub Actions cron</div></div>
            <div><div className="n" style={{ fontSize: 13, color: 'var(--t2)' }}>평일 22:00 UTC</div></div>
          </div>
        </div>
      </div>

      <div className="sh"><span className="t">거시 지표</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="tx" style={{ color: 'var(--t3)', padding: '8px 0' }}>
          FRED 거시 지표 (금리·VIX·PMI)
          <span style={{ display: 'block', fontSize: 12, marginTop: 4 }}>Phase 3B에서 market.json 추가 후 제공 예정</span>
        </div>
      </div>
    </section>
  );
}
