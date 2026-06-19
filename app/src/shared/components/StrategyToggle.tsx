'use client'
import { useAppContext } from '../context/AppContext'

export function StrategyToggle() {
  const { strategy, setStrategy } = useAppContext()

  return (
    <div className="relative flex bg-[#1e1e26] rounded-[10px] p-[3px] gap-[2px]">
      {(['masam', 'momentum'] as const).map(s => (
        <button
          key={s}
          onClick={() => setStrategy(s)}
          className={`relative z-10 px-3 py-[4.5px] rounded-lg text-xs font-500 transition-colors duration-200 whitespace-nowrap
            ${strategy === s ? 'text-txt' : 'text-txt-3'}`}
        >
          {s === 'masam' ? '마삼룰' : '모멘텀'}
        </button>
      ))}
      <div
        className="absolute top-[3px] bottom-[3px] bg-[#2e2e3a] rounded-lg transition-all duration-250 pointer-events-none"
        style={{
          left: strategy === 'masam' ? '3px' : '50%',
          width: 'calc(50% - 3px)',
        }}
      />
    </div>
  )
}
