'use client';
import { useMarket } from '@/hooks/useMarket';

const RATE_LABEL: Record<string, string> = {
  ZERO:     '제로금리',
  NON_ZERO: '정상금리',
};

const QE_LABEL: Record<string, string> = {
  QE_ON:    'QE 활성',
  QE_OFF:   'QE 비활성',
  AMBIGUOUS:'판단 유보',
};

function vixColor(vix: number): string {
  if (vix < 20) return 'var(--green)';
  if (vix < 30) return 'var(--amber)';
  return 'var(--up)';
}

function vixLabel(vix: number): string {
  if (vix < 20) return '안정';
  if (vix < 30) return '경계';
  return '공포';
}

export default function MarketContextSection() {
  const { data, isLoading } = useMarket();

  if (isLoading) return <div className="skeleton" style={{ height: 160, margin: '0' }} />;
  if (!data) return (
    <div className="card" style={{ marginTop: 0 }}>
      <div className="tx" style={{ color: 'var(--t3)' }}>시장환경 데이터 없음</div>
    </div>
  );

  return (
    <>
      {/* 레짐 + VIX */}
      <div style={{ display: 'flex', gap: 10, margin: '0 0 10px' }}>
        <div style={{
          flex: 1, background: 'var(--inset)', borderRadius: 12, padding: '14px 0', textAlign: 'center',
        }}>
          <div style={{
            fontSize: 18, fontWeight: 800,
            color: data.regime === 'RISK_ON' ? 'var(--green)' : 'var(--up)',
          }}>
            {data.regime === 'RISK_ON' ? 'RISK ON' : 'RISK OFF'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 3, fontWeight: 600 }}>레짐</div>
        </div>
        <div style={{
          flex: 1, background: 'var(--inset)', borderRadius: 12, padding: '14px 0', textAlign: 'center',
        }}>
          <div style={{
            fontSize: 18, fontWeight: 800,
            color: data.vix !== null ? vixColor(data.vix) : 'var(--t3)',
          }}>
            {data.vix !== null ? data.vix.toFixed(1) : 'N/A'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 3, fontWeight: 600 }}>
            VIX{data.vix !== null ? ` (${vixLabel(data.vix)})` : ''}
          </div>
        </div>
      </div>

      {/* 금리·QE */}
      <div className="mlist">
        <div className="mr">
          <div>
            <div className="k">금리 환경</div>
            <div className="ks">{data.dff !== null ? `DFF ${data.dff}%` : 'FRED 데이터 없음'}</div>
          </div>
          <div>
            <div className="n" style={{
              fontSize: 13,
              color: data.rate_env === 'ZERO' ? 'var(--green)' : data.rate_env ? 'var(--amber)' : 'var(--t3)',
            }}>
              {data.rate_env ? RATE_LABEL[data.rate_env] : '—'}
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
              color: data.qe_state === 'QE_ON' ? 'var(--green)' : data.qe_state ? 'var(--t2)' : 'var(--t3)',
            }}>
              {data.qe_state ? QE_LABEL[data.qe_state] : '—'}
            </div>
          </div>
        </div>
        <div className="mr">
          <div>
            <div className="k">공포·탐욕 지수</div>
            <div className="ks">CNN Fear & Greed</div>
          </div>
          <div>
            <div className="n" style={{ fontSize: 13, color: 'var(--t3)' }}>
              {data.fear_greed !== null ? data.fear_greed : '준비 중'}
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
              {data.pmi !== null ? data.pmi : '준비 중'}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 10, fontSize: 11, color: 'var(--t3)', textAlign: 'right' }}>
        기준일 {data.as_of}
      </div>
    </>
  );
}
