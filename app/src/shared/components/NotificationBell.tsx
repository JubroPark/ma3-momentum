'use client'

interface Props { count?: number }

export function NotificationBell({ count = 0 }: Props) {
  return (
    <button className="relative p-1">
      <span className="iconify text-xl text-txt-2" data-icon="ph:bell-bold" />
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-up" />
      )}
    </button>
  )
}
