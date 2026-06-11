'use client';
import { useState, useEffect } from 'react';
import { useSignals } from '@/hooks/useSignals';

type RiskOffMode = 'strict' | 'soft';

const PARAMS: { key: string; label: string; sub: string; value: string }[] = [
  { key: 'vol_mult', label: '거래량 배수', sub: 'vol_mult · hard filter', value: '1.5x' },
  { key: 'breakout_high_lookback', label: '신고가 돌파 기간', sub: 'breakout_high_lookback', value: '20일' },
  { key: 'rs_early_th', label: '초기추세 RS 문턱', sub: 'rs_early_th', value: '상위 80' },
  { key: 'consec_below_sell', label: '연속 이탈 강제매도', sub: 'consec_below_sell', value: '2일' },
  { key: 'max_hold_watch_days', label: 'HOLD-WATCH 시간제한', sub: 'max_hold_watch_days', value: '7일' },
];

export default function SettingsTab() {
  const [mode, setMode] = useState<RiskOffMode>('strict');
  const { data } = useSignals();

  useEffect(() => {
    const saved = localStorage.getItem('riskOffMode');
    if (saved === 'strict' || saved === 'soft') setMode(saved);
  }, []);

  const switchMode = (m: RiskOffMode) => {
    setMode(m);
    localStorage.setItem('riskOffMode', m);
  };

  return (
    <section>
      <div className="bigttl">설정<small>파라미터 · 데이터</small></div>

      <div className="sh"><span className="t">레짐 모드 · 하락장 매수</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="srow">
          <div className="k">
            RISK-OFF 동작
            <span style={{ display: 'block', fontSize: 12, color: 'var(--t2)', marginTop: 2 }}>하락장일 때 매수 처리</span>
          </div>
          <div className="tg">
            <button className={mode === 'strict' ? 'on' : ''} onClick={() => switchMode('strict')}>차단</button>
            <button className={mode === 'soft' ? 'on' : ''} onClick={() => switchMode('soft')}>완화</button>
          </div>
        </div>
      </div>

      <div className="sh"><span className="t">시그널 파라미터 (읽기 전용)</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        {PARAMS.map(p => (
          <div className="srow" key={p.key}>
            <div className="k">
              {p.label}
              <span style={{ display: 'block', fontSize: 11, color: 'var(--t3)', marginTop: 2 }}>{p.sub}</span>
            </div>
            <div className="v">{p.value}</div>
          </div>
        ))}
      </div>

      <div className="sh"><span className="t">데이터</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="srow">
          <div className="k">기준일<span style={{ display: 'block', fontSize: 12, color: 'var(--t2)', marginTop: 2 }}>마지막 데이터 갱신</span></div>
          <div className="v" style={{ color: 'var(--t1)' }}>{data?.as_of ?? '—'}</div>
        </div>
        <div className="srow">
          <div className="k">갱신 주기<span style={{ display: 'block', fontSize: 12, color: 'var(--t2)', marginTop: 2 }}>GitHub Actions cron</span></div>
          <div className="v" style={{ color: 'var(--t1)' }}>평일 22:00 UTC</div>
        </div>
        <div className="srow">
          <div className="k">데이터 소스<span style={{ display: 'block', fontSize: 12, color: 'var(--t2)', marginTop: 2 }}>수정주가 · 무료</span></div>
          <div className="v" style={{ color: 'var(--t1)' }}>yfinance</div>
        </div>
      </div>
    </section>
  );
}
