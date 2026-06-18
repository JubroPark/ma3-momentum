import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  gradient?: boolean
}

export function Card({ children, className = '', gradient = false }: CardProps) {
  if (gradient) {
    return (
      <div className="p-[1.4px] rounded-card gradient-accent">
        <div className={`bg-bg rounded-[14.6px] p-4 ${className}`}>{children}</div>
      </div>
    )
  }
  return (
    <div className={`bg-surface rounded-card px-[17px] py-4 ${className}`}>
      {children}
    </div>
  )
}
