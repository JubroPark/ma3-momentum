'use client'
import { useAppContext } from '../context/AppContext'

const TABS = {
  masam: ['발견', '관심', '경제지표', '설정'],
  momentum: ['탑픽', '관심종목', '경제지표', '설정'],
} as const

const ICONS = {
  masam: ['ph:compass-bold', 'ph:star-bold', 'ph:chart-line-bold', 'ph:gear-bold'],
  momentum: ['ph:chart-bar-bold', 'ph:briefcase-bold', 'ph:chart-line-bold', 'ph:gear-bold'],
}

export function BottomTabBar() {
  const { strategy, tab, setTab } = useAppContext()
  const labels = TABS[strategy]
  const icons = ICONS[strategy]

  return (
    <nav className="flex border-t border-line bg-bg-deep">
      {labels.map((label, i) => (
        <button
          key={i}
          onClick={() => setTab(i as 0 | 1 | 2 | 3)}
          className={`flex-1 flex flex-col items-center justify-center gap-1 py-2.5 transition-colors
            ${tab === i ? 'text-blue' : 'text-txt-3'}`}
        >
          <span className="iconify text-xl" data-icon={icons[i]} />
          <span className="text-[10px] font-600">{label}</span>
        </button>
      ))}
    </nav>
  )
}
