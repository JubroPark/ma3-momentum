import { ReactNode } from 'react'

const VARIANTS = {
  normal:  'bg-blue/20 text-blue',
  crisis:  'bg-amber/20 text-amber',
  panic:   'bg-up/20 text-up',
  green:   'bg-teal/20 text-teal',
  yellow:  'bg-amber/20 text-amber',
  red:     'bg-up/20 text-up',
  buy:     'bg-teal/20 text-teal',
  sell:    'bg-up/20 text-up',
  hold:    'bg-surface-2 text-txt-2',
  watch:   'bg-purple/20 text-purple',
} as const

type Variant = keyof typeof VARIANTS

interface BadgeProps {
  variant: Variant
  children: ReactNode
  className?: string
}

export function Badge({ variant, children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-600 ${VARIANTS[variant]} ${className}`}>
      {children}
    </span>
  )
}
