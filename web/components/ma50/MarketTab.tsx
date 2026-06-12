'use client';
import { useMarket } from '@/hooks/useMarket';

const RATE_LABEL: Record<string, string> = {
  ZERO: '제로금리',
  NON_ZERO: '정상금리',
};
const QE_LABEL: Record<string, string> = {
  QE_ON: 'QE 활성',
  QE_OFF: 'QE 비활성',
  AMBIGUOUS: '판단 유보',
};

function vixColor(v: number) {
  if (v < 20) return 'var(--green)';
  if (v < 30) return 'var(--amber)';
  return 'var(--up)';
}
function vixLabel(v: number) {
  if (v < 20) return '안정';
  if (v < 30) return '경계';
  return '공포';
}

export default function MarketTab() {
  const { data, isLoading } = useMarket();

  if (isLoading) return (
    <>
      <div className="skeleton" style={{ height: 60 }} />
      <div className="skeleton" style={{ height: 220, marginTop: 10 }} />
    </>
  );

  const regime = data?.regime ?? null;
  const vix = data?.vix ?? null;
  const isRiskOn = regime === 'RISK_ON';
  const barWidth = isRiskOn ? '74%' : '28%';
  const regimeColor = isRiskOn ? 'var(--green)' : 'var(--up)';

  return (
    <section>
      <div className="bigttl">시장 환경 <small>레짐 · 거시</small></div>

      {/* 레짐 게이지 */}
      <div className="card gauge" style={{ marginTop: 6 }}>
        <div className="lab">현재 시장 레짐</div>
        <div className="big" style={{ color: regime ? regimeColor : 'var(--t3)' }}>
          {regime ? (isRiskOn ? 'RISK ON' : 'RISK OFF') : '—'}
        </div>
        <div className="desc">
          {isRiskOn
            ? 'SPY가 200일선 위 — 위험선호 · 풀 매수 활성'
            : regime
            ? 'SPY가 200일선 아래 — 매수 보수화 · 청산 강화'
            : '데이터 로딩 중'}
        </div>
        <div className="bar">
          <i style={{ width: regime ? barWidth : '0%' }} />
          {regime && <div className="mk" style={{ left: barWidth }} />}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--t3)', fontWeight: 600 }}>
          <span>방어</span><span>중립</span><span>위험선호</span>
        </div>
      </div>

      {/* 핵심 지표 */}
      <div className="sh"><span className="t">핵심 지표</span></div>
      <div className="card mlist" style={{ marginTop: 0 }}>
        <div className="mr">
          <div>
            <div className="k">VIX 변동성</div>
            <div className="ks">{vix !== null ? `${vixLabel(vix)} 구간` : '데이터 없음'}</div>
          </div>
          <div>
            <div className="n" style={{ color: vix !== null ? vixColor(vix) : 'var(--t3)' }}>
              {vix !== null ? vix.toFixed(1) : '—'}
            </div>
          </div>
        </div>
        <div className="mr">
          <div>
            <div className="k">금리 환경</div>
            <div className="ks">{data?.dff !== null ? `DFF ${data?.dff}%` : 'FRED 없음'}</div>
          </div>
          <div>
            <div className="n" style={{
              fontSize: 13,
              color: data?.rate_env === 'ZERO' ? 'var(--green)' : data?.rate_env ? 'var(--amber)' : 'var(--t3)',
            }}>
              {data?.rate_env ? RATE_LABEL[data.rate_env] : '—'}
            </div>
          </div>
        </div>
        <div className="mr">
          <div>
            <div className="k">QE 상태</div>
            <div className="ks">연준 총자산 기울기</div>
          </div>
          <div>
            <div className="n" style={{
              fontSize: 13,
              color: data?.qe_state === 'QE_ON' ? 'var(--green)' : 'var(--t2)',
            }}>
              {data?.qe_state ? QE_LABEL[data.qe_state] : '—'}
            </div>
          </div>
        </div>
        <div className="mr">
          <div>
            <div className="k">공포·탐욕</div>
            <div className="ks">CNN Fear & Greed</div>
          </div>
          <div>
            <div className="n" style={{ fontSize: 13, color: 'var(--t3)' }}>
              {data?.fear_greed !== null && data?.fear_greed !== undefined ? data.fear_greed : '준비 중'}
            </div>
          </div>
        </div>
        <div className="mr">
          <div>
            <div className="k">PMI</div>
            <div className="ks">제조업·서비스업</div>
          </div>
          <div>
            <div className="n" style={{ fontSize: 13, color: 'var(--t3)' }}>
              {data?.pmi !== null && data?.pmi !== undefined ? data.pmi : '준비 중'}
            </div>
          </div>
        </div>
      </div>

      {/* 데이터 기준일 */}
      {data?.as_of && (
        <div style={{ margin: '10px 20px 0', fontSize: 11, color: 'var(--t3)', textAlign: 'right' }}>
          기준일 {data.as_of}
        </div>
      )}
    </section>
  );
}
