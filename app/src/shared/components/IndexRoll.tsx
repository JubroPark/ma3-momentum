'use client'
import { useState, useEffect } from 'react'

interface IndexItem {
  label: string
  value: string
  changePct: number
}

export function IndexRoll({ items, intervalMs = 3000 }: { items: IndexItem[]; intervalMs?: number }) {
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    if (items.length <= 1) return
    const t = setInterval(() => setIdx(i => (i + 1) % items.length), intervalMs)
    return () => clearInterval(t)
  }, [items.length, intervalMs])

  const item = items[idx]
  if (!item) return null

  return (
    <div className="flex items-baseline gap-1.5 text-[11.9px] font-500 text-txt-2">
      <span className="text-txt font-700">{item.label}</span>
      <span className="font-700">{item.value}</span>
      <span className={item.changePct >= 0 ? 'text-up' : 'text-down'}>
        {item.changePct >= 0 ? '+' : ''}{item.changePct.toFixed(2)}%
      </span>
    </div>
  )
}
