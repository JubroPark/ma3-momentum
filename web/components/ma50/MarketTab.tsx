'use client';
import { useSignals } from '@/hooks/useSignals';
import MarketContextSection from '@/components/shared/MarketContextSection';

export default function MarketTab() {
  const { data, isLoading } = useSignals();

  return (
    <section>
      <div className="bigttl">
        시장 환경
        {data?.as_of && <small>기준일 <b>{data.as_of}</b></small>}
      </div>

      <div className="sh"><span className="t">거시 지표</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        {isLoading
          ? <div className="skeleton" style={{ height: 160 }} />
          : <MarketContextSection />}
      </div>

      <div className="sh"><span className="t">갱신 정보</span></div>
      <div className="card" style={{ marginTop: 0 }}>
        <div className="mlist">
          <div className="mr">
            <div><div className="k">갱신 주기</div><div className="ks">GitHub Actions cron</div></div>
            <div><div className="n" style={{ fontSize: 13, color: 'var(--t2)' }}>평일 22:00 UTC</div></div>
          </div>
        </div>
      </div>
    </section>
  );
}
