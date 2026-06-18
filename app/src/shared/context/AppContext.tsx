'use client'
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

type Strategy = 'masam' | 'momentum'
type Tab = 0 | 1 | 2 | 3

interface AppContextValue {
  strategy: Strategy
  tab: Tab
  setStrategy: (s: Strategy) => void
  setTab: (t: Tab) => void
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [strategy, setStrategyState] = useState<Strategy>('masam')
  const [tab, setTabState] = useState<Tab>(0)

  useEffect(() => {
    const saved = localStorage.getItem('strategy') as Strategy | null
    if (saved) setStrategyState(saved)
  }, [])

  const setStrategy = (s: Strategy) => {
    setStrategyState(s)
    setTabState(0)
    localStorage.setItem('strategy', s)
  }

  return (
    <AppContext.Provider value={{ strategy, tab, setStrategy, setTab: setTabState }}>
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used within AppProvider')
  return ctx
}
